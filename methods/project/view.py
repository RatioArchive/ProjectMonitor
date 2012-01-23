from toto.invocation import *
from toto.exceptions import *
from math import sqrt

STATUS_GOOD = 1
STATUS_OK = 2
STATUS_BAD = 3

def invoke(handler, params):
  if 'name' in params:
    project = handler.connection.db.projects.find_one({'name': params['name'], 'hidden': {'$ne': True}})
    if not project:
      raise TotoException(ERROR_INVALID_PROJECT, "No project exists with that name.")
    projects = [project,]
  else:
    projects = [project for project in handler.connection.db.projects.find({'hidden': {'$ne': True}})]
  views = []
  for project in projects:
    updates = [update for update in handler.connection.db.updates.find({'name': project['name']}).sort('timestamp', -1).limit(10)]
    view = updates and updates[0] or {'name':project['name'], 'hours_spent': 0, 'hours_budgeted': 0, 'story_progress': 0, 'project_progress': 0}
    if '_id' in view:
      del view['_id']
    view['client'] = project['client']
    view['velocities'] = [(updates[i-1]['project_progress'] - updates[i]['project_progress'])/(updates[i-1]['timestamp'] - updates[i]['timestamp']) for i in xrange(1, len(updates))]
    if view['velocities']:
      view['average_velocity'] = sum(view['velocities'])/len(view['velocities'])
      view['stddev_velocity'] = sqrt(sum([(v - view['average_velocity']) ** 2 for v in view['velocities']]) / len(view['velocities']))
    hour_progress = view['hours_budgeted'] and float(view['hours_spent']) / view['hours_budgeted'] or 0
    view['status'] = {'components': {
      'hours': {
        'code': hour_progress <= view['project_progress'] and STATUS_GOOD or hour_progress < view['project_progress'] + 0.05 and STATUS_OK or STATUS_BAD,
        'message': 'Usage: %d%% Project: %d%%' % (int(hour_progress * 100), int(view['project_progress'] * 100))},
      'story': {
        'code': view['story_progress'] <= view['project_progress'] and STATUS_GOOD or view['story_progress'] < view['project_progress'] + 0.05 and STATUS_OK or STATUS_BAD,
        'message': 'Current: %d%% Project: %d%%' % (int(view['story_progress'] * 100), int(view['project_progress'] * 100))},
    }}
    if view['velocities']:
      diff = view['average_velocity'] - view['velocities'][0]
      view['status']['components']['velocity'] = {
        'code': diff <= view['stddev_velocity'] and STATUS_GOOD or diff <= 3 * view['stddev_velocity'] and STATUS_OK or STATUS_BAD,
        'message': 'Current: %d%% Average: %d%%' % (int(view['velocities'][0] * 100), int(view['average_velocity'] * 100))
      }
    view['status']['code'] = max((view['status']['components'][k]['code'] for k in view['status']['components']))
    views.append(view)
  return views
