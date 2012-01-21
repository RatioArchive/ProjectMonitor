from toto.invocation import *
from toto.exceptions import *
from toto.events import EventManager

ERROR_PROJECT_EXISTS = 2001

@requires('name','client')
def invoke(handler, params):
  if handler.connection.db.projects.find_one({'name': params['name']}):
    raise TotoException(ERROR_PROJECT_EXISTS, "A project with that name already exists")
  handler.connection.db.projects.insert({'name': params['name'], 'client': params['client'], 'hidden': False})
  EventManager.instance().send("project_updated", {'name': params['name']})
  return params;
