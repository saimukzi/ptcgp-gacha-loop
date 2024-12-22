import os
import portalocker

from my_logger import logger

def lock(fn, msg):
    try:
        ret = Lock(fn, msg)
        ret.lock()
        return ret
    except Exception as e:
        logger.error(f'lock() failed: {e}')
        return None

class Lock:
    def __init__(self, fn, msg):
        self.fn = fn
        self.msg = msg
        self._lock = None
        self._aq = None

    def lock(self):
        os.makedirs(os.path.dirname(self.fn), exist_ok=True)
        self._lock = portalocker.Lock(self.fn, mode='w', encoding='utf-8', timeout=1)
        self._aq = self._lock.acquire()
        self._aq.write(self.msg)
        self._aq.write('\n')
        self._aq.flush()

    def unlock(self):
        if self._aq:
            self._aq.close()
            self._aq = None
        if self._lock:
            self._lock.release()
            self._lock = None
