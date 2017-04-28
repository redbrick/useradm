#!/usr/bin/env python3
"""Test server for rrs cgi running on port 8000"""

import http.server
import cgitb

cgitb.enable()  ## This line enables CGI error reporting

server = http.server.HTTPServer
handler = http.server.CGIHTTPRequestHandler
server_address = ("", 8000)

class Handler(http.server.CGIHTTPRequestHandler):
    """Handler for cgi requests"""
    def is_cgi(self):
        self.cgi_info = '', self.path[1:]
        if self.path[1:].startswith("rrs.cgi"):
            return True
        return False

httpd = server(server_address, Handler)
httpd.serve_forever()
