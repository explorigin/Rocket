# -*- coding: utf-8 -*-

import os
from ..worker import Worker

class FileWorker(Worker):
    def run_app(self, environ, sock_file):
        first_line = sock_file.readline().decode('ISO-8859-1')
        request = first_line.split(' ')

        path_info = request[1]

        file_path = os.path.abspath(os.path.normpath(path_info))

        if os.path.isfile(file_path):
            self.status = '200 OK'
            self.headers = [('Content-type','text/plain')]
            return [open(file_path, 'rb').read()]
        else:
            self.status = '404 Not Found'
            self.headers = []

        return [b'404 Not Found']
