"""Wait for owned work before propagating cancellation or releasing protection."""
import asyncio


async def drain(awaitable):
    task = asyncio.ensure_future(awaitable)
    cancelled = False
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            cancelled = True
        except Exception:
            break
    # Retrieve failures even when the caller was cancelled.
    if cancelled:
        if not task.cancelled():
            task.exception()
        raise asyncio.CancelledError()
    return task.result()


async def blocking(function, *args, **kwargs):
    return await drain(asyncio.to_thread(function, *args, **kwargs))
