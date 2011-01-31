# -*- coding: utf-8 -*-

# This file is part of the Rocket Web Server
# Copyright (c) 2011 Timothy Farrell

# Import System Modules
import time
try:
    from concurrency.futures import Future, ThreadPoolExecutor
    from concurrent.futures.thread import _WorkItem
    has_futures = True
except ImportError:
    has_futures = False
    class Future:
        pass

class WSGIFuture(Future):
    def __init__(self, f_dict, *args, **kwargs):
        Future.__init__(self, f_dict, *args, **kwargs)

        self.timeout = None

        self._mem_dict = f_dict
        self._lifespan = None
        self._name = None
        self._start_time = time.time()

    def set_running_or_notify_cancel(self):
        if self._start_time - time.time() >= self._lifespan:
            self.cancel()
        else:
            return super().set_running_or_notify_cancel()


    def remember(self, name, lifespan=None, errors='raise'):
        self._lifespan = None

        if name in self._mem_dict:
            if errors == 'raise':
                msg = 'Cannot remember future by name "%s".  ' + \
                      'A future already exists with that name.'
                raise KeyError(msg % name)

            if errors == 'ignore':
                return self

            if not errors.startswith('replace'):
                msg = '"Unknown error-handling method "%s".'
                raise AttributeError(msg % errors)

            if errors == 'replaceAndCancel':
                self._mem_dict[name].cancel()

        # Here either there is no named future, or the caller wishes to replace
        # it (i.e. error == 'replace')
        self._name = name
        self._mem_dict[name] = self

        return self

    def forget():
        if name in self._mem_dict and self._mem_dict[name] is self:
            del self._mem_dict[name]
            self._name = None

class _WorkItem(object):
    def __init__(self, future, fn, args, kwargs):
        self.future = future
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def run(self):
        if not self.future.set_running_or_notify_cancel():
            return

        try:
            result = self.fn(*self.args, **self.kwargs)
        except BaseException:
            e = sys.exc_info()[1]
            self.future.set_exception(e)
        else:
            self.future.set_result(result)

class WSGIExecutor(ThreadPoolExecutor):
    multithread = True
    multiprocess = False

    def __init__(self, *args, **kwargs):
        ThreadPoolExecutor.__init__(self, *args, **kwargs)

        self.futures = dict()

    def submit(self, fn, *args, **kwargs):
        with self._shutdown_lock:
            if self._shutdown:
                raise RuntimeError('cannot schedule new futures after shutdown')

            f = WSGIFuture(self.futures)
            w = _WorkItem(f, fn, args, kwargs)

            self._work_queue.put(w)
            self._adjust_thread_count()
            return f
