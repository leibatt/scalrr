import random
import json
#import md5
import traceback
import scidb_server_interface as sdbi
import mysql_server_interface as mdbi

import threading
import select
import socket
import sys

HOST = '0.0.0.0'
PORT = 50007            # Arbitrary non-privileged port
PACKET_SIZE = 1024

#databases
SCIDB = 'scidb'
MYSQL = 'mysql'

DEFAULT_DB = SCIDB

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

def process_request(inputstring):
    print "received request: \"",inputstring,"\""
    request = json.loads(inputstring) # parse string into json
    response = ''
    dbconnect()
    if request['function'] == "query_execute":
        options = request['options']
        query = str(request['query'])
        print "executing query:\"",query,"\""
        if DEFAULT_DB == MYSQL:
            response = query_execute_base(query,options)
        elif DEFAULT_DB == SCIDB:
            response = query_execute(query,options)
    else:
        raise Exception("unrecognized function passed")
    dbclose()
    print "returning response"
    return json.dumps(response)

#mysql code
def query_execute_base(userquery,options):
	query = userquery
	mdbioptions = {}
	mdbi.mysqlExecuteQuery(query,mdbioptions)
	return mdbi.mysqlGetAllAttrArrFromQueryForJSON(mdbioptions)

#options: {reduce_res_check:True/False}
def query_execute(userquery,options):
	query = userquery
	print  "user query: ",query
	sdbioptions = {'afl':False}
	saved_qpresults = None
        if 'saved_qpresults' in options:
        	saved_qpresults = options['saved_qpresults']
	if saved_qpresults is None:
		saved_qpresults = sdbi.verifyQuery(query,sdbioptions)
		#only do this check for new queries
		if options['reduce_res_check'] and (saved_qpresults['size'] > sdbi.D3_DATA_THRESHOLD):
			return {'reduce_res':True,'saved_qpresults':saved_qpresults}
	if 'reduce_type' in options: # reduction requested
		sdbioptions['reduce_res'] = True
		srtoptions = {'afl':False,'saved_qpresults':saved_qpresults}
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
	print  "setting saved_qpresults to None"
	saved_qpresults = None # reset so we can use later
	queryresultarr['saved_qpresults'] = saved_qpresults
	return queryresultarr # note that I don't set reduce_res false. JS code will still handle it properly


#returns necessary options for reduce type
#options: {'afl':True/False, 'predicate':"boolean predicate",'probability':double,'chunkdims':[]}
#required options: afl, predicate (if filter specified)
#TODO: make these reduce types match the scidb interface api reduce types
def setup_reduce_type(reduce_type,options):
        saved_qpresults = options['saved_qpresults']
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

class Server:
    def __init__(self):
        self.host = HOST
        self.port = PORT
        self.backlog = 5
        self.size = PACKET_SIZE
        self.server = None
        self.threads = []

    def open_socket(self):
        for res in socket.getaddrinfo(HOST, PORT, socket.AF_UNSPEC, socket.SOCK_STREAM, 0, socket.AI_PASSIVE):
            af, socktype, proto, canonname, sa = res
            try:
                self.server = socket.socket(af, socktype, proto)
            except socket.error, msg:
                self.server = None
                continue
            try:
                self.server.bind(sa)
                self.server.listen(1)
            except socket.error, msg:
                self.server.close()
                self.server = None
                continue
            break
        if self.server is None:
            print 'could not open socket'
            sys.exit(1)

    def run(self):
        self.open_socket()
        input = [self.server,sys.stdin]
        running = 1
        while running:
            inputready,outputready,exceptready = select.select(input,[],[])

            for s in inputready:

                if s == self.server:
                    # handle the server socket
                    c = Client(self.server.accept())
                    c.start()
                    self.threads.append(c)

                elif s == sys.stdin:
                    # handle standard input
                    junk = sys.stdin.readline()
                    running = 0

        # close all threads

        self.server.close()
        for c in self.threads:
            c.join()

class Client(threading.Thread):
    def __init__(self,(client,address)):
        threading.Thread.__init__(self)
        self.client = client
        self.address = address
        self.size = PACKET_SIZE

    def run(self):
        running = 1
	print 'Connected by', self.address
	request = ''
	while running:
	    print "got here"
	    data = self.client.recv(PACKET_SIZE)
	    print "data: ",data
	    if data: 
                request += data
            else:
                running = 0
	print "final data: \"",request,"\""
	response = process_request(request)
	self.client.send(response)
	self.client.close()

if __name__ == "__main__":
    s = Server()
    s.run() 
