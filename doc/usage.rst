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

API Reference
=============

Rocket(*interfaces*, *method*, *app_info*, *min_threads*, *max_threads*, *queue_size*)

.. _interfaces:

* interfaces_ - Either a tuple or list of tuples that specify the listening socket information.  Each tuple contains a string-based IP address and an integer port number.  For example::
   
    ('127.0.0.1', 80)
    
 will serve only to localhost on port 80.  To serve on all interfaces, specify the IP address of **0.0.0.0** along with the desired port number.  interfaces_ is a list of such tuples specifying all interfaces on which the Rocket server will respond to requests.  interfaces_ defaults to the value of **('127.0.0.1', 8000)** and is intended for testing purposes.  *Note that some operating systems require special privileges in order to serve on sockets 1-1024.*

.. _method:

* method_ - A string value indicating the type of Worker to use to answer the requests received by Rocket.  The default is **'wsgi'** and will invoke the WSGIWorker class for handling requests.  Currently this is the only option.  In the future more handlers could be added.

.. _app_info:

* app_info_ - A dictionary that holds information that the Worker class specified in *method* will use for configuration.  See the documentation for the Worker class you are using for specifics on what to put in this dictionary.

.. _min_threads:

* min_threads_ - An integer number of minimum Worker threads to run.  This number must be greater than 0.  Rocket will always have at least *min_threads* number of threads running at a time unless it is in the process of shutting down.

.. _max_threads:

* max_threads_ - An integer number of maximum Worker threads.  This number must be greater than min_threads_ or 0.  A max_threads_ of 0 (zero) indicates there to be no maximum thread count.  Rocket will continue generating threads so long as there are unanswered connections in the request queue.  If the running environment is limited by how many threads a process can own, consider that in addition to max_threads_ there will also be a monitor thread and listening thread running.

.. _queue_size:

* queue_size_ - An integer number of connections allowed to be queued before Rocket accepts them.  This number is passed to the *listen()* function in the operating system's socket library.  It defaults to **None** which either uses the operating system's maximum or 5 if the OS max is not discoverable.

.. _CherryPyWSGIServer:

CherryPyWSGIServer(*interface*, *wsgi_app*, *numthreads*, *server_name*, *max*, *request_queue_size*, *timeout*, *shutdown_timeout*)

.. _interface:

* *interface* - equivalent to one tuple of interfaces_ above

.. _wsgi_app:

* *wsgi_app* - the WSGI application for Rocket to serve

.. _numthreads:

* *numthreads* - equivalent to min_threads_ above

.. _server_name:

* *server_name* - *Not Used* - Rocket uses it's own server name.

.. _max:

* *max* - equivalent to max_threads_ above

.. _request_queue_size:

* *request_queue_size* - equivalent to queue_size_ above

.. _shutdown_timeout:

* *shutdown_timeout* - *Not Used* - Rocket's shutdown mechanism works differently and does not require a timeout.

Architecture Considerations
===========================

The Short Story
---------------

For Jython running CPU bound applications, use 1.5 times the number of CPU cores for both min_threads_ and max_threads_.

For cPython, use a reasonable number of min_threads_ (10 for a small server or development server, 64 for a production server) with no limit set to max_threads_.


Explanation
-----------

Rocket is tested to run with both cPython and Jython.  Which are very different platforms from a concurrency perspective.  This has an impact on how Rocket should be configured on each platform.

Because of its GIL, cPython is keeps one process on one CPU regardless of the number of running threads.  Threads are used in cPython to allow other work to go on while some portions are blocked on external (to Python) operations.  For this reason, it is advantageous to have a large number of threads running.

Jython, on the other hand, has no GIL and is fully multi-threaded with fine-grained locking.  The downside of this is that many threads will sit and lock on global resources.  Starvation is a major problem for CPU-bound servers.  If your web application is largely I/O bound, then a large number of threads is perfectly fine.  But for CPU bound applications, having a large number of threads will dramatically decrease the performance of Rocket on Jython.  The recommended number for max_threads_ for Rocket on CPU-bound applications is 1.5 * the number of CPU-cores.  For example, a server with 2 dual-core processors has 8 cores.  The recommended maximum number of threads for Jython would be 12.  Since this is such a low number, setting max_threads_ and min_threads_ to an equal number will prevent the threadpool from dynamically flexing the thread pool (thus saving a little more processor power).

