#!/usr/bin/env python3
"""Test server for rrs cgi running on port 8000"""

import cgitb
import http.server

cgitb.enable()  # This line enables CGI error reporting

SERVER = http.server.HTTPServer
HANDLER = http.server.CGIHTTPRequestHandler
SERVER_ADDRESS = ("", 8000)


class Handler(http.server.CGIHTTPRequestHandler):
    """Handler for cgi requests"""

    def is_cgi(self):
        self.cgi_info = '', self.path[1:]
        if self.path[1:].startswith("rrs.cgi"):
            return True
        return False


HTTPD = SERVER(SERVER_ADDRESS, Handler)
HTTPD.serve_forever()
