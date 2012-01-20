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
      raise TotoError(ERROR_INVALID_PROJECT, "No project exists with that name.")
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
    view['velocities'] = [updates[i-1]['project_progress'] - updates[i]['project_progress'] for i in xrange(1, len(updates))]
    if view['velocities']:
      view['average_velocity'] = sum(view['velocities'])/len(view['velocities'])
      view['stddev_velocity'] = sqrt(sum([(v - view['average_velocity']) ** 2 for v in view['velocities']]) / len(view['velocities']))
    hour_progress = view['hours_budgeted'] and float(view['hours_spent']) / view['hours_budgeted'] or 0
    view['status'] = {'hours': hour_progress <= view['project_progress'] and STATUS_GOOD or hour_progress < view['project_progress'] + 0.05 and STATUS_OK or STATUS_BAD,
                      'story': view['story_progress'] <= view['project_progress'] and STATUS_GOOD or view['story_progress'] < view['project_progress'] + 0.05 and STATUS_OK or STATUS_BAD}
    if view['velocities']:
      diff = view['average_velocity'] - view['velocities'][0]
      view['status']['velocity'] = diff <= view['stddev_velocity'] and STATUS_GOOD or diff <= 3 * view['stddev_velocity'] and STATUS_OK or STATUS_BAD
    view['status']['general'] = max((view['status'][k] for k in view['status']))
    views.append(view)
  return views
