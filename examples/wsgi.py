# -*- coding: utf-8 -*-

import logging
from wsgiref.simple_server import demo_app
from rocket import Rocket

if __name__ == '__main__':
    log = logging.getLogger('Rocket.Requests')
    log.setLevel(logging.INFO)
    fmt = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
    h = logging.StreamHandler()
    h.setFormatter(fmt)
    log.addHandler(h)
    Rocket(interfaces=('127.0.0.1', 80),
           method='wsgi',
           app_info={"wsgi_app": demo_app},
           min_threads=64,
           max_threads=128,
           timeout=60).start()
