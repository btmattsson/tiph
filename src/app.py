import argparse

from flask import Flask, render_template, request, session
from flask_font_awesome import FontAwesome
from json_minify import json_minify
import base64, json, sys
from werkzeug.serving import run_simple

app = Flask(__name__)
font_awesome = FontAwesome(app)

app.secret_key = 'BAD_SECRET_KEY'

@app.route('/')
@app.route('/home')
def index():
  return render_template('index.html')

@app.route('/decode', methods=['GET', 'POST'])
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

@app.route('/build', defaults={'profile': ''}, methods=['GET', 'POST'])
@app.route('/build/<profile>', methods=['GET', 'POST'])
def build(profile):
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

  if request.method == 'POST':
    name = request.form['name']
    count = 0
    countStr = str(count)
    while ('select_'+countStr in request.form):
      profileJSON['profiles'][name]['entities'][count]['select'] = request.form['select_'+countStr]

      if ('match_'+countStr in request.form):
        profileJSON['profiles'][name]['entities'][count]['match'] = request.form['match_'+countStr]
      else:
        profileJSON['profiles'][name]['entities'][count]['match'] = 'registrationAuthority'

      if ('include_'+countStr in request.form):
        profileJSON['profiles'][name]['entities'][count]['include'] = request.form['include_'+countStr] == "true"
      else:
        profileJSON['profiles'][name]['entities'][count]['include'] = True

      count = count + 1
      countStr = str(count)
    profileJSON['profiles'][name]['strict'] = ('strict' in request.form and request.form['strict'] == "true")

    profile64 = base64.b64encode(json_minify(json.dumps(profileJSON)).encode("utf-8")).decode("utf-8")
    session['profile64'] = profile64

  editProfile = json.loads('{"name":"","profile":""}')
  if (profile != ''):
    editProfile['name'] = profile
    editProfile['profile']  = profileJSON['profiles'][profile]
    editProfile['profile']

  return render_template('build.html', profile64 = profile64, profileJSON = profileJSON, editProfile = editProfile)

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