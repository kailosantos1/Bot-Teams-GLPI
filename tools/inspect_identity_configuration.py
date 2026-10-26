"""Offline presence/schema inspection. Never prints configuration secrets or links."""
import argparse
import logging
from contextlib import closing
import sqlite3
from identity.store import LinkStore, guid

REQUIRED = ('MICROSOFT_APP_ID', 'MICROSOFT_APP_PASSWORD', 'MICROSOFT_APP_TENANT_ID',
            'GLPI_URL', 'GLPI_APP_TOKEN', 'GLPI_USER_TOKEN', 'IDENTITY_ALLOWED_TENANT_ID',
            'IDENTITY_DB_PATH')
GUID_FIELDS = ('MICROSOFT_APP_ID', 'MICROSOFT_APP_TENANT_ID', 'IDENTITY_ALLOWED_TENANT_ID')


def inspect(config):
    lines = []
    for name in REQUIRED:
        present = bool(str(getattr(config, name, '') or '').strip())
        lines.append(f'{name}: ' + ('present' if present else 'missing'))
        if present and name in GUID_FIELDS:
            try:
                guid(getattr(config, name))
                state = 'valid_uuid'
            except (ValueError, TypeError, AttributeError):
                state = 'invalid_uuid'
            lines.append(f'{name}: {state}')
    candidate = getattr(config, 'IDENTITY_DB_PATH', '')
    if not isinstance(candidate, str) or not candidate.strip():
        return lines + ['database: path_missing']
    path = LinkStore(candidate).path.resolve()
    if not path.is_file():
        return lines + ['database: missing']
    # URI read-only mode never creates/initializes/migrates the database.
    try:
        with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=5)) as db:
            version = db.execute('PRAGMA user_version').fetchone()[0]
            tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if version not in (1, 2, 3):
                state = 'unsupported_schema'
            elif not ({'links', 'audit'} | ({'reply_operations'} if version >= 2 else set())
                      | ({'notification_references', 'notification_watches', 'notification_events', 'notification_lease'} if version >= 3 else set())) <= tables:
                state = 'schema_incomplete'
            else:
                # Validate the identity columns without exposing any row.
                db.execute('SELECT tenant_id, object_id, glpi_user_id, status, updated_at FROM links LIMIT 0')
                state = 'schema_current' if version == 3 else 'schema_upgrade_required'
            lines.append(f'database: {state}')
    except (sqlite3.Error, OSError, ValueError):
        lines.append('database: unavailable')
    return lines


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db-path', action='store_true', help='Print only the resolved database path (not credentials)')
    args = parser.parse_args(argv)
    # Settings errors may contain input values: never print them or traceback.
    logging.disable(logging.CRITICAL)
    try:
        from config import settings
        if args.db_path:
            if not settings.IDENTITY_DB_PATH.strip():
                raise ValueError()
            print(LinkStore(settings.IDENTITY_DB_PATH).path.resolve())
        else:
            print('\n'.join(inspect(settings)))
    except Exception:
        print('configuration_unavailable')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
