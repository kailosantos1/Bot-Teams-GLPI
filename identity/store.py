"""Vínculos administrativos e auditoria transacional em SQLite."""
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from uuid import UUID

from runtime_paths import ROOT


def guid(value):
    return str(UUID(value))


def user_id(value):
    if isinstance(value, bool) or not str(value).isascii() or not str(value).isdigit() or int(value) <= 0:
        raise ValueError("invalid_user_id")
    return int(value)


class Conflict(ValueError):
    pass


class LinkStore:
    def __init__(self, path="data/identity.sqlite3"):
        candidate = Path(path).expanduser()
        self.path = candidate if candidate.is_absolute() else ROOT / candidate

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA foreign_keys=ON")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def initialize(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1, 2, 3, 4):
                raise ValueError("unsupported_schema")
            if version in (1, 2, 3, 4):
                if version == 1:
                    self._migrate_replies(db)
                if version < 3:
                    from .notifications import migrate
                    migrate(db)
                if version < 4:
                    self._migrate_reply_activity(db)
                return
            db.execute("""CREATE TABLE links (
                tenant_id TEXT NOT NULL, object_id TEXT NOT NULL,
                glpi_user_id INTEGER NOT NULL CHECK(glpi_user_id > 0),
                status TEXT NOT NULL CHECK(status IN ('active','revoked')),
                created_at TEXT NOT NULL, created_by TEXT NOT NULL,
                updated_at TEXT NOT NULL, updated_by TEXT NOT NULL,
                approved_at TEXT NOT NULL, approved_by TEXT NOT NULL,
                approval_reference TEXT NOT NULL,
                PRIMARY KEY(tenant_id, object_id))""")
            db.execute("""CREATE UNIQUE INDEX active_glpi_identity
                ON links(tenant_id, glpi_user_id) WHERE status='active'""")
            db.execute("""CREATE TABLE audit (
                id INTEGER PRIMARY KEY, tenant_id TEXT NOT NULL, object_id TEXT NOT NULL,
                action TEXT NOT NULL CHECK(action IN ('create','revoke','replace')),
                old_glpi_user_id INTEGER, new_glpi_user_id INTEGER,
                occurred_at TEXT NOT NULL, operator TEXT NOT NULL, reference TEXT NOT NULL)""")
            self._migrate_replies(db)
            from .notifications import migrate
            migrate(db)
            self._migrate_reply_activity(db)

    @staticmethod
    def _migrate_replies(db):
        db.execute("""CREATE TABLE reply_operations (
            id TEXT PRIMARY KEY, binding TEXT NOT NULL, ticket_id INTEGER NOT NULL,
            link_revision TEXT NOT NULL,
            body TEXT, state TEXT NOT NULL CHECK(state IN
                ('ready','reserved','submitting','sent','uncertain','cancelled','expired')),
            attempts INTEGER NOT NULL DEFAULT 0, followup_id INTEGER, activity_id TEXT,
            reservation TEXT, created REAL NOT NULL, updated REAL NOT NULL, expires REAL NOT NULL)""")
        db.execute("CREATE INDEX reply_retention ON reply_operations(updated)")
        db.execute("PRAGMA user_version=2")

    @staticmethod
    def _migrate_reply_activity(db):
        columns = {row['name'] for row in db.execute('PRAGMA table_info(reply_operations)')}
        if 'activity_id' not in columns:
            db.execute('ALTER TABLE reply_operations ADD COLUMN activity_id TEXT')
        db.execute('''CREATE UNIQUE INDEX IF NOT EXISTS reply_activity_once
            ON reply_operations(binding,ticket_id,activity_id) WHERE activity_id IS NOT NULL''')
        db.execute('PRAGMA user_version=4')

    def get(self, tenant, object_id):
        with self.connection() as db:
            row = db.execute("SELECT * FROM links WHERE tenant_id=? AND object_id=?",
                             (guid(tenant), guid(object_id))).fetchone()
            return dict(row) if row else None

    def audit(self, tenant, object_id):
        with self.connection() as db:
            return [dict(row) for row in db.execute(
                "SELECT * FROM audit WHERE tenant_id=? AND object_id=? ORDER BY id",
                (guid(tenant), guid(object_id)))]

    def create_automatic(self, tenant, object_id, glpi_user_id):
        """Create only; concurrent equivalent success is safe, never replace/revive.

        change owns the transaction, unique index and audit insert. HTTP must
        already have completed before entering here. No email is retained.
        """
        target = user_id(glpi_user_id)
        try:
            self.change('create', tenant, object_id, glpi_user_id=target,
                        operator='system:teams-email-auto-link',
                        reference='policy:authenticated-microsoft-email-v1')
        except Conflict:
            row = self.get(tenant, object_id)
            if not row or row['status'] != 'active' or row['glpi_user_id'] != target:
                raise
            return row
        row = self.get(tenant, object_id)
        if not row or row['status'] != 'active' or row['glpi_user_id'] != target:
            raise Conflict('link_changed')
        return row

    def change(self, action, tenant, object_id, *, operator, reference,
               glpi_user_id=None, expected_user_id=None):
        tenant, object_id = guid(tenant), guid(object_id)
        if action not in ('create', 'revoke', 'replace') or not operator.strip() or not reference.strip():
            raise ValueError("invalid_change")
        target = user_id(glpi_user_id) if action != 'revoke' else None
        now = datetime.now(timezone.utc).isoformat()
        try:
            with self.connection() as db:
                db.execute("BEGIN IMMEDIATE")
                row = db.execute("SELECT * FROM links WHERE tenant_id=? AND object_id=?",
                                 (tenant, object_id)).fetchone()
                if action == 'create':
                    if row:
                        raise Conflict("link_exists_use_replace")
                    db.execute("INSERT INTO links VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                               (tenant, object_id, target, 'active', now, operator,
                                now, operator, now, operator, reference))
                else:
                    if not row or row['glpi_user_id'] != user_id(expected_user_id):
                        raise Conflict("link_changed_or_missing")
                    if action == 'revoke':
                        if row['status'] != 'active':
                            raise Conflict("already_revoked")
                        db.execute("""UPDATE links SET status='revoked', updated_at=?, updated_by=?
                            WHERE tenant_id=? AND object_id=?""", (now, operator, tenant, object_id))
                    else:
                        if row['status'] == 'active' and row['glpi_user_id'] == target:
                            raise Conflict("same_active_link")
                        db.execute("""UPDATE links SET glpi_user_id=?, status='active', updated_at=?,
                            updated_by=?, approved_at=?, approved_by=?, approval_reference=?
                            WHERE tenant_id=? AND object_id=?""",
                                   (target, now, operator, now, operator, reference, tenant, object_id))
                db.execute("""INSERT INTO audit (tenant_id,object_id,action,old_glpi_user_id,
                    new_glpi_user_id,occurred_at,operator,reference) VALUES (?,?,?,?,?,?,?,?)""",
                           (tenant, object_id, action, row['glpi_user_id'] if row else None,
                            target, now, operator, reference))
        except sqlite3.IntegrityError:
            raise Conflict("conflicting_active_link") from None
