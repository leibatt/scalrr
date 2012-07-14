from gevent.pywsgi import WSGIServer # must be pywsgi to support websocket
from geventwebsocket.handler import WebSocketHandler
from flask import Flask, request, render_template, g, redirect, send_file
import random
import json
#import md5
import traceback
import socket
import sys
app = Flask(__name__)

saved_qpresults = 0

HOST = 'modis.csail.mit.edu'    # The remote host
PORT = 50007              # The same port as used by the server
s = None

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

def send_request(mydata):
    global s
    print >> sys.stderr,"sending request to ",HOST
    connect_to_backend()
    s.send(json.dumps(mydata))
    print >> sys.stderr,"retrieving data from ",HOST
    response = ''
    while 1:
        data = s.recv(1024)
        response += data
        if not data: break
    print >> sys.stderr,"received data from ",HOST
    close_connection_to_backend()
    return json.loads(response)

@app.route('/index2/', methods=["POST", "GET"])
def get_data2():
    return render_template('index2.html')

@app.route('/json-data', methods=["POST", "GET"])
def get_data_ajax():
    print >> sys.stderr, "got json request in init function"
    query = request.args.get('query',"",type=str)
    options = {'reduce_res_check':True}
    server_request = {'query':query,'options':options,'function':'query_execute'}
    queryresultarr = send_request(server_request)
    #print >> sys.stderr, queryresultarr
    #print >> sys.stderr, json.dumps(queryresultarr)
    return json.dumps(queryresultarr)

@app.route('/json-data-noreduction', methods=["POST", "GET"])
def get_data_ajax_noreduction():
    print >> sys.stderr, "got json request in noreduce function"
    query = request.args.get('query',"",type=str)
    options = {'reduce_res_check':False}
    server_request = {'query':query,'options':options,'function':'query_execute'}
    queryresultarr = send_request(server_request)
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
    if predicate != "":
	options['predicate'] = predicate
    server_request = {'query':query,'options':options,'function':'query_execute'}
    queryresultarr = send_request(server_request)
    print >> sys.stderr, "result length: ",len(queryresultarr['data'])
    #print >> sys.stderr, queryresultarr
    #print >> sys.stderr, json.dumps(queryresultarr)
    return json.dumps(queryresultarr)


if __name__ == "__main__":
    app.debug = True
    address = ('', 8080)
    http_server = WSGIServer(address, app, handler_class=WebSocketHandler)
    print "server is running now"
    http_server.serve_forever()
    #app.run()
