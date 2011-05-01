:Title: wsgiorg.executor
:Author: Timothy Farrell <explorigin@gmail.com>
:Discussions-To: Python Web-SIG <web-sig@python.org>
:Status: Draft
:Created: 28-Jan-2011

======
Extras
======

Extras are extensions available for certain methods in Rocket. Currently there is only the Futures draft specification available for the WSGI method.

Futures
=======

** EXPERIMENTAL **

Abstract
--------

This proposes two new standard environment keys ``environ['wsgiorg.executor']`` and ``environ['wsgiorg.futures']``. ``wsgiorg.executor`` will provide a wrapped futures (`PEP 3148`_) executor that a WSGI application may use to register a function to be run outside of the normal WSGI request/response processing. ``wsgiorg.futures`` provides a dictionary that an application can use to reference previously submitted jobs.

.. _PEP 3148: http://www.python.org/dev/peps/pep-3148/

Rationale
---------

As web applications grow in complexity and power, there is a growing need to execute operations related to a request that don't need to finish before the response is fully sent to the client.  Some example use cases are:

 - Send an email
 - Build or clear a cache
 - Vacuum a database

Other applications could run jobs that would span requests such as generating a report or building a custom download.  Subsequent polling requests could check the if the method was finished finding the named future available in ``wsgiorg.futures``

Specification
-------------

This specification defines two new keys that can go in the WSGI environment, ``wsgiorg.executor`` and ``environ['wsgiorg.futures']``.  ``wsgiorg.executor`` is a wrapped futures executor.  There is only one method available to a WSGI application.

``submit(func, \*args,\*\*kwargs)``

    submit `func` to be executed as ``func(\*args, \*\*kwargs)`` in a separate thread/process.  A special future instance is returned.
  
The executor will also have additional properties to indicate the concurrency model.  These values are not mutually-exclusive and may both be true if a server implements such an executor.  The concurrency model of the executor is implementation specific.  These properties are:

``multithread``

    a boolean value indicating if functions may be run in a separate thread from which the function is submitted
    
``multiprocess``

    a boolean value indicating if functions may be run outside of the the process in which the function is submitted.
  
The future instance returned by submit has all of the normal methods of a standard futures instance but also has additional methods:

``remember(name, lifespan, duplicate_behavior="raise")``

    Saves the future in ``wsgiorg.futures`` as ``name`` for up to ``lifespan`` seconds after the function associated with this future has completed.  The ``lifespan`` parameter may be defaulted as a server-specific configuration option.  ``duplicate_behavior`` dictates how the future should respond if there is already a future of the same name listed
  
``forget()``

    Remove thes future from ``wsgiorg.futures``.  This action does not change the state of the future.  A "forgotten" is not necessarily a cancelled future.

The future instance also has an additional property:
  
``timeout``

    a float value property in seconds indicating how long the future will wait in the queue to run.  Just before a function is run, its timeout value is checked.  If the timeout value is less than the time elapsed waiting in the queue, the function will be cancelled.  The default value will be None which means that functions will wait indefinitely to run.
  
``wsgiorg.futures`` is a mapping type of remembered futures.  The key is the name parameter passed to future.remember().  The futures provided must only be previously saved with a call to remember().  WSGI application may only access futures contained in ``wsgiorg.futures``.  Applications must not attempt to delete or overwrite values in ``wsgiorg.futures``.  It is effectively read-only.
  
Limitations
-----------

The nature of running futures brings the possibility of certain deadlock situations.  To avoid deadlocks, submitted functions should never wait on other submitted functions.

Also functions and parameters passed to submit() must abide by the same picklability limitations as the multiprocessing module can handle.

Example
-------

This example is a WSGI application that uses all features of this specification.

::

    from concurrent import futures

    class WsgiOrgFuturesExecutor(futures.ThreadPoolExecutor):
        

    class WsgiOrgFuture(futures.Future):

        def __init__(self):
            self.timeout = None

        def remember(self, name, lifespan=60):
            return self

        def forget(self):
            return self

Example using futures to generate a report::

    # inside a WSGI application...
    
    def buildReport(vars):
        pass
        
    rpt_fut = environ["wsgiorg.executor"].submit(buildReport, data)
    rpt_fut.remember("client-123-report")
    rpt_fut.timeout = 90
