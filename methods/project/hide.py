from toto.invocation import *
from toto.exceptions import *

@requires('name')
def invoke(handler, params):
  handler.connection.db.projects.update({'name': params['name']}, {'$set': {'hidden': True}})
  return {'name': params['name'], 'hidden': True}
