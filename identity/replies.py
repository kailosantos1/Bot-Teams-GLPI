"""Durable at-most-one automatic POST attempt per draft; no HTTP in transactions."""
import json
import secrets
import time
import unicodedata
from .store import LinkStore, user_id, Conflict

DRAFT_TTL = 900
METADATA_TTL = 7 * 86400
MAX_REPLY = 2000


def valid_reply(body):
    return (isinstance(body, str) and 0 < len(body) <= MAX_REPLY
            and any(not c.isspace() and unicodedata.category(c)[0] != 'C' for c in body)
            and all(c in '\n\t' or unicodedata.category(c)[0] != 'C' for c in body))


class ReplyStore(LinkStore):
    def prepare(self):
        # Identity database must already exist; never invent administrative links.
        if not self.path.is_file():
            raise OSError('identity_database_missing')
        self.initialize()
        self.cleanup()

    @staticmethod
    def scope(binding):
        return json.dumps(binding, ensure_ascii=True, separators=(',', ':'))

    def cleanup(self):
        now = time.time()
        with self.connection() as db:
            db.execute("""UPDATE reply_operations SET body=NULL,
                state=CASE WHEN state IN ('reserved','submitting') THEN 'uncertain'
                    WHEN state='ready' THEN 'expired' ELSE state END
                WHERE expires<=?""", (now,))
            db.execute('DELETE FROM reply_operations WHERE updated<?', (now - METADATA_TTL,))

    def create(self, binding, ticket, body):
        return self.create_for_activity(binding, ticket, body, None)[0]

    def create_for_activity(self, binding, ticket, body, activity_id):
        if not valid_reply(body):
            raise ValueError('invalid_reply')
        if activity_id is not None and (not isinstance(activity_id, str) or not activity_id.strip()
                or len(activity_id) > 512 or any(unicodedata.category(c)[0] == 'C' for c in activity_id)):
            raise ValueError('invalid_activity_id')
        self.prepare()
        now, operation = time.time(), secrets.token_urlsafe(24)
        scope, ticket = self.scope(binding), user_id(ticket)
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            link = db.execute('SELECT * FROM links WHERE tenant_id=? AND object_id=?',
                              (binding[0], binding[1])).fetchone()
            if not link or link['status'] != 'active' or link['glpi_user_id'] != binding[2]:
                raise Conflict('link_changed')
            if activity_id is not None:
                existing = db.execute('''SELECT id FROM reply_operations
                    WHERE binding=? AND ticket_id=? AND activity_id=?''',
                    (scope, ticket, activity_id)).fetchone()
                if existing:
                    return existing['id'], False
            db.execute("""INSERT INTO reply_operations
                (id,binding,ticket_id,body,state,created,updated,expires,link_revision,activity_id)
                VALUES (?,?,?,?,'ready',?,?,?,?,?)""",
                (operation, scope, ticket, body, now, now, now + DRAFT_TTL,
                 link['updated_at'], activity_id))
        return operation, True

    def get_operation(self, operation, binding, ticket):
        self.prepare()
        with self.connection() as db:
            row = db.execute('SELECT * FROM reply_operations WHERE id=? AND binding=? AND ticket_id=?',
                             (operation, self.scope(binding), user_id(ticket))).fetchone()
            return dict(row) if row else None

    def reserve(self, operation, binding, ticket):
        self.prepare()
        token, now = secrets.token_urlsafe(24), time.time()
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            link = db.execute('SELECT status,glpi_user_id,updated_at FROM links WHERE tenant_id=? AND object_id=?',
                              (binding[0], binding[1])).fetchone()
            previous = db.execute('SELECT link_revision FROM reply_operations WHERE id=?', (operation,)).fetchone()
            if (not link or link['status'] != 'active' or link['glpi_user_id'] != binding[2]
                    or not previous or previous['link_revision'] != link['updated_at']):
                return None
            count = db.execute("""UPDATE reply_operations SET state='reserved', reservation=?,
                attempts=attempts+1, updated=? WHERE id=? AND binding=? AND ticket_id=?
                AND state='ready' AND expires>?""",
                (token, now, operation, self.scope(binding), user_id(ticket), now)).rowcount
            if count != 1:
                return None
            row = dict(db.execute('SELECT * FROM reply_operations WHERE id=?', (operation,)).fetchone())
            return row

    def mark_submitting(self, operation, token):
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT binding,link_revision FROM reply_operations WHERE id=? AND reservation=?',
                             (operation, token)).fetchone()
            if not row:
                raise Conflict('operation_missing')
            binding = json.loads(row['binding'])
            link = db.execute('SELECT status,glpi_user_id,updated_at FROM links WHERE tenant_id=? AND object_id=?',
                              (binding[0], binding[1])).fetchone()
            if (not link or link['status'] != 'active' or link['glpi_user_id'] != binding[2]
                    or row['link_revision'] != link['updated_at']):
                raise Conflict('link_changed')
            count = db.execute("""UPDATE reply_operations SET state='submitting', updated=?
                WHERE id=? AND reservation=? AND state='reserved' AND expires>?""",
                (time.time(), operation, token, time.time())).rowcount
            if count != 1:
                raise Conflict('operation_not_reserved')

    def finish(self, operation, token, followup_id=None):
        with self.connection() as db:
            count = db.execute("""UPDATE reply_operations SET state=?,followup_id=?,body=NULL,updated=?
                WHERE id=? AND reservation=? AND state IN ('submitting','uncertain')""",
                ('sent' if followup_id else 'uncertain', user_id(followup_id) if followup_id else None,
                 time.time(), operation, token)).rowcount
            if followup_id and count != 1:
                raise Conflict('receipt_not_recorded')

    def release(self, operation, token):
        # Only failures known to precede POST can make the draft retryable.
        with self.connection() as db:
            db.execute("""UPDATE reply_operations SET state='ready',reservation=NULL,updated=?
                WHERE id=? AND reservation=? AND state='reserved'""", (time.time(), operation, token))

    def cancel(self, operation, binding, ticket):
        self.prepare()
        with self.connection() as db:
            db.execute("""UPDATE reply_operations SET state='cancelled',body=NULL,updated=?
                WHERE id=? AND binding=? AND ticket_id=? AND state='ready'""",
                (time.time(), operation, self.scope(binding), user_id(ticket)))

    def sent_followups(self, binding, ticket):
        """Confirmed receipts in this exact identity/conversation scope."""
        self.prepare()
        with self.connection() as db:
            return {row['followup_id'] for row in db.execute('''SELECT followup_id
                FROM reply_operations WHERE binding=? AND ticket_id=? AND state='sent'
                AND followup_id IS NOT NULL''', (self.scope(binding), user_id(ticket)))}
