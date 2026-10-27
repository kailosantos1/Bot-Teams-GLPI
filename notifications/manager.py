"""Single-service worker, isolated from the inbound Teams event loop."""
import asyncio
import threading

from config import logger, settings
from notifications.lifecycle import drain
from notifications.policy import Policy
from tools.notifications_lock import SingleInstanceLock


class NotificationManager:
    def __init__(self):
        self._task = None
        self._stop_event = threading.Event()
        self._lifecycle = asyncio.Lock()
        self._running = False

    async def start(self):
        async with self._lifecycle:
            if self._task is not None or not settings.NOTIFICATIONS_ENABLED:
                return
            policy = Policy.configured(settings)
            if policy is None:
                logger.warning('Configuração de notificações incompleta; worker não iniciado.')
                return
            self._stop_event.clear()
            ready = threading.Event()
            self._task = asyncio.create_task(asyncio.to_thread(self._thread, policy, ready))
            # Initialization (including SQLite/adapter/lock) is off the web loop.
            try:
                await drain(asyncio.to_thread(ready.wait))
            except asyncio.CancelledError:
                self._stop_event.set()
                await drain(self._task)
                self._task = None
                raise
            if not self._running:
                await drain(self._task)
                self._task = None

    def _thread(self, policy, ready):
        lock = None
        try:
            from identity.notifications import NotificationStore
            from identity.ingress import _build_adapter
            from notifications.glpi import NotificationQuery
            from notifications.worker import Worker, SDKTransport
            store = NotificationStore(settings.IDENTITY_DB_PATH)
            lock = SingleInstanceLock(store.path)
            if not lock.acquire():
                logger.warning('Worker de notificações já ativo para este banco.')
                return
            store.prepare()
            async def run():
                adapter, _, _ = _build_adapter(settings)
                worker = Worker(store, NotificationQuery(settings.GLPI_URL, settings.GLPI_APP_TOKEN,
                                settings.GLPI_USER_TOKEN), policy, SDKTransport(adapter, policy.app))
                self._running = True
                ready.set()
                await self._run_loop(worker, settings.NOTIFICATIONS_INTERVAL)
            asyncio.run(run())
        except Exception as error:
            logger.error('Falha no worker de notificações: %s', type(error).__name__)
        finally:
            # asyncio.run has drained its executor before this lock is released.
            if lock is not None:
                lock.release()
            self._running = False
            ready.set()

    async def stop(self):
        async with self._lifecycle:
            self._stop_event.set()
            if self._task is not None:
                try:
                    # No arbitrary cancellation deadline: Requests threads cannot
                    # be killed safely. Keep the OS lock until they actually exit.
                    await drain(self._task)
                finally:
                    self._task = None

    async def _run_loop(self, worker, interval):
        interval = interval if 10 <= interval <= 86400 else 10
        while not self._stop_event.is_set():
            try:
                await worker.cycle(simulate=False)
            except Exception as error:
                logger.error('Falha no ciclo de notificações: %s', type(error).__name__)
            # Interruptible idle/backoff, without blocking either event loop.
            end = asyncio.get_running_loop().time() + interval
            while not self._stop_event.is_set() and asyncio.get_running_loop().time() < end:
                await asyncio.sleep(0.1)


manager = NotificationManager()
