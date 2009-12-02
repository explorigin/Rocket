=========
Extending
=========

Rocket can be extended to handle multiple middle-ware applications.  

To do so, create a module in the methods subdirectory.  The module should specify a subclass of the Worker_ class.  The subclass should overload Worker's run_app method.  run_app is passed a single parameter, a Connection instance for the requesting client.  run_app is responsible for reading the complete request from the Connection and writing a complete response.  run_app should leave the connection in a state ready to receive another request.  If the client closes the connection or run_app needs to close a connection, it should set the self.closeConnection property to True and return.  It can optionally raise SocketTimeout to put the Connection in the wait_queue.  The app_info_ parameter passed to Rocket will be available as self.app_info.  app_info_ should be treated as read_only since all Worker_ threads use it.

WSGIWorker
==========

.. _WSGIWorker_app_info:

The *app_info* property for the WSGIWorker method should contain a single key, value pair::

  {'wsgi_app': wsgi_app}
  
**wsgi_app** represents the WSGI application for Rocket to serve.

.. _Worker: design.html#worker
.. _app_info: usage.html#app-info