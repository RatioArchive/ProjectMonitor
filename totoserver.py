#!/usr/bin/python

from tornado.web import *
from tornado.ioloop import *
import json
import hashlib
import hmac
import toto
from toto.exceptions import *
from toto.invocation import *
from time import time
from tornado.options import define, options
import base64

define("database", metavar='mysql|mongodb', default="mongodb", help="the database driver to use (default 'mongodb')")
define("mysql_host", default="localhost:3306", help="MySQL database 'host:port' (default 'localhost:3306')")
define("mysql_database", type=str, help="Main MySQL schema name")
define("mysql_user", type=str, help="Main MySQL user")
define("mysql_password", type=str, help="Main MySQL user password")
define("mongodb_host", default="localhost", help="MongoDB host (default 'localhost')")
define("mongodb_port", default=27017, help="MongoDB port (default 27017)")
define("mongodb_database", default="toto_server", help="MongoDB database (default 'toto_server')")
define("port", default=8888, help="The port to run this server on. Multiple daemon servers will be numbered sequentially starting at this port. (default 8888)")
define("bson_enabled", default=False, help="Allows requests to use BSON with content-type application/bson")
define("daemon", metavar='start|stop|restart', help="Start, stop or restart this script as a daemon process. Requires the multiprocessing module.")
define("processes", default=1, help="The number of daemon processes to run, pass 0 to run one per cpu (default 1)")
define("pidfile", default="toto.pid", help="The path to the pidfile for daemon processes will be named <path>.<num>.pid (default toto.pid -> toto.0.pid)")
define("root", default="/", help="The path to run the server on. This can be helpful when hosting multiple services on the same domain (default /)")

tornado.options.parse_config_file("toto.conf")
tornado.options.parse_command_line()

if options.bson_enabled:
  from bson import BSON as bson

class TotoHandler(RequestHandler):

  SUPPORTED_METHODS = ["POST", "OPTIONS"]
  ACCESS_CONTROL_ALLOW_ORIGIN = "*"

  def initialize(self, connection):
    self.connection = connection

  """
    Lookup method by name: a.b.c loads api/a/b/c.py
  """
  def __get_method(self, method_name):
    method_path = method_name.split('.')
    method = toto
    while method_path:
      method = getattr(method, method_path.pop(0))
    return method.invoke

  def options(self):
    allowed_headers = set(['x-toto-hmac','x-toto-session-id','origin','content-type'])
    if 'access-control-request-headers' in self.request.headers:
      allowed_headers = allowed_headers.union(self.request.headers['access-control-request-headers'].lower().replace(' ','').split(','))
    self.add_header('access-control-allow-headers', ','.join(allowed_headers))
    if 'access-control-request-method' in self.request.headers and self.request.headers['access-control-request-method'] not in self.SUPPORTED_METHODS:
      raise HTTPError(405, 'Method not supported')
    self.add_header('access-control-allow-origin', self.ACCESS_CONTROL_ALLOW_ORIGIN)
    self.add_header('access-control-allow-methods', ','.join(self.SUPPORTED_METHODS))
    self.add_header('access-control-expose-headers', 'x-toto-hmac')

  @asynchronous
  def post(self):
    self.session = None
    self.__method = None
    headers = self.request.headers
    response = {}
    use_bson = options.bson_enabled and 'content-type' in headers and headers['content-type'] == 'application/bson'
    self.add_header('access-control-allow-origin', self.ACCESS_CONTROL_ALLOW_ORIGIN)
    self.add_header('access-control-expose-headers', 'x-toto-hmac')
    try:
      if use_bson:
        body = bson(self.request.body).decode()
      else:
        body = json.loads(self.request.body)
      if 'method' not in body:
        raise TotoException(ERROR_MISSING_METHOD, "Missing method.")
      self.__method = self.__get_method(body['method'])
      if 'x-toto-session-id' in headers:
        self.session = self.connection.retrieve_session(headers['x-toto-session-id'], 'x-toto-hmac' in headers and headers['x-toto-hmac'] or None, self.request.body)
      if not 'parameters' in body:
        raise TotoException(ERROR_MISSING_PARAMS, "Missing parameters.")
      response['result'] = self.__method(self, body['parameters'])
    except TotoException as e:
      response['error'] = e.__dict__
    except Exception as e:
      response['error'] = TotoException(ERROR_SERVER, str(e)).__dict__
    if response is not None:
      if use_bson:
        self.add_header('content-type', 'application/bson')
        response_body = str(bson.encode(response))
      else:
        self.add_header('content-type', 'application/json')
        response_body = json.dumps(response)
      if self.session:
        self.add_header('x-toto-hmac', base64.b64encode(hmac.new(str(self.session.user_id), response_body, hashlib.sha1).digest()))
      self.write(response_body)
    if not hasattr(self.__method, 'asynchronous'):
      self.finish()

  def on_connection_close(self):
    if hasattr(self.__method, 'on_connection_close'):
      self.__method.on_connection_close();

def run_server(port):
  connection = None
  if options.database == "mongodb":
    from mongodbconnection import MongoDBConnection
    connection = MongoDBConnection(options.mongodb_host, options.mongodb_port, options.mongodb_database)
  elif options.database == "mysql":
    from mysqldbconnection import MySQLdbConnection
    connection = MySQLdbConnection(options.mysql_host, options.mysql_database, options.mysql_user, options.mysql_password)

  application = Application([
    (options.root, TotoHandler, {'connection': connection}),
  ])

  application.listen(port)
  print "Starting server on port %s" % port
  IOLoop.instance().start()


if __name__ == "__main__":
  if options.daemon:
    import multiprocessing, os
    #convert p to the absolute path, insert ".i" before the last "." or at the end of the path
    def path_with_id(p, i):
      (d, f) = os.path.split(os.path.abspath(p))
      components = f.rsplit('.', 1)
      f = '%s.%s' % (components[0], i)
      if len(components) > 1:
        f += "." + components[1]
      return os.path.join(d, f)

    count = options.processes > 0 and options.processes or multiprocessing.cpu_count()
    if options.daemon == 'stop' or options.daemon == 'restart':
      import signal, re
      pattern = path_with_id(options.pidfile, r'\d+').replace('.', r'\.')
      piddir = os.path.dirname(pattern)
      for fn in os.listdir(os.path.dirname(pattern)):
        pidfile = os.path.join(piddir, fn)
        if re.match(pattern, pidfile):
          with open(pidfile, 'r') as f:
            pid = int(f.read())
            os.kill(pid, signal.SIGTERM)
            print "Stopped server %s" % pid 
          os.remove(pidfile)

    if options.daemon == 'start' or options.daemon == 'restart':
      import sys
      def run_daemon_server(port, pidfile):
        #fork and only continue on child process
        if not os.fork():
          #detach from controlling terminal
          os.setsid()
          #fork again and write pid to pidfile from parent, run server on child
          pid = os.fork()
          if pid:
            with open(pidfile, 'w') as f:
              f.write(str(pid))
          else:
            run_server(port)

      for i in xrange(count):
        pidfile = path_with_id(options.pidfile, i)
        if os.path.exists(pidfile):
          print "Skipping %d, pidfile exists at %s" % (i, pidfile)
          continue
        p = multiprocessing.Process(target=run_daemon_server, args=(options.port + i, pidfile))
        p.start()
    if options.daemon not in ('start', 'stop', 'restart'):
      print "Invalid daemon option: " + options.daemon
  else:
    run_server(options.port)
