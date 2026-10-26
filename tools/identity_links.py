"""Executar na raiz: python3 -m tools.identity_links --help."""
import argparse
import json
import sqlite3
from identity.store import LinkStore, guid, user_id, Conflict
from identity.glpi import GLPIUserReader


def main(argv=None):
    parser = argparse.ArgumentParser(description=(
        'Afirmação administrativa: confira os IDs reais no Entra/Teams e GLPI. '
        'Os IDs informados não comprovam que se trata da mesma pessoa.'))
    parser.add_argument('--db', help='Caminho absoluto ou relativo à raiz do projeto')
    sub = parser.add_subparsers(dest='action', required=True)
    sub.add_parser('init')
    for action in ('get', 'audit', 'create', 'revoke', 'replace'):
        cmd = sub.add_parser(action)
        cmd.add_argument('--tenant', required=True, type=guid)
        cmd.add_argument('--object-id', required=True, type=guid)
        if action in ('create', 'revoke', 'replace'):
            cmd.add_argument('--operator', required=True)
            cmd.add_argument('--reference', required=True, help='Referência da aprovação, sem segredos')
        if action in ('create', 'replace'):
            cmd.add_argument('--glpi-user-id', required=True, type=user_id)
        if action in ('revoke', 'replace'):
            cmd.add_argument('--expected-user-id', required=True, type=user_id)
    args = parser.parse_args(argv)
    # Import tardio: --help não carrega .env; init/get/audit/revoke com --db também não.
    config = None
    if not args.db or args.action in ('create', 'replace'):
        try:
            from config import settings
            config = settings
        except Exception:
            print('configuration_unavailable')
            return 1
    store = LinkStore(args.db or config.IDENTITY_DB_PATH)
    try:
        if args.action == 'init':
            store.initialize()
            print('schema_ready')
            return 0
        if args.action == 'get':
            print(json.dumps(store.get(args.tenant, args.object_id), ensure_ascii=False))
            return 0
        if args.action == 'audit':
            print(json.dumps(store.audit(args.tenant, args.object_id), ensure_ascii=False))
            return 0
        if args.action in ('create', 'replace'):
            check = GLPIUserReader(config.GLPI_URL, config.GLPI_APP_TOKEN,
                                   config.GLPI_USER_TOKEN).check(args.glpi_user_id)
            if check.code != 'ok' or check.glpi_user_id != args.glpi_user_id:
                print('glpi_validation_denied')
                return 1
        store.change(args.action, args.tenant, args.object_id, operator=args.operator,
                     reference=args.reference, glpi_user_id=getattr(args, 'glpi_user_id', None),
                     expected_user_id=getattr(args, 'expected_user_id', None))
        print('link_updated')
        return 0
    except (Conflict, ValueError, sqlite3.Error, OSError):
        print('operation_denied: confira vínculo, versão do esquema e disponibilidade do banco')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
