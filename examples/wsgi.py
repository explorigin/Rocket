# -*- coding: utf-8 -*-

import logging
from wsgiref.simple_server import demo_app
from rocket import Rocket

if __name__ == '__main__':
    log = logging.getLogger('Rocket')
    log.setLevel(logging.DEBUG)
    fmt = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
    h = logging.StreamHandler()
    h.setFormatter(fmt)
    log.addHandler(h)
    Rocket(interfaces=[('127.0.0.1', 80), ('127.0.0.1', 443, 'mybad.pem', 'mycert.pem')],
           method='wsgi',
           app_info={"wsgi_app": demo_app},
           min_threads=2,
           max_threads=10,
           timeout=60).start()
