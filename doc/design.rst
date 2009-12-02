======
Design
======

The class design of Rocket consists of a main listener_, a `connection monitor`_, a threadpool_ and the `worker`_ threads that the threadpool manages.

Listener
========

The listener is the main thread of operation.  It handles setup of the listening sockets, connection monitor and threadpool.  Once it has setup these, if enters into a connection accept loop.  Once it has accepted a connection, it puts it in the connection queue to be processed by a worker.

Connection Monitor
==================

The connection monitor collection connections that are in=between requests but not closed.  Whenever a worker is waiting for a new request, it will timeout if no new request comes in.  Upon this timeout, the worker will send this connection to the connection monitor and move on to process another request.  The connection monitor puts the received connection in a set of connections to listen on.  As soon as there is activity on the listened socket, the connection monitor will put the connection back in the active requests queue to be processed by a worker.

ThreadPool
==========

The ThreadPool manages how many active worker threads there are at a given time.  When constructed by the Listener (prior to the listener entering its main loop), the ThreadPool creates *min_threads* number of Worker_ threads.  The number of threads varies from *min_threads* to *max_threads* based on how many requests are waiting in the request queue.  If the number of active threads is greater than *min_threads* and the request queue is empty, Threadpool will reduce the number of active threads slowly until the number of active threads is equal to *min_threads*.

Worker
======

The Worker class grabs a connection from the request queue and processes it until either the client signals to close the connection or the connection times out waiting for a new request.  In the former case, the Worker finishes the request and closes the connection.  In the case of the latter, the Worker places the Connection on the wait queue for the Connection Monitor to watch for activity.  In both cases, it then grabs another request from the request queue and starts the process over.

The Worker class is the class to inherit from when extending Rocket.  While Worker provides basic functions such as reading headers and request lines, Worker is not equipped to fully process any one request.  For this reason, Worker must be sub=classed for each request handling method.  For example the WSGIWorker_ subclass extends Worker to create a valid WSGI environment and pass it on to a supplied WSGI application.
