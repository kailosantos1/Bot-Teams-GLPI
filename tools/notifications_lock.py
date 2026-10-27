"""OS-owned, non-expiring lock shared by manager and CLI for one database.

The inode/file must remain in place, including after release. OS process exit
releases the lock; a leftover file is not evidence of a running worker.
"""
import os
from pathlib import Path


class SingleInstanceLock:
    def __init__(self, database):
        self.lockfile = str(Path(database).resolve()) + '.notifications.lock'
        self._file = None
        self._windows = os.name == 'nt'

    def acquire(self):
        if self._file is not None:
            return True
        handle = open(self.lockfile, 'a+b')
        try:
            if self._windows:
                import msvcrt
                # Lock exactly byte zero, even for an initially empty file.
                handle.seek(0, os.SEEK_END)
                if handle.tell() == 0:
                    handle.write(b'\0')
                    handle.flush()
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            handle.close()
            return False
        except BaseException:
            handle.close()
            raise
        self._file = handle
        return True

    def release(self):
        handle, self._file = self._file, None
        if handle is None:
            return
        try:
            if self._windows:
                import msvcrt
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()
