#activate_this = '/path/to/env/bin/activate_this.py'
#execfile(activate_this, dict(__file__=activate_this))
#from gevent.pywsgi import WSGIServer # must be pywsgi to support websocket
#from geventwebsocket.handler import WebSocketHandler
from flask import Flask, session, request, render_template, g, redirect, send_file
import random
import simplejson as json
#import md5
import traceback
import socket
import sys
import uuid
import websocket
import logging
from logging.handlers import RotatingFileHandler
from logging import Formatter
app = Flask(__name__)


#TODO: put this info in a config file
LOGFILE = None
HOST = None
#HOST = 'modis.csail.mit.edu'
PORT = None              # The same port as used by the server

app.secret_key = None

with open("config.txt","r") as keyfile:
    for line in keyfile:
	keypair = line[:-1].split('=',1)
	if keypair[0] == 'log_file':
	    LOGFILE = str(keypair[1])
        elif keypair[0] == 'host':
            HOST = str(keypair[1])
        elif keypair[0] == 'port':
            PORT = int(keypair[1])
        elif keypair[0] == 'secret_key':
            app.secret_key = str(keypair[1])

CONN_STRING = str("ws://"+str(HOST)+":"+str(PORT)+"/")

def connect_to_backend():
    if 'backend_conn' not in session:
        try:
            ws = websocket.create_connection(CONN_STRING)
            session['backend_conn'] = ws
        except Exception as e:
            app.logger.error('error occurred connecting to backend:\n'+str(type(e)))
    if ('backend_conn' not in session) or (session['backend_conn'] is None):
        app.logger.warning('could not open connection to \''+CONN_STRING+'\'')

def close_connection_to_backend():
    """Make sure we close the connection"""
    session['backend_conn'].close()
    session['backend_conn'] = None
    session.pop('backend_conn')

def send_request(request):
    connect_to_backend()
    ws = session['backend_conn']
    app.logger.info("sending request \""+json.dumps(request)+"\" to '"+CONN_STRING+"'")
    ws.send(json.dumps(request))
    app.logger.info("retrieving data from '"+CONN_STRING+"'")
    response = ws.recv()
    app.logger.info("received data from '"+CONN_STRING+"'")
    close_connection_to_backend()
    return json.loads(response)

#@app.route('/blah/',methods=["POST", "GET"])
def blah():
    return render_template('blah.html')

#@app.route('/blah/miserables.json', methods=["POST", "GET"])
def get__example_readme():
    return send_file("data/miserables.json")

@app.route('/move-zoom/', methods=["POST", "GET"])
def get_move_zoom():
    session['user_id'] = str(uuid.uuid4())
    return render_template('move-zoom.html')

@app.route('/index2/', methods=["POST", "GET"])
def get_data2():
    session['user_id'] = str(uuid.uuid4())
    return render_template('index2.html')

@app.route('/canvas/', methods=["POST", "GET"])
def get_data2():
    session['user_id'] = str(uuid.uuid4())
    return render_template('canvas.html')

@app.route('/fetch-first-tile',methods=["POST", "GET"])
def fetch_first_tile():
    app.logger.info("got fetch first tile request")
    query = request.args.get('query',"",type=str)
    data_threshold = request.args.get('data_threshold',0,type=int)
    options = {'user_id':session['user_id']}
    if data_threshold > 0:
	options['data_threshold'] = data_threshold
    server_request = {'query':query,'options':options,'function':'fetch_first_tile'}
    queryresultarr = send_request(server_request)
    if 'error' not in queryresultarr: # error happened
        app.logger.info("result length: "+str(len(queryresultarr['data'])))
    #print >> sys.stderr, json.dumps(queryresultarr)
    return json.dumps(queryresultarr)

@app.route('/fetch-tile',methods=["POST", "GET"])
def fetch_tile():
    app.logger.info("got json request in noreduce function")
    tile_xid = request.args.get('tile_xid',"",type=int)
    tile_yid = request.args.get('tile_yid',"",type=int)
    tile_id = request.args.getlist('temp_id[]')
    for i in range(len(tile_id)):
        tile_id[i] = int(tile_id[i])
    x_label = request.args.get('x_label',"",type=str)
    y_label = request.args.get('y_label',"",type=str)
    level = request.args.get('level',"",type=int)
    options = {'user_id':session['user_id']}
    server_request = {'options':options,'tile_xid':tile_xid,'tile_yid':tile_yid,'tile_id':tile_id,'level':level,'y_label':y_label,'x_label':x_label,'function':'fetch_tile'}
    queryresultarr = send_request(server_request)
    if 'saved_qpresults' in queryresultarr:
        session['saved_qpresults'] = queryresultarr['saved_qpresults']
    app.logger.info("result length: "+str(len(queryresultarr['data'])))
    #print >> sys.stderr, json.dumps(queryresultarr)
    return json.dumps(queryresultarr)

@app.route('/json-data', methods=["POST", "GET"])
def get_data_ajax():
    app.logger.info("got json request in init function")
    query = request.args.get('query',"",type=str)
    resolution = request.args.get('resolution',0,type=int)
    options = {'reduce_res_check':True,'resolution':resolution}
    #options['saved_qpresults'] = None
    #requests from this url always happen at the beginning of a user session
    options['user_id'] = session['user_id']
    server_request = {'query':query,'options':options,'function':'query_execute'}
    queryresultarr = send_request(server_request)
    if 'saved_qpresults' in queryresultarr:
        session['saved_qpresults'] = queryresultarr['saved_qpresults']
    #print >> sys.stderr, queryresultarr
    #print >> sys.stderr, json.dumps(queryresultarr)
    return json.dumps(queryresultarr)

@app.route('/json-data-noreduction', methods=["POST", "GET"])
def get_data_ajax_noreduction():
    app.logger.info("got json request in noreduce function")
    query = request.args.get('query',"",type=str)
    options = {'reduce_res_check':False}
    options['user_id'] = session['user_id']
    if 'saved_qpresults' in session and session['saved_qpresults'] is not None:
        options['saved_qpresults'] = session['saved_qpresults']
    else:
        options['saved_qpresults'] = None
    server_request = {'query':query,'options':options,'function':'query_execute'}
    queryresultarr = send_request(server_request)
    if 'saved_qpresults' in queryresultarr:
        session['saved_qpresults'] = queryresultarr['saved_qpresults']
    app.logger.info("result length: "+str(len(queryresultarr['data'])))
    #print >> sys.stderr, json.dumps(queryresultarr)
    return json.dumps(queryresultarr)

@app.route('/json-data-reduce', methods=["POST", "GET"])
def get_data_ajax_reduce():
    app.logger.info("got json request in reduce function")
    query = request.args.get('query',"",type=str)
    reduce_type = request.args.get('reduce_type',"",type=str)
    predicate = request.args.get('predicate',"",type=str)
    resolution = request.args.get('resolution',0,type=int)
    options = {'reduce_res_check':False,'reduce_res':True,'reduce_type':reduce_type,'resolution':resolution}
    options['user_id'] = session['user_id']
    if 'saved_qpresults' in session and session['saved_qpresults'] is not None:
        options['saved_qpresults'] = session['saved_qpresults']
    else:
        options['saved_qpresults'] = None
    if predicate != "":
	options['predicate'] = predicate
    server_request = {'query':query,'options':options,'function':'query_execute'}
    queryresultarr = send_request(server_request)
    app.logger.info("result length: "+str(len(queryresultarr['data'])))
    if 'saved_qpresults' in queryresultarr:
        session['saved_qpresults'] = queryresultarr['saved_qpresults']
    #print >> sys.stderr, queryresultarr
    #print >> sys.stderr, json.dumps(queryresultarr)
    return json.dumps(queryresultarr)


if __name__ == "__main__":
    app.debug = True
    if not app.debug:
        file_handler = RotatingFileHandler(LOGFILE, maxBytes=10000, backupCount=1)
        file_handler.setFormatter(Formatter(
            '%(asctime)s %(levelname)s: %(message)s '
            '[in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.WARNING)
        app.logger.addHandler(file_handler)
    #address = ('', 8080)
    #http_server = WSGIServer(address, app, handler_class=WebSocketHandler)
    app.logger.info("server is running now")
    #http_server.serve_forever()
    app.run()
