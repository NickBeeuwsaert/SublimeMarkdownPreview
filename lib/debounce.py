import functools
import threading
from itertools import count
from weakref import WeakValueDictionary

counter = count()


class SetTimeoutFactory:
    def __init__(self):
        self._timers = WeakValueDictionary()

    def __call__(self, callback, timeout):
        id = next(counter)
        condition = threading.Condition()

        def target():
            with condition:
                if condition.wait(timeout):
                    return
            callback()

        self._timers[id] = condition
        thread = threading.Thread(target=target)
        thread.start()
        return id

    def cancel(self, id):
        try:
            condition = self._timers.pop(id)
        except KeyError:
            return
        else:
            with condition:
                condition.notify()


set_timeout = SetTimeoutFactory()


class debounce:
    def __init__(self, timeout):
        self.timeout = timeout
        self.last_id = None

    def __call__(self, fn):
        def _(*args, **kwargs):
            if self.last_id is not None:
                set_timeout.cancel(self.last_id)

            self.last_id = set_timeout(
                functools.partial(fn, *args, **kwargs), self.timeout
            )
            return self.last_id

        return _
