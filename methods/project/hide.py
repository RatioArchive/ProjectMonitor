from toto.invocation import *
from toto.exceptions import *
from toto.events import EventManager

@requires('name')
def invoke(handler, params):
  handler.connection.db.projects.update({'name': params['name']}, {'$set': {'hidden': True}})
  EventManager.instance().send("project_updated", {'name': params['name']})
  return {'name': params['name'], 'hidden': True}
