import argparse

from flask import Flask, render_template, make_response, request, session, abort, jsonify
from flask_font_awesome import FontAwesome
from json_minify import json_minify
import base64, json, sys, sqlite3
from werkzeug.serving import run_simple

app = Flask(__name__)
font_awesome = FontAwesome(app)

app.secret_key = 'BAD_SECRET_KEY'

application = app

@app.route('/')
@app.route('/home')
def index():
  return render_template('index.html')

@app.route('/decode/', methods=['GET', 'POST'])
def decode():
  if request.method == 'POST':
    profile64 = request.form['profile64']
    session['profile64'] = profile64
  else:
    if session.get("profile64"):
      profile64 = session['profile64']
    else:
      profile64 = ''

  try:
    profileJSONraw = base64.b64decode(profile64).decode("utf-8")
    if (profileJSONraw == '') :
      profileJSON = ''
    else:
      try:
        profileJSON = json.dumps(json.loads(profileJSONraw),indent = 2)
      except json.JSONDecodeError as e:
        profileJSON = "Unable to decode JSON, Error: {}".format(e)
  except base64.binascii.Error as e:
    profileJSONraw = "Unable to decode base64, Error: {}".format(e)
    profileJSON = profileJSONraw

  return render_template('decode.html', profile64 = profile64, profileJSON =  profileJSON, profileJSONraw = profileJSONraw)

@app.route('/build/', defaults={'profileName': ''}, methods=['GET', 'POST'])
@app.route('/build/<profileName>', methods=['GET', 'POST'])
def build(profileName):
  if session.get("profile64"):
    profile64 = session['profile64']
  else:
    profile64 = ''

  try:
    profileJSONraw = base64.b64decode(profile64).decode("utf-8")
  except base64.binascii.Error as e:
    profileJSONraw = '{"profiles":{}}'

  if (profileJSONraw == '') :
    profileJSONraw = '{"profiles":{}}'

  try:
    profileJSON = json.loads(profileJSONraw)
  except:
    profileJSONraw = '{"profiles":{}}'
    profileJSON = json.loads(profileJSONraw)

  if request.method == 'GET' and profileName != '':
    if 'removeProfile' in request.args:
      # Remove a profile
      profileJSON['profiles'].pop(profileName)
      profileName = ''

    if 'addEntities' in request.args:
      # Add a new set in entities
      if 'entities' not in profileJSON['profiles'][profileName]:
        profileJSON['profiles'][profileName]['entities'] = json.loads('[]')
      profileJSON['profiles'][profileName]['entities'].append(json.loads('{"include": false,"match": "","select": ""}'))

    if 'addEntity' in request.args:
      # Add a new set in entity
      if 'entity' not in profileJSON['profiles'][profileName]:
        profileJSON['profiles'][profileName]['entity'] = json.loads('[]')
      profileJSON['profiles'][profileName]['entity'].append(json.loads('{"include": false,"entity_id": ""}'))

    if 'removeEntities' in request.args:
      # Remove selected entities
      profileJSON['profiles'][profileName]['entities'].pop(int(request.args['removeEntities']))

    if 'removeEntity' in request.args:
      # Remove selected entities
      profileJSON['profiles'][profileName]['entity'].pop(int(request.args['removeEntity']))

    # Save changed profile
    profile64 = base64.b64encode(json_minify(json.dumps(profileJSON)).encode("utf-8")).decode("utf-8")
    session['profile64'] = profile64

  if request.method == 'POST' and request.form['name'] != '':
    name = request.form['name']
    if name not in profileJSON['profiles']:
      profileJSON['profiles'][name] = json.loads('{}')

    # Handle entities
    count = 0
    countStr = str(count)
    while ('select_'+countStr in request.form):
      if 'entities' not in profileJSON['profiles'][name]:
        profileJSON['profiles'][name]['entities'] = json.loads('[]')

      if len(profileJSON['profiles'][name]['entities'])-1 < count:
        profileJSON['profiles'][name]['entities'].append(json.loads('{"include": false,"match": "","select": ""}'))

      profileJSON['profiles'][name]['entities'][count]['select'] = request.form['select_'+countStr]

      if ('match_'+countStr in request.form):
        profileJSON['profiles'][name]['entities'][count]['match'] = request.form['match_'+countStr]
      else:
        profileJSON['profiles'][name]['entities'][count]['match'] = 'registrationAuthority'

      if ('entities_include_'+countStr in request.form):
        profileJSON['profiles'][name]['entities'][count]['include'] = request.form['entities_include_'+countStr] == "true"
      else:
        profileJSON['profiles'][name]['entities'][count]['include'] = True

      count = count + 1
      countStr = str(count)

    # Handle entity
    count = 0
    countStr = str(count)
    while ('entity_id_'+countStr in request.form):
      if 'entity' not in profileJSON['profiles'][name]:
        profileJSON['profiles'][name]['entity'] = json.loads('[]')

      if len(profileJSON['profiles'][name]['entity'])-1 < count:
        profileJSON['profiles'][name]['entity'].append(json.loads('{"include": false,"entity_id": ""}'))

      profileJSON['profiles'][name]['entity'][count]['entity_id'] = request.form['entity_id_'+countStr]

      if ('entity_include_'+countStr in request.form):
        profileJSON['profiles'][name]['entity'][count]['include'] = request.form['entity_include_'+countStr] == "true"
      else:
        profileJSON['profiles'][name]['entity'][count]['include'] = True

      count = count + 1
      countStr = str(count)

    profileJSON['profiles'][name]['strict'] = ('strict' in request.form and request.form['strict'] == "true")

    profile64 = base64.b64encode(json_minify(json.dumps(profileJSON)).encode("utf-8")).decode("utf-8")
    session['profile64'] = profile64
    profileName = name

  editProfile = json.loads('{"name":"","profile":""}')
  if (profileName != ''):
    editProfile['name'] = profileName
    editProfile['profile']  = profileJSON['profiles'][profileName]

  return render_template('build.html', profile64 = profile64, profileJSON = profileJSON, editProfile = editProfile)

@app.route('/api/select/<matchTerm>')
def apiSelect(matchTerm):
  connect = sqlite3.connect('database.db')
  cursor = connect.cursor()

  if matchTerm == 'registrationAuthority':
    cursor.execute('SELECT id, name FROM registrationAuthority')
  elif matchTerm == 'entity_category':
    cursor.execute('SELECT id, name FROM entity_category')
  elif matchTerm == 'assurance_certification':
    cursor.execute('SELECT id, name FROM assurance_certification')
  elif matchTerm == 'entity_category_support':
    cursor.execute('SELECT id, name FROM entity_category_support')
  elif matchTerm == 'md_source':
    cursor.execute('SELECT id, name FROM md_source')
  else:
    print (f'Unkown match requested %s', (matchTerm))
    abort(404)

  data = cursor.fetchall()
  valueDict = json.loads('{"values":[]}')
  for row in data:
    x = {
      "id": row[0],
      "value": row[1]
    }
    valueDict['values'].append(x)
  return  jsonify(valueDict)

def main():
  global app

  parser = argparse.ArgumentParser(description="Process some integers.")
  parser.add_argument("port", type=int)
  parser.add_argument("--keyfile", type=str)
  parser.add_argument("--certfile", type=str)
  parser.add_argument("--host", type=str)
  args = parser.parse_args()

  if (args.keyfile and not args.certfile) or (args.certfile and not args.keyfile):
    print("Both keyfile and certfile must be specified for HTTPS.")
    sys.exit(1)

  ssl_context = (
    (args.certfile, args.keyfile)
    if args.keyfile and args.certfile
    else None
  )
  host = args.host or "localhost"
  run_simple(host, args.port, app, use_reloader=True, use_debugger=True, ssl_context=ssl_context)

if __name__ == '__main__':
  main()