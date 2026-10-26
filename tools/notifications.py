"""Dedicated notification process; imports never start a worker."""
import argparse
import asyncio
import json
from identity.notifications import NotificationStore
from identity.store import guid
from notifications.policy import Policy


async def run(args):
    from config import settings
    store = NotificationStore(args.db or settings.IDENTITY_DB_PATH)
    if args.action in {'pause', 'resume', 'cleanup'}:
        await asyncio.to_thread(store.prepare)
        if args.action == 'cleanup':
            await asyncio.to_thread(store.cleanup)
        else:
            if not args.tenant or not args.object_id:
                raise SystemExit('--tenant e --object-id obrigatórios')
            await asyncio.to_thread(getattr(store, 'disable' if args.action == 'pause' else 'resume'), guid(args.tenant), guid(args.object_id))
        return
    policy = Policy.configured(settings)
    if policy is None:
        raise SystemExit('Notificações desabilitadas ou configuração incompleta; nenhum serviço foi consultado.')
    from identity.ingress import _build_adapter
    from notifications.glpi import NotificationQuery
    from notifications.worker import Worker, SDKTransport
    transport = None
    if not args.simulate:
        adapter, _, _ = _build_adapter(settings)
        transport = SDKTransport(adapter, policy.app)
    query = NotificationQuery(settings.GLPI_URL, settings.GLPI_APP_TOKEN, settings.GLPI_USER_TOKEN)
    worker = Worker(store, query, policy, transport)
    interval = args.interval if args.interval is not None else settings.NOTIFICATIONS_INTERVAL
    if not 10 <= interval <= 86400:
        raise SystemExit('Intervalo deve estar entre 10 e 86400 segundos.')
    while True:
        try:
            print(json.dumps(await worker.cycle(simulate=args.simulate)), flush=True)
        except Exception as error:
            # No credentials, reference, title, API bodies or raw exceptions.
            print(json.dumps({'error': type(error).__name__}), flush=True)
            if args.action == 'once':
                raise SystemExit(1) from None
        if args.action == 'once':
            return
        await asyncio.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['once', 'run', 'pause', 'resume', 'cleanup'])
    parser.add_argument('--db')
    parser.add_argument('--simulate', action='store_true')
    parser.add_argument('--interval', type=int)
    parser.add_argument('--tenant')
    parser.add_argument('--object-id')
    args = parser.parse_args()
    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
