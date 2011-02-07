# -*- coding: utf-8 -*-

import logging
from rocket import Rocket, b
from cgi import parse_qs
import time

def wait(duration=5):
    time.sleep(duration)
    return duration


def wsgiapp(environ, start_response):
    base_page = '''<html><head><title>Futures Demonstration</title></head><body>%s<br /><a href="/">Home</a></body></html>'''
    home_content = '''<h1>Futures Demonstration</h1><h2>Current Futures</h2>%s

<h2>Start a new future</h2>
<form action="/start" method="GET">
    <input name="name" type="text" placeholder="Future name"/>
    <input name="duration" type="text" placeholder="Duration (seconds)"/>
    <input type="submit" />
</form>'''

    def format_future_link(name, future):
        tpl = '''<a href="/result?name=%s">%s - %s</a>'''
        return tpl % (name, name, future._state)

    path_list = [x for x in environ['PATH_INFO'].split('/') if x]
    vars = parse_qs(environ['QUERY_STRING'])

    if 'wsgiorg.executor' not in environ:
        start_response('200 OK', [('Content-Type', 'text/html')])
        return [b("futures not supported")]
    else:
        executor = environ['wsgiorg.executor']
        futures = environ['wsgiorg.futures']

    data = base_page

    if len(path_list) == 0:
        data %= home_content % "<br/>".join([format_future_link(n, f) for n,f in futures.items()])
    elif len(path_list) == 1:
        if path_list[0] == "start" and 'name' in vars:
            try:
                f = executor.submit(wait, int(vars.get("duration", ["10"])[0]))
                if 'name' in vars:
                    f.remember(vars['name'][0])
                    data %= "\n\nJob remembered as: " + vars['name'][0]
                else:
                    data %= "\n\nJob Submitted"
            except NameError:
                data %= "\n\nJob already exists with name: " + vars['name'][0]
        elif path_list[0] == "result" and 'name' in vars:
            name = vars['name'][0]
            if name not in futures:
                data %= "No future named %s available." % name
            else:
                data %= "%s = %s" % (name, futures[name].result())
                futures[name].forget()

        else:
            data %= "\n\nUnknown action"



    start_response('200 OK', [('Content-Type', 'text/html')])
    return [b(data)]


if __name__ == '__main__':
    log = logging.getLogger('Rocket')
    log.setLevel(logging.DEBUG)
    fmt = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
    h = logging.StreamHandler()
    h.setFormatter(fmt)
    log.addHandler(h)

    app_info = dict(wsgi_app=wsgiapp,
                    futures=True)
    Rocket(interfaces=[('127.0.0.1', 80)],
           method='wsgi',
           app_info=app_info,
           max_threads=1,
           min_threads=1).start()
