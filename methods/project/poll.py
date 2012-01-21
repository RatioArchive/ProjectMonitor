from toto.invocation import *
from toto.events import EventManager

def on_connection_close(handler):
  print 'CLOSED'

@asynchronous
def invoke(handler, params):
  def project_updated(project):
    handler.respond(result=project)
  EventManager.instance().register_handler("project_updated", project_updated)
