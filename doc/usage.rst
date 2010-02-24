.. _overview_toplevel:

============
Using Rocket
============

Usage
=====

There are two methods of invoking Rocket.  The first is the native method which exposes the full capabilities of Rocket to the developer.

::

    from rocket import Rocket
    from wsgiref import demo_app

    server = Rocket(('127.0.0.1', 80), 'wsgi', {wsgi_app:demo_app})
    server.start()

The second is a simple CherryPy adapter to make Rocket work as a drop-in replacement for the CherryPy WSGI server.

::

    from rocket import CherryPyWSGIServer
    from wsgiref import demo_app

    server = CherryPyWSGIServer(('127.0.0.1', 80), demo_app)
    server.start()
    
See the `API Reference`_ below for more details on all available options.  Also the source distribution contains an examples directory with a ready-to-run example of each method type.

Logging
=======

Rocket uses the standard Python logging module for logging.  It provides three classes of logs:

    1) "Rocket.Requests" - HTTP Requests are logged here at the *INFO* level.
    2) "Rocket.Errors" - Errors are logged here at the appropriate level.
    3) "Rocket" - This log class will encompass all log messages

To log messages to a file, do something like this before running Rocket().start()::

    import logging
    import logging.handlers
    log = logging.getLogger('Rocket')
    log.setLevel(logging.INFO)
    log.addHandler(logging.handlers.FileHandler('rocket.log'))

API Reference
=============

Classes
-------

Rocket(interfaces_, method_, app_info_, min_threads_, max_threads_, queue_size_, timeout_)

.. _interfaces:

* interfaces_ - Either a tuple or list of tuples that specify the listening socket information.  Each tuple contains a string-based IP address, an integer port number and, optionally, a key file path and a certificate file path.  For example::

    ('127.0.0.1', 80)

 will serve only to localhost on port 80.  To serve on all interfaces, specify the IP address of **0.0.0.0** along with the desired port number.  interfaces_ can also be a list of such tuples specifying all interfaces on which the Rocket server will respond to requests. For example::

    [('0.0.0.0', 80),
     ('0.0.0.0', 443, 'server_key.pem', 'server_cert.pem')]

 will serve HTTP on port 80 to clients from any address and HTTPS on port 443 to clients from any address.  Note that if you are using Rocket on a version of Python less than 2.6, you will have to install the `ssl module <http://pypi.python.org/pypi/ssl>`_ manually since the HTTPS feature depends on it.  

 **NOTE:** The CherryPyWSGIServer_ adapter does not support SSL in the typical way that CherryPy's server does.  Instead, pass an interfaces_-like list or tuple to CherryPyWSGIServer_ and it will be handled as Rocket does natively.

.. _method:

* method_ - A string value indicating the type of Worker to use to answer the requests received by Rocket.  The default is **wsgi** and will invoke the WSGIWorker class for handling requests.  Go to the Methods_ section to see all available methods.

.. _app_info:

* app_info_ - A dictionary that holds information that the Worker class specified in *method* will use for configuration.  See the documentation in the Methods_ section for the Worker class you are using for details on what to put in this dictionary.

.. _Methods: methods.html#methods

.. _WSGIWorker: methods.html#wsgiworker

.. _min_threads:

* min_threads_ - An integer number of minimum Worker threads to run.  This number must be greater than 0.  Rocket will always have at least *min_threads* number of threads running at a time unless it is in the process of shutting down.

.. _max_threads:

* max_threads_ - An integer number of maximum Worker threads.  This number must be greater than min_threads_ or 0.  A max_threads_ of 0 (zero) indicates there to be no maximum thread count.  Rocket will continue generating threads so long as there are unanswered connections in the request queue.  If the running environment is limited by how many threads a process can own, consider that in addition to max_threads_ there will also be a monitor thread and listening thread running.

.. _queue_size:

* queue_size_ - An integer number of connections allowed to be queued before Rocket accepts them.  This number is passed to the *listen()* function in the operating system's socket library.  It defaults to **None** which either uses the operating system's maximum or 5 if the OS max is not discoverable.

.. _timeout:

* timeout_ - An integer number of seconds to listen to a connection for a new request before closing it.  Defaults to **600**.



.. _CherryPyWSGIServer:

CherryPyWSGIServer(interface_, wsgi_app_, numthreads_, server_name_, max_, request_queue_size_, timeout_, shutdown_timeout_)

.. _interface:

* interface_ - equivalent to one tuple of interfaces_ above

.. _wsgi_app:

* wsgi_app_ - the WSGI application for Rocket to serve.

.. _numthreads:

* numthreads_ - equivalent to min_threads_ above

.. _server_name:

* server_name_ - *Not Used* - Rocket uses it's own server name.

.. _max:

* max_ - equivalent to max_threads_ above

.. _request_queue_size:

* request_queue_size_ - equivalent to queue_size_ above

.. _timeoutq:

* timeout_ - equivalent to timeout_ above but defaults to **10**.

.. _shutdown_timeout:

* shutdown_timeout_ - *Not Used* - Rocket's shutdown mechanism works differently and does not require a timeout.

Instances
---------

An instance of Rocket (or CherryPyWSGIServer) two methods for external use:

* start() - Start the main server loop.  This call will block until server execution is interrupted by:
    - KeyboardInterrupt for a server running in a console.
    - The process receives a SIGTERM or SIGHUP signal for platforms that support signals.
    - A running thread signals the server to stop.
    - An external thread calls the stop_ method.

.. _stop:

* stop(stoplogging=True) - This method will:
    - timeout and close all active connections
    - stop all worker and monitor threads
    - if the *stoplogging* parameter is set to **False**, all logging objects will be preserved should the server be restarted.

Architecture Considerations
===========================

The Short Story
---------------

For Jython running **CPU-bound** applications, use 1.5 times the number of CPU cores for both min_threads_ and max_threads_.

For cPython, use a reasonable number of min_threads_ (10 for a small server or development server, 64 for a production server) with no limit set to max_threads_.


Explanation
-----------

Rocket is tested to run with both cPython and Jython.  Which are very different platforms from a concurrency perspective.  This has an impact on how Rocket should be configured on each platform.

Because of its GIL, cPython keeps one process on one CPU regardless of the number of running threads.  Threads are used in cPython to allow other work to go on while some portions are blocked on external operations such as database queries or file reads.  For this reason, it is advantageous to have a large number of threads running.

Jython, on the other hand, has no GIL and is fully multi-threaded with fine-grained locking.  The downside of this is that many threads will sit and lock on global resources.  Starvation is a major problem for **CPU-bound** servers with a high number of threads.  If your web application is largely I/O bound, then a large number of threads is perfectly fine.  But for CPU-bound applications, having a large number of threads will dramatically decrease the performance of Rocket on Jython.  The recommended number for max_threads_ for Rocket on CPU-bound applications is 1.5 * the number of CPU-cores.  For example, a server with 2 dual-core processors has 4 cores.  The recommended maximum number of threads for Jython would be 6 for CPU-bound applications.  Since this is such a low number compared to the cPython recommendations, setting max_threads_ and min_threads_ to an equal number will prevent the threadpool from dynamically flexing the thread pool (thus saving a little more processor power).

