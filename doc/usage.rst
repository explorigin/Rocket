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

* *interfaces* - Either a tuple or list of tuples that specify the listening socket information.  Each tuple contains a string-based IP address and an integer port number.  For example::
   
    ('127.0.0.1', 80)
    
 will serve only to localhost on port 80.  To serve on all interfaces, specify the IP address of **0.0.0.0** along with the desired port number.  *interfaces* is a list of such tuples specifying all interfaces on which the Rocket server will respond to requests.  *interfaces* defaults to the value of **('127.0.0.1', 8000)** and is intended for testing purposes.  *Note that some operating systems require special privileges in order to serve on sockets 1-1024.*

* *method* - A string value indicating the type of Worker to use to answer the requests received by Rocket.  The default is **'wsgi'** and will invoke the WSGIWorker class for handling requests.  Currently this is the only option.  In the future more handlers could be added.

* *app_info* - A dictionary that holds information that the Worker class specified in *method* will use for configuration.  See the documentation for the Worker class you are using for specifics on what to put in this dictionary.

* *min_threads* - An integer number of minimum Worker threads to run.  This number must be greater than 0.  Rocket will always have at least *min_threads* number of threads running at a time unless it is in the process of shutting down.

* *max_threads* - An integer number of maximum Worker threads.  This number must be greater than *min_threads* or 0.  A *max_threads* of 0 (zero) indicates there to be no maximum thread count.  Rocket will continue generating threads so long as there are unanswered connections in the request queue.  If the running environment is limited by how many threads a process can own, consider that in addition to *max_threads* there will also be a monitor thread and listening thread running.

* *queue_size* - An integer number of connections allowed to be queued before Rocket accepts them.  This number is passed to the *listen()* function in the operating system's socket library.  It defaults to **None** which either uses the operating system's maximum or 5 if the OS max is not discoverable.

CherryPyWSGIServer(*interface*, *wsgi_app*, *numthreads*, *server_name*, *max*, *request_queue_size*, *timeout*, *shutdown_timeout*)

* *interface* - equivalent to one tuple of *interfaces* above
* *wsgi_app* - the WSGI application for Rocket to serve
* *numthreads* - equivalent to *min_threads* above
* *server_name* - *Not Used* - Rocket uses it's own server name.
* *max* - equivalent to *max_threads* above
* *request_queue_size* - equivalent to *queue_size* above
* *shutdown_timeout* - *Not Used* - Rocket's shutdown mechanism works differently and does not require a timeout.

