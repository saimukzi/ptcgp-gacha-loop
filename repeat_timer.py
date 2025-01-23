import atexit
import threading
import traceback

class RepeatTimer:

    def __init__(self, interval, function, args=[], kwargs={}):
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs

        self.condition = threading.Condition()
        self.is_active = False
        self.timer = None
        self.atexit_registered = False
        self.is_atexit = False

    def _run(self):
        if not self.is_active:
            return
        if self.is_atexit:
            return
        try:
            self.function(*self.args, **self.kwargs)
        except:
            traceback.print_exc()
        with self.condition:
            if self.timer is not None:
                self.timer.cancel()
            self.timer = threading.Timer(self.interval, self._run)
            self.timer.start()

    def _atexit(self):
        with self.condition:
            self.is_atexit = True
            self.is_active = False
            if self.timer is not None:
                self.timer.cancel()
            self.timer = None

    def start(self):
        with self.condition:
            self.is_active = True
            if self.timer is not None:
                self.timer.cancel()
            self.timer = threading.Timer(self.interval, self._run)
            self.timer.start()
            if not self.atexit_registered:
                atexit.register(self._atexit)
                self.atexit_registered = True

    def stop(self):
        with self.condition:
            if self.atexit_registered:
                atexit.unregister(self._atexit)
                self.atexit_registered = False
            self.is_active = False
            if self.timer is not None:
                self.timer.cancel()
            self.timer = None
