import random
import json
#import md5
import traceback
import scidb_server_interface as sdbi
import mysql_server_interface as mdbi

import socket
import sys

saved_qpresults = 0

HOST = '0.0.0.0'
PORT = 50007              # Arbitrary non-privileged port
s = None

#databases
SCIDB = 'scidb'
MYSQL = 'mysql'

DEFAULT_DB = MYSQL

def dbconnect():
    """Make sure we are connected to the database each request."""
    if DEFAULT_DB == SCIDB:
    	sdbi.scidbOpenConn()
    else:
    	mdbi.mysqlOpenConn()

def dbclose():
    """Closes the database again at the end of the request."""
    if DEFAULT_DB == SCIDB:
    	sdbi.scidbCloseConn()
    else:
    	mdbi.mysqlOpenConn()

def send(mydata):
    s.send(mydata)

def process_request(inputstring):
    request = json.loads(inputstring) # parse string into json
    response = ''
    dbconnect()
    if request['function'] == "query_execute":
        options = request['options']
        query = request['query']
        if DEFAULT_DB == MYSQL:
            response = query_execute_base(query,options)
        elif DEFAULT_DB == SCIDB:
            response = query_execute(query,options)
    else:
        raise Exception("unrecognized function passed")
    dbclose()
    return json.dumps(response)

#gets dim & attr names, along with num dims, and dim boundaries
def get_queryplan_info():
    print  "got json request in queryplan function"
    query = request.args.get('query',"",type=str)
    options = {'reduce_res_check':True}
    queryplan = queryplan_execute(query,options)
    print  queryplan
    return json.dumps(queryplan)

#mysql code
def query_execute_base(userquery,options):
	query = userquery
	mdbioptions = {}
	mdbi.mysqlExecuteQuery(query,mdbioptions)
	return mdbi.mysqlGetAllAttrArrFromQueryForJSON(mdbioptions)

#options: {reduce_res_check:True/False}
def query_execute(userquery,options):
	global saved_qpresults
	query = "select * from earthquake"
	if userquery != "":
		query = userquery
		print  "user query: ",query
	sdbioptions = {'afl':False}
	print  "saved_qpresults",saved_qpresults
	if saved_qpresults == 0:
		saved_qpresults = sdbi.verifyQuery(query,sdbioptions)
		#only do this check for new queries
		if options['reduce_res_check'] and (saved_qpresults['size'] > sdbi.D3_DATA_THRESHOLD):
			return {'reduce_res':True}
	if 'reduce_type' in options: # reduction requested
		sdbioptions['reduce_res'] = True
		srtoptions = {'afl':False}
		if 'predicate' in options:
			srtoptions['predicate'] = options['predicate']
		sdbioptions['reduce_options'] = setup_reduce_type(options['reduce_type'],srtoptions)
	else: #return original query
		sdbioptions = {'afl':False,'reduce_res':False}
	queryresultobj = sdbi.executeQuery(query,sdbioptions)

	print  "retrieved data from db.\nparsing results..."
	sdbioptions={'dimnames':saved_qpresults['dims']}
	queryresultarr = sdbi.getAllAttrArrFromQueryForJSON(queryresultobj[0],sdbioptions)
	if queryresultobj[1] != 0:
		saved_qpresults = queryresultobj[1]
	# get the new dim info
	queryresultarr['dimnames'] = saved_qpresults['dims'];
	queryresultarr['dimbases'] = saved_qpresults['dimbases'];
	queryresultarr['dimwidths'] = saved_qpresults['dimwidths'];
	print  "setting saved_qpresults to 0"
	saved_qpresults = 0 # reset so we can use later
	return queryresultarr # note that I don't set reduce_res false. JS code will still handle it properly


#returns necessary options for reduce type
#options: {'afl':True/False, 'predicate':"boolean predicate",'probability':double,'chunkdims':[]}
#required options: afl, predicate (if filter specified)
#TODO: make these reduce types match the scidb interface api reduce types
def setup_reduce_type(reduce_type,options):
	global saved_qpresults
	returnoptions = {'qpresults':saved_qpresults,'afl':options['afl']}
	returnoptions['reduce_type'] = sdbi.RESTYPE[reduce_type]
	#if reduce_type == 'agg':
	if 'chunkdims' in options:
		returnoptions['chunkdims'] = chunkdims
		#returnoptions['reduce_type'] = sdbi.RESTYPE['AGGR']
	#elif reduce_type == 'sample':
	if 'probability' in options:
		returnoptions['probability'] = options['probability']
		#returnoptions['reduce_type'] = sdbi.RESTYPE['SAMPLE']
	#elif reduce_type == 'filter':
	if 'predicate' in options:
		returnoptions['predicate'] = options['predicate']
		#returnoptions['reduce_type'] = sdbi.RESTYPE['FILTER']
	#else: #unrecognized type
	#	raise Exception("Unrecognized reduce type passed to the server.")
	return returnoptions


#this will set up the connection, and keep it running
for res in socket.getaddrinfo(HOST, PORT, socket.AF_UNSPEC, socket.SOCK_STREAM, 0, socket.AI_PASSIVE):
    af, socktype, proto, canonname, sa = res
    try:
	s = socket.socket(af, socktype, proto)
    except socket.error, msg:
	s = None
	continue
    try:
	s.bind(sa)
	s.listen(1)
    except socket.error, msg:
	s.close()
	s = None
	continue
    break
if s is None:
    print 'could not open socket'
    sys.exit(1)
while 1:
    conn, addr = s.accept()
    print 'Connected by', addr
    request = ''
    while 1:
        data = conn.recv(1024)
        request += data
        if not data: break
    print "data: \"",request,"\""
    response = process_request(request)
    send(response)
conn.close()
