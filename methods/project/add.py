from toto.invocation import *
from toto.exceptions import *

@requires('name','client')
def invoke(handler, params):
  if handler.connection.db.projects.find_one({'name': params['name']}):
    raise TotoError(ERROR_PROJECT_EXISTS, "A project with that name already exists")
  handler.connection.db.projects.insert({'name': params['name'], 'client': params['client'], 'hidden': False})
  return params;
