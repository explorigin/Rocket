
=======
Methods
=======

Rocket uses *Methods* as a way to serve different types of content.  Currently there are two methods:

* `fs`_ - Serves files from a specified directory.
* `wsgi`_ - Serves a `WSGI <http://www.python.org/dev/peps/pep-3333/>`_-compliant application.

.. _wsgiworker:

WSGI
====

The *wsgi* method is implemented by the WSGIWorker class.

.. _WSGIWorker_app_info:

The *app_info* property for the WSGIWorker should be a dictionary containing the following:

* wsgi_app: an instance of the WSGI application Rocket should serve.
* futures: a boolean value to include experimental futures environment variables.  See extras_ for more details.

.. _extras: extras.html

.. _WSGIWorker_environment_variables:

Rocket provides the following environment variables to applications that it runs in addition to WSGI's `standard environment variables <http://www.python.org/dev/peps/pep-3333/#environ-variables>`_:

* **REMOTE_PORT** - the port from which the client computer is connecting.

* **REMOTE_ADDR** - the IP address of the device directly connected to the server.  Note: IP addresses can be spoofed or hidden behind a proxy, NAT device or redirector.  This IP address is not guaranteed to reflect the true client's IP address.

*Since Rocket does not currently support HTTP-authentication, REMOTE_USER is never provided.*

* **wsgiorg.executor**
* **wsgiorg.futures** - These two environment variables are provide if, Rocket is running on a Python distribution that includes futures and the futures option in app_info is explicitly set to **True**.

.. _Worker: design.html#worker
.. _app_info: usage.html#app-info


FS
==

The *fs* method is implemented by the FileSystemWorker class.

The *app_info* property for the FileSystemWorker should contain the following:

* document_root: a string-value path to the directory that will serve as the root for serving files.
* display_index: a boolean-value indicating if an HTML index of a directory should be served if a directory is requested.
