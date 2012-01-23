from toto.invocation import *
from toto.exceptions import *
from toto.events import EventManager

@requires('name')
def invoke(handler, params):
  handler.connection.db.projects.remove({'name': params['name']})
  handler.connection.db.updates.remove({'name': params['name']})
  EventManager.instance().send("project_updated", {'name': params['name']})
  return {'name': params['name']}
