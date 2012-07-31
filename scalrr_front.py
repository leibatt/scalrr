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
app = Flask(__name__)

#HOST = 'modis.csail.mit.edu'    # The remote host
HOST = 'localhost'
PORT = 50007              # The same port as used by the server
s = None

app.secret_key = 'L\x05\xb9\xab=\xe8V\x98X)\xb5\xa6\xf3uQB\x1d\x1fz\xb9y\xd7\xfb\xca'

def connect_to_backend():
    global s
    """Make sure we're connected"""
    for res in socket.getaddrinfo(HOST, PORT, socket.AF_UNSPEC, socket.SOCK_STREAM):
        af, socktype, proto, canonname, sa = res
        try:
	    s = socket.socket(af, socktype, proto)
        except socket.error, msg:
	    print msg
	    s = None
	    continue
        try:
	    s.connect(sa)
        except socket.error, msg:
	    print msg
	    s.close()
	    s = None
	    continue
        break
    if s is None:
        print 'could not open socket'
	sys.exit(1)

def close_connection_to_backend():
    global s
    """Make sure we close the connection"""
    s.close()
    s = None

def send_request(request):
    global s
    print >> sys.stderr,"sending request \"",json.dumps(request),"\" to ",HOST
    connect_to_backend()
    s.send(json.dumps(request))
    s.shutdown(socket.SHUT_WR)
    print >> sys.stderr,"retrieving data from ",HOST
    response = ''
    while 1:
        data = s.recv(1024)
        response += data
        if not data: break
    print >> sys.stderr,"received data from ",HOST
    close_connection_to_backend()
    return json.loads(response)

@app.route('/move-zoom/', methods=["POST", "GET"])
def get_move_zoom():
    session['user_id'] = str(uuid.uuid4())
    return render_template('move-zoom.html')

@app.route('/index2/', methods=["POST", "GET"])
def get_data2():
    session['user_id'] = str(uuid.uuid4())
    return render_template('index2.html')

@app.route('/fetch-first-tile',methods=["POST", "GET"])
def fetch_first_tile():
    print >> sys.stderr, "got fetch first tile request"
    query = request.args.get('query',"",type=str)
    options = {'user_id':session['user_id']}
    server_request = {'query':query,'options':options,'function':'fetch_first_tile'}
    queryresultarr = send_request(server_request)
    print >> sys.stderr, "result length: ",len(queryresultarr['data'])
    #print >> sys.stderr, json.dumps(queryresultarr)
    return json.dumps(queryresultarr)

@app.route('/fetch-tile',methods=["POST", "GET"])
def fetch_tile():
    print >> sys.stderr, "got json request in noreduce function"
    tile_id = request.args.get('tile_id',"",type=int)
    level = request.args.get('level',"",type=int)
    options = {'user_id':session['user_id']}
    server_request = {'options':options,'tile_id':tile_id,'level':level,'function':'fetch_tile'}
    queryresultarr = send_request(server_request)
    if 'saved_qpresults' in queryresultarr:
        session['saved_qpresults'] = queryresultarr['saved_qpresults']
    print >> sys.stderr, "result length: ",len(queryresultarr['data'])
    #print >> sys.stderr, json.dumps(queryresultarr)
    return json.dumps(queryresultarr)

@app.route('/json-data', methods=["POST", "GET"])
def get_data_ajax():
    print >> sys.stderr, "got json request in init function"
    query = request.args.get('query',"",type=str)
    options = {'reduce_res_check':True}
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
    print >> sys.stderr, "got json request in noreduce function"
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
    print >> sys.stderr, "result length: ",len(queryresultarr['data'])
    #print >> sys.stderr, json.dumps(queryresultarr)
    return json.dumps(queryresultarr)

@app.route('/json-data-reduce', methods=["POST", "GET"])
def get_data_ajax_reduce():
    print >> sys.stderr, "got json request in reduce function"
    query = request.args.get('query',"",type=str)
    reduce_type = request.args.get('reduce_type',"",type=str)
    predicate = request.args.get('predicate',"",type=str)
    options = {'reduce_res_check':False,'reduce_res':True,'reduce_type':reduce_type}
    options['user_id'] = session['user_id']
    if 'saved_qpresults' in session and session['saved_qpresults'] is not None:
        options['saved_qpresults'] = session['saved_qpresults']
    else:
        options['saved_qpresults'] = None
    if predicate != "":
	options['predicate'] = predicate
    server_request = {'query':query,'options':options,'function':'query_execute'}
    queryresultarr = send_request(server_request)
    print >> sys.stderr, "result length: ",len(queryresultarr['data'])
    if 'saved_qpresults' in queryresultarr:
        session['saved_qpresults'] = queryresultarr['saved_qpresults']
    #print >> sys.stderr, queryresultarr
    #print >> sys.stderr, json.dumps(queryresultarr)
    return json.dumps(queryresultarr)


if __name__ == "__main__":
    app.debug = True
    #address = ('', 8080)
    #http_server = WSGIServer(address, app, handler_class=WebSocketHandler)
    print "server is running now"
    #http_server.serve_forever()
    app.run()
