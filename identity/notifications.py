"""Durable notification metadata. No message bodies and no network in transactions."""
import json
import secrets
import time
from .store import LinkStore, Conflict


def migrate(db):
    db.execute('''CREATE TABLE notification_references (
        tenant TEXT NOT NULL, object_id TEXT NOT NULL, uid INTEGER NOT NULL,
        revision TEXT NOT NULL, generation TEXT NOT NULL, app TEXT NOT NULL,
        reference TEXT, enabled INTEGER NOT NULL, updated REAL NOT NULL, polled REAL NOT NULL,
        PRIMARY KEY(tenant,object_id))''')
    db.execute('''CREATE TABLE notification_watches (
        tenant TEXT NOT NULL, object_id TEXT NOT NULL, generation TEXT NOT NULL,
        ticket INTEGER NOT NULL, high INTEGER NOT NULL, checked REAL NOT NULL,
        PRIMARY KEY(tenant,object_id,generation,ticket))''')
    db.execute('''CREATE TABLE notification_events (
        id TEXT PRIMARY KEY, tenant TEXT NOT NULL, object_id TEXT NOT NULL,
        revision TEXT NOT NULL, generation TEXT NOT NULL, ticket INTEGER NOT NULL,
        followup INTEGER NOT NULL, state TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
        due REAL NOT NULL, updated REAL NOT NULL, reservation TEXT, reserved_until REAL,
        receipt TEXT, UNIQUE(tenant,object_id,generation,ticket,followup))''')
    db.execute('CREATE INDEX notification_due ON notification_events(state,due)')
    db.execute('CREATE TABLE notification_lease (id INTEGER PRIMARY KEY CHECK(id=1), owner TEXT, expires REAL NOT NULL)')
    db.execute('PRAGMA user_version=3')


class NotificationStore(LinkStore):
    MAX_QUEUE = 2000

    def prepare(self):
        if not self.path.is_file():
            raise OSError('identity_database_missing')
        self.initialize()

    @staticmethod
    def _current(db, ref):
        link = db.execute('SELECT * FROM links WHERE tenant_id=? AND object_id=?',
                          (ref['tenant'], ref['object_id'])).fetchone()
        return bool(link and link['status'] == 'active' and link['glpi_user_id'] == ref['uid']
                    and link['updated_at'] == ref['revision'])

    def capture(self, result, reference, app):
        self.prepare()
        identity = result.identity
        now = time.time()
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            link = db.execute('SELECT * FROM links WHERE tenant_id=? AND object_id=?',
                              (identity.tenant_id, identity.object_id)).fetchone()
            if (not link or link['status'] != 'active' or link['glpi_user_id'] != result.glpi_user_id
                    or link['updated_at'] != result.link_revision):
                raise Conflict('link_changed')
            old = db.execute('SELECT * FROM notification_references WHERE tenant=? AND object_id=?',
                             (identity.tenant_id, identity.object_id)).fetchone()
            # A paused/invalidated recipient requires explicit administrative resume.
            if old and not old['enabled'] and old['revision'] == link['updated_at']:
                return
            same = old and old['enabled'] and old['revision'] == link['updated_at'] and old['app'] == app
            generation = old['generation'] if same else secrets.token_urlsafe(24)
            db.execute('''INSERT OR REPLACE INTO notification_references VALUES (?,?,?,?,?,?,?,?,?,?)''',
                       (identity.tenant_id, identity.object_id, result.glpi_user_id, link['updated_at'],
                        generation, app, json.dumps(reference), 1, now, old["polled"] if same else 0))

    def disable(self, tenant, object_id):
        with self.connection() as db:
            db.execute('''UPDATE notification_references SET enabled=0,reference=NULL,updated=?
                WHERE tenant=? AND object_id=?''', (time.time(), tenant, object_id))
            db.execute("UPDATE notification_events SET state='discarded',updated=? WHERE tenant=? AND object_id=? AND state IN ('pending','reserved')",
                       (time.time(), tenant, object_id))

    def resume(self, tenant, object_id):
        # Delete activation, not links. A NEW authenticated activity must recapture;
        # the fresh generation establishes fresh baselines, never sends old history.
        with self.connection() as db:
            db.execute('DELETE FROM notification_references WHERE tenant=? AND object_id=?', (tenant, object_id))
            db.execute("UPDATE notification_events SET state='discarded',updated=? WHERE tenant=? AND object_id=? AND state IN ('pending','reserved')",
                       (time.time(), tenant, object_id))

    def references(self, limit=None):
        with self.connection() as db:
            sql = 'SELECT * FROM notification_references WHERE enabled=1 ORDER BY polled,tenant,object_id'
            return [dict(r) for r in db.execute(sql + (' LIMIT ?' if limit is not None else ''), (limit,) if limit is not None else ())]

    def reference_for(self, tenant, object_id):
        with self.connection() as db:
            row = db.execute('SELECT * FROM notification_references WHERE tenant=? AND object_id=? AND enabled=1',
                             (tenant, object_id)).fetchone()
            return dict(row) if row else None

    def touch(self, ref):
        with self.connection() as db:
            db.execute("UPDATE notification_references SET polled=? WHERE tenant=? AND object_id=? AND generation=?",
                       (time.time(), ref["tenant"], ref["object_id"], ref["generation"]))

    def current(self, ref):
        with self.connection() as db:
            row = db.execute('SELECT * FROM notification_references WHERE tenant=? AND object_id=?', (ref['tenant'], ref['object_id'])).fetchone()
            return bool(row and row['enabled'] and row['generation'] == ref['generation']
                        and row['app'] == ref['app'] and row['reference'] == ref['reference'] and self._current(db, ref))

    def observe(self, ref, ticket, ids, eligible, owner=None):
        """Complete snapshot only. Queue inserts and high watermark share one commit."""
        now = time.time()
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            if owner is not None and not db.execute('SELECT 1 FROM notification_lease WHERE owner=? AND expires>?', (owner, time.time())).fetchone():
                raise Conflict('lease_lost')
            current = db.execute('SELECT * FROM notification_references WHERE tenant=? AND object_id=?', (ref['tenant'], ref['object_id'])).fetchone()
            if not current or not current['enabled'] or current['generation'] != ref['generation'] or not self._current(db, ref):
                raise Conflict('activation_changed')
            key = (ref['tenant'], ref['object_id'], ref['generation'], ticket)
            watch = db.execute('SELECT high FROM notification_watches WHERE tenant=? AND object_id=? AND generation=? AND ticket=?', key).fetchone()
            high = max(ids, default=0)
            if watch:
                if db.execute("SELECT count(*) FROM notification_events WHERE state IN ('pending','reserved','submitting')").fetchone()[0] + len([fid for fid in eligible if fid > watch['high']]) > self.MAX_QUEUE:
                    raise Conflict('queue_full')
                for fid in sorted(eligible):
                    if fid > watch['high']:
                        db.execute('''INSERT OR IGNORE INTO notification_events
                            (id,tenant,object_id,revision,generation,ticket,followup,state,due,updated)
                            VALUES (?,?,?,?,?,?,?,'pending',?,?)''',
                            (secrets.token_urlsafe(24), ref['tenant'], ref['object_id'], ref['revision'], ref['generation'], ticket, fid, now, now))
            db.execute('INSERT OR REPLACE INTO notification_watches VALUES (?,?,?,?,?,?)', (*key, max(high, watch['high'] if watch else 0), now))
            db.execute('UPDATE notification_references SET polled=? WHERE tenant=? AND object_id=?', (now, ref['tenant'], ref['object_id']))

    def reconcile(self, ref, ticket_ids):
        with self.connection() as db:
            rows = db.execute("SELECT ticket FROM notification_watches WHERE tenant=? AND object_id=? AND generation=?",
                              (ref["tenant"], ref["object_id"], ref["generation"])).fetchall()
            for row in rows:
                if row[0] not in ticket_ids:
                    db.execute("DELETE FROM notification_watches WHERE tenant=? AND object_id=? AND generation=? AND ticket=?",
                               (ref["tenant"], ref["object_id"], ref["generation"], row[0]))

    def ordered_tickets(self, ref, tickets):
        with self.connection() as db:
            checked = {r[0]: r[1] for r in db.execute(
                "SELECT ticket,checked FROM notification_watches WHERE tenant=? AND object_id=? AND generation=?",
                (ref["tenant"], ref["object_id"], ref["generation"]))}
        return sorted(tickets, key=lambda t: (checked.get(t["id"], 0), t["id"]))

    def lease(self, owner, seconds=900):
        now = time.time()
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM notification_lease WHERE id=1').fetchone()
            if row and row['owner'] != owner and row['expires'] > now:
                return False
            db.execute('INSERT OR REPLACE INTO notification_lease VALUES (1,?,?)', (owner, now + seconds))
            return True

    def has_lease(self, owner):
        with self.connection() as db:
            return bool(db.execute('SELECT 1 FROM notification_lease WHERE id=1 AND owner=? AND expires>?', (owner, time.time())).fetchone())

    def release(self, owner):
        with self.connection() as db:
            db.execute('DELETE FROM notification_lease WHERE owner=?', (owner,))

    def reserve(self):
        now, token = time.time(), secrets.token_urlsafe(24)
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute("UPDATE notification_events SET state='uncertain',updated=? WHERE state='submitting' AND reserved_until<=?", (now, now))
            db.execute("UPDATE notification_events SET state='pending',reservation=NULL WHERE state='reserved' AND reserved_until<=?", (now,))
            db.execute("UPDATE notification_events SET state='failed',updated=? WHERE state='pending' AND attempts>=5", (now,))
            row = db.execute("SELECT * FROM notification_events WHERE state='pending' AND due<=? ORDER BY due,id LIMIT 1", (now,)).fetchone()
            if not row:
                return None
            db.execute("UPDATE notification_events SET state='reserved',reservation=?,reserved_until=?,attempts=attempts+1,updated=? WHERE id=?", (token, now + 900, now, row['id']))
            return dict(db.execute('SELECT * FROM notification_events WHERE id=?', (row['id'],)).fetchone())

    def transition(self, event, state, *, delay=0, receipt=None, classification_retry=False):
        if classification_retry and state != 'pending':
            raise ValueError('invalid_classification_retry')
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            if state == 'submitting':
                ref = db.execute('SELECT * FROM notification_references WHERE tenant=? AND object_id=?',
                                 (event['tenant'], event['object_id'])).fetchone()
                if (not ref or not ref['enabled'] or ref['generation'] != event['generation']
                        or ref['revision'] != event['revision'] or not self._current(db, dict(ref))):
                    raise Conflict('activation_changed')
            count = db.execute('''UPDATE notification_events SET state=?,due=?,updated=?,receipt=?,attempts=attempts-?
                WHERE id=? AND reservation=? AND state IN ('reserved','submitting')
                  AND (?=0 OR state='reserved')''',
                (state, time.time() + delay, time.time(), receipt, int(classification_retry),
                 event['id'], event['reservation'], int(classification_retry))).rowcount
            if count != 1:
                raise Conflict('reservation_changed')

    def event(self, token, result, app):
        with self.connection() as db:
            row = db.execute('SELECT * FROM notification_events WHERE id=? AND tenant=? AND object_id=? AND revision=?',
                             (token, result.identity.tenant_id, result.identity.object_id, result.link_revision)).fetchone()
            if not row:
                return None
            ref = db.execute('SELECT * FROM notification_references WHERE tenant=? AND object_id=?', (row['tenant'], row['object_id'])).fetchone()
            if (not ref or not ref['enabled'] or ref['app'] != app or row['generation'] != ref['generation']
                    or row['updated'] < time.time() - 7 * 86400 or not self._current(db, dict(ref))):
                return None
            return dict(row)

    def cleanup(self):
        now = time.time()
        with self.connection() as db:
            db.execute("DELETE FROM notification_events WHERE updated<? AND state NOT IN ('reserved','submitting')", (now - 7 * 86400,))
            # Watches survive event retention: cleanup must never replay historical IDs.
            db.execute('''DELETE FROM notification_watches WHERE NOT EXISTS
                (SELECT 1 FROM notification_references r WHERE r.tenant=notification_watches.tenant
                 AND r.object_id=notification_watches.object_id AND r.generation=notification_watches.generation AND r.enabled=1)''')
            stale = db.execute('SELECT tenant,object_id FROM notification_references WHERE updated<?', (now - 30 * 86400,)).fetchall()
        for row in stale:
            self.disable(row['tenant'], row['object_id'])
