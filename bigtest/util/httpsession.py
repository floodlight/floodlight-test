#!/usr/bin/env python
"""
This module provides support for mimicking a client HTTP session that spans
a number of requests.

Instances of the HTTPSession class contain a pool of cookies and standard
headers, and allow the creation of HTTP request objects that refer to the
session.

References

- HTTP Protocol: http://www.w3.org/Protocols/rfc1945/rfc1945
- File upload:   http://www.magres.nottingham.ac.uk/cgi-bin/rfc/1867
"""

import string, httplib, urlparse, urllib, mimetools, base64
import bigtest

# If the following module (Timothy O'Malley's Cookie module) is missing, try
#   http://www.google.com/search?q=cookie.py"
# (Python >= 2 has this module in the standard library.)
import Cookie

try: from cStringIO import StringIO
except: from StringIO import StringIO

__author__ = 'Steve Purcell'
__version__ = '$Revision: 1.6 $'[11:-2]
__email__ = 'stephen_purcell@yahoo.com'

##############################################################################
# Query string/parameter parsing
##############################################################################

def query_string_to_param_list(querystr):
    """Take a url-encoded query string and convert to a list of tuples.

    Each tuple is in the form (name, value), where 'value' will be None if
    the corresponding parameter in the query string was not in the form 'a=b'.
    """
    params = []
    for param in string.split(querystr, '&'):
        if not param:
            continue
        parts = map(urllib.unquote_plus, string.split(param, '='))
        if len(parts) == 2:
            name, value = parts
        else:
            name, value = parts[0], None
        params.append((name, value))
    return params

def param_list_to_query_string(params):
    """Takes a list of parameter tuples and returns a url-encoded string.

    Each tuple is in the form (name, value), where 'value' can be None if
    the corresponding parameter in the query string is not to be in
    the form 'a=b'.
    """
    encoded = []
    for key, value in params:
        if value is None:
            encoded.append(urllib.quote_plus(key))
        else:
            encoded.append("%s=%s" % tuple(map(urllib.quote_plus, (key, value))))
    return string.join(encoded, '&')



##############################################################################
# Standard request classes
##############################################################################

class HTTPRequestError(Exception):
    """Error thrown in response to misuse of API or internal failure"""
    pass


class HTTPRequest:
    """Base class for HTTP requests that are made in the context of a
    session instance. Cannot be used directly.
    """
    follow_redirects = 0

    def __init__(self, session, url):
        self.session = session
        self.redirects = 0
        self._extra_headers = []
        self._init_request(url)

    def _init_request(self, url):
        self.url = url
        try:
            (self.scheme, self.server, self.path, self.params,
             query, self.fragment) = urlparse.urlparse(url)
        except TypeError:
            raise HTTPRequest, 'illegal URL: %s' % url
        self.query_params = query_string_to_param_list(query)
        if not self.scheme:
            raise HTTPRequestError, 'not a full url: %s' % url
        elif self.scheme == 'http':
            self._request = httplib.HTTP()
        elif self.scheme == 'https' and hasattr(httplib, 'HTTPS'):
            self._request = httplib.HTTPS()
        else:
            raise HTTPRequestError, 'unsupported url scheme %s' % self.scheme
        if self.session.debug_level > 1:
            self._request.set_debuglevel(1)
        self._finished = 0

    def get_query_param(self, key):
        for param, value in self.query_params:
            if param == key:
                return value
        raise KeyError, key

    def _get_path(self):
        if self.query_params:
            query_string = param_list_to_query_string(self.query_params)
            return "%s?%s" % (self.path, query_string)
        else:
            return self.path

    def _finish_request(self):
        if self._finished:
            return
        selector = self._get_path()
        self.session._debug("begin %s request: %s" %
                            (self.request_type, selector))
        self.url = urlparse.urljoin(self.url, selector)
        self._request.connect(self.server)
        self._request.putrequest(self.request_type, selector)
        self._send_headers(self.session.get_headers_for(self.server, selector))
        self._send_headers(self._extra_headers)
        self._send_body()
        reply = self._request.getreply()
        if reply[0] == -1:
            raise HTTPRequestError, \
                  'illegal response from server: %s' % reply[1]
        self.replycode, self.message, self.replyheaders = reply
        self.session._debug("got response: %s: %s" %
                            (self.replycode, self.message))
        self._extract_cookies(self.replyheaders)
        if self.replycode in (301, 302) and self.follow_redirects:
            self.redirects = self.redirects + 1
            if not self.replyheaders.has_key('location'):
                raise HTTPRequestError, 'redirected, but no location in headers'
            location = self.replyheaders['location']
            self.session._debug("redirecting to: %s" % location)
            self._init_request(self.resolve_href(location))
            self._finish_request()
        self._finished = 1

    def _send_headers(self, headers):
        for header, value in headers:
            self._send_header(header, value)

    def _send_header(self, header, value):
        self.session._debug("sending header: %s: %s" % (header, value))
        self._request.putheader(header, value)

    def _send_body(self):
        pass

    def query_string(self):
        return param_list_to_query_string(self.query_params)

    def add_query_param(self, key, value):
        self.query_params.append((key,value))

    def add_query_params(self, dict):
        for key, value in dict.items():
            self.add_query_param(key, value)

    def resolve_href(self, href):
        return urlparse.urljoin(self.url, href)

    def redirect(self):
        self._finish_request()
        if self.replycode in (301, 302):
            return self.replyheaders['location']
        else:
            return None

    add_param = add_query_param

    def add_params(self, dict):
        for key, value in dict.items():
            self.add_param(key, value)

    def getfile(self):
        self._finish_request()
        return self._request.getfile()

    def _extract_cookies(self, headers):
        for cookie in headers.getallmatchingheaders('set-cookie'):
            self.session.add_cookie(self.server, cookie)

    def getreply(self):
        self._finish_request()
        return self.replycode, self.message, self.replyheaders


class GetRequest(HTTPRequest):
    request_type = 'GET'
    follow_redirects = 1

    def _send_body(self):
        self._request.endheaders()


class PostRequest(HTTPRequest):
    request_type = 'POST'
    follow_redirects = 0

    def _init_request(self, url):
        self.post_params = []
        HTTPRequest._init_request(self, url)

    def add_param(self, key, value):
        self.post_params.append((key, value))

    def _send_body(self):
        self._send_header('Content-Type', 'application/x-www-form-urlencoded')
        content = param_list_to_query_string(self.post_params)
        self._send_header('Content-Length', str(len(content)))
        self._request.endheaders()
        self._request.send(content)


class PostMultipartRequest(PostRequest):
    def _init_request(self, url):
        self.post_files = []
        self._boundary = '-' * 16 + mimetools.choose_boundary()
        PostRequest._init_request(self, url)

    def add_file(self, name, filename, content_type, stream):
        self.post_files.append((name, filename, content_type, stream))

    def _send_body(self):
        body = StringIO()
        start_boundary = '--' + self._boundary
        end_boundary = start_boundary + '--'
        for key, value in self.post_params:
            body.write(start_boundary + '\r\n')
            body.write('Content-Disposition:  form-data; name="%s"\r\n' % key)
            body.write('\r\n')
            if value is not None:
                body.write(value)
            body.write('\r\n')

        for name, filename, content_type, stream in self.post_files:
            body.write(start_boundary + '\r\n')
            body.write('Content-Disposition: form-data; name="%s"; filename="%s"\r\n'
                       % (name, filename))
            body.write('Content-Type: %s\r\n' % content_type)
            #body.write('Content-Transfer-Encoding: binary\r\n')
            body.write('\r\n')
            while 1:
                data = stream.read(512)
                if not data: break
                body.write(data)
            stream.close()
            body.write('\r\n')
        body.write(end_boundary + '\r\n')
        content = body.getvalue()
        self._send_header('Content-Type', 'multipart/form-data; boundary="%s"' %
                        self._boundary)
        self._send_header('Content-Length', str(len(content)))
        self._request.endheaders()
        self._request.send(content)
        body.close()


class HTTPSession:
    def __init__(self, use_cookies=1, debug_level=0):
        self.cookies = Cookie.SmartCookie()
        self.use_cookies = use_cookies
        self.debug_level = debug_level
        self.standard_headers = []
        self.authorisation = None

    def _debug(self, msg, level=1):
        if self.debug_level >= level:
            print msg

    def set_basic_auth(self, user, password):
        if user is None:
            self.authorisation = None
        else:
            self.authorisation = (user, password)

    def add_header(self, header, value):
        self.standard_headers.append((header, value))

    def add_cookie(self, server, header):
        header = string.strip(header)
        new_cookies = Cookie.SmartCookie()
        new_cookies.load(header)
        for cookie in new_cookies.values():
            if not cookie.get('domain', None):
                cookie['domain'] = string.lower(server)
            bigtest.Assert(len(cookie['domain']) > 0)
        self.cookies.update(new_cookies)
        self._debug("added cookie: server=%s, header=%s" % (server, header))

    def get(self, *args, **kwargs):
        return apply(GetRequest, (self,) + args, kwargs)

    def post(self, *args, **kwargs):
        return apply(PostRequest, (self,) + args, kwargs)

    def post_multipart(self, *args, **kwargs):
        return apply(PostMultipartRequest, (self,) + args, kwargs)

    def _cookie_matches(self, cookie, server, path):
        return self._domains_match(server, cookie['domain']) and \
               self._paths_match(path, cookie['path'])

    def _domains_match(self, domain, cookie_domain):
        domain = string.lower(domain)
        cookie_domain = string.lower(cookie_domain)
        if domain == cookie_domain:
            return 1
        elif cookie_domain[0] == '.':
            index = string.find(domain, cookie_domain)
            if index != -1 and (len(domain) - index) == len(cookie_domain):
                return 1
        return 0

    def _paths_match(self, path, cookie_path):
        path = string.split(path, '/')
        cookie_path = string.split(cookie_path, '/')
        if cookie_path[-1] != '':
            return 0  ## invalid cookie!
        cookie_path = cookie_path[:-1]
        if path == cookie_path:
            return 1
        if len(path) < len(cookie_path):
            return 0
        if path[:len(cookie_path)] == cookie_path:
            return 1
        return 0

    def get_headers_for(self, server, path):
        headers = self.standard_headers[:]
        if self.authorisation:
            authstr = base64.encodestring("%s:%s" % self.authorisation)[:-1]
            headers.append(("Authorization", "Basic " + authstr))
        if self.use_cookies and self.cookies.values():  # TODO: fix path matching...
            cookies = []
            for cookie in self.cookies.values():
                if self._cookie_matches(cookie, server, path):
                    cookies.append(cookie.output(attrs=(), header=''))
            headers.append(("Cookie", string.join(cookies,'')))
        return headers


