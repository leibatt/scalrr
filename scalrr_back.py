import random
import json
#import md5
import traceback
import scidb_server_interface as sdbi
#import mysql_server_interface as mdbi
import scalrr_back_data as sbdata
import tile_interface as ti
import threading
import select
import socket
import sys
import os

# for web socket stuff, using Tornado
import tornado.httpserver
import tornado.websocket
import tornado.ioloop
import tornado.web

from datetime import datetime

import dumb_expert

history_dir = "user_history_files"

HOST = '0.0.0.0'
PORT = 50007            # Arbitrary non-privileged port
PACKET_SIZE = 1024

#databases
SCIDB = 'scidb'
MYSQL = 'mysql'

DEFAULT_DB = SCIDB

experts = []
expert_threads = []

def dbconnect():
    """Make sure we are connected to the database each request."""
    if DEFAULT_DB == SCIDB:
    	sdbi.scidbOpenConn()
    #else:
    	#mdbi.mysqlOpenConn()

def dbclose():
    """Closes the database again at the end of the request."""
    if DEFAULT_DB == SCIDB:
    	sdbi.scidbCloseConn()
    #else:
    	#mdbi.mysqlOpenConn()

def process_request(inputstring):
    print "received request: \"",inputstring,"\""
    request = json.loads(inputstring) # parse string into json
    print "parsed request:",request
    response = ''
    #dbconnect()
    if request['function'] == "query_execute":
        options = request['options']
        query = str(request['query'])
        print "executing query:\"",query,"\""
        if DEFAULT_DB == MYSQL:
            #response = query_execute_base(query,options)
            response = {}
        elif DEFAULT_DB == SCIDB:
            response = query_execute(query,options)
    elif request['function'] == "fetch_first_tile":
        options = request['options']
        query = str(request['query'])
        print "fetching first tile for:\"",query,"\""
        response = fetch_first_tile2(query,options)
    elif request['function'] == "fetch_tile":
	print "got here"
        options = request['options']
        tile_xid = int(request['tile_xid'])
        tile_yid = int(request['tile_yid'])
	tile_id=request['tile_id']
	x_label = request['x_label']
	y_label = request['y_label']
	level = int(request['level'])
        print "fetching tile"
        #response = fetch_tile(tile_xid,tile_yid,x_label,y_label,level,options)
        response = fetch_tile2(tile_id,level,options)
    else:
	response = {'error':{'type':"unrecognized function passed",'args':inputstring}}
        #raise Exception("unrecognized function passed")
    #dbclose()
    print "returning response"
    return json.dumps(response)

#mysql code
#def query_execute_base(userquery,options):
#	query = userquery
#	mdbioptions = {}
#	mdbi.mysqlExecuteQuery(query,mdbioptions)
#	return mdbi.mysqlGetAllAttrArrFromQueryForJSON(mdbioptions)

#options: {reduce_res_check:True/False}
def query_execute(userquery,options):
	user_id = options['user_id']
	resolution = sdbi.D3_DATA_THRESHOLD
	if 'resolution' in options and options['resolution'] > 0:
		print "got resolution"
        	resolution = options['resolution']
	db = sdbi.scidbOpenConn()
	query = userquery
	#print  "user query: ",query
	sdbioptions = {'afl':False,'db':db,'resolution':resolution}
	saved_qpresults = None
        if 'saved_qpresults' in options:
        	saved_qpresults = options['saved_qpresults']
		#dumb_expert.prefetch(3,options['user_id'])
		#tile = ti.getTileByID(2,sbdata.backend_metadata[options['user_id']]['levels'],options['user_id'])
		#print "tile: ",tile
		#sdbioptions={'dimnames':saved_qpresults['dims']}
		#print sdbi.getAllAttrArrFromQueryForJSON(tile[0],sdbioptions)
		#fetch_tile(0,1,{'user_id':user_id})
	if saved_qpresults is None: # first time
		#fetch_first_tile(query,{'user_id':user_id})
		saved_qpresults = sdbi.verifyQuery(query,sdbioptions)
		#with sbdata.metadata_lock:
		#	sbdata.backend_metadata[user_id] = {}
		#	sbdata.backend_metadata[user_id]['orig_query'] = query
		#	sbdata.backend_metadata[user_id]['saved_qpresults'] = saved_qpresults
		#	if 'data_threshold' in options:
		#		sbdata.backend_metadata[user_id]['data_threshold'] = options['data_threshold']
		#	else: # default
		#		sbdata.backend_metadata[user_id]['data_threshold'] = sdbi.D3_DATA_THRESHOLD
		#	sbdata.backend_metadata[user_id]['levels'] = sbdata.default_levels #leave at default levels for now
		#	#TODO: let # levels vary
		#only do this check for new queries
		if options['reduce_res_check'] and (saved_qpresults['size'] > resolution):#sdbi.D3_DATA_THRESHOLD):
			return {'reduce_res':True,'saved_qpresults':saved_qpresults}
	if 'reduce_type' in options: # reduction requested
		sdbioptions['reduce_res'] = True
		srtoptions = {'afl':False,'saved_qpresults':saved_qpresults}
		if 'predicate' in options:
			srtoptions['predicate'] = options['predicate']
		sdbioptions['reduce_options'] = setup_reduce_type(options['reduce_type'],srtoptions)
	else: #return original query
		sdbioptions = {'afl':False,'reduce_res':False,'db':db}
	queryresultobj = sdbi.executeQuery(query,sdbioptions)
	print "queryresultobj:",queryresultobj
	print  "retrieved data from db.\nparsing results..."
	sdbioptions={'dimnames':saved_qpresults['dims']}
	queryresultarr = sdbi.getAllAttrArrFromQueryForJSON(queryresultobj[0],sdbioptions)
	if queryresultobj[1] != 0:
		saved_qpresults = queryresultobj[1]
	# get the new dim info
	queryresultarr['dimnames'] = saved_qpresults['dims']
	queryresultarr['dimbases'] = saved_qpresults['dimbases']
	queryresultarr['dimwidths'] = saved_qpresults['dimwidths']
	queryresultarr['saved_qpresults'] = saved_qpresults
	sdbi.scidbCloseConn(db)
	return queryresultarr # note that I don't set reduce_res false. JS code will still handle it properly

def fetch_first_tile(userquery,options):
	db = sdbi.scidbOpenConn()
	global experts
	query = userquery
	sdbioptions = {'afl':False,'db':db}
	saved_qpresults = sdbi.verifyQuery(query,sdbioptions)
	user_id = options['user_id']
	# setup metadata
	print "setting up metadata"
	with sbdata.metadata_lock:
		sbdata.backend_metadata[user_id] = {}
		sbdata.backend_metadata[user_id]['orig_query'] = query
		sbdata.backend_metadata[user_id]['saved_qpresults'] = saved_qpresults
		if 'data_threshold' in options:
			sbdata.backend_metadata[user_id]['data_threshold'] = options['data_threshold']
		else: # default is whatever is prescribed in scidb server interface code
			sbdata.backend_metadata[user_id]['data_threshold'] = sdbi.D3_DATA_THRESHOLD
		sbdata.backend_metadata[user_id]['levels'] = 0 #sbdata.default_levels #leave at default levels for now
		#TODO: let # levels vary
	#get tile
	tile = ti.getTileByIDXY(0,0,0,user_id)
	#save tile info
	tile_key = "0,0"
	with sbdata.user_history_lock: # add tile to history
		sbdata.user_history[user_id] = [{'tile_xid':0,'tile_yid':0,'level':0,'timestamp':datetime.now()}]
	with sbdata.user_tiles_lock:# save tile
		sbdata.user_tiles[user_id] = {0:{tile_key:tile}}
		print "added tile to sbdata.user_tiles:"#,sbdata.user_tiles
	#start prefetching
	#print "setting up prefetching experts"
	#experts = range(1)
	#expert_threads = range(1)
	#experts[0] = dumb_expert.BasicExpert()
	#expert_threads[0] = threading.Thread(target=experts[0].prefetch,args=(sbdata.max_prefetched,user_id,))
	#expert_threads[0].start()
	#sdbi.scidbCloseConn(db)
	return tile

#this is called after original query is run
def fetch_tile(tile_xid,tile_yid,x_label,y_label,level,options):
	global expert_threads
	print "stopping experts"
	sbdata.stop_prefetch.set() #stop the experts
	user_id = options['user_id']
	#check if this a tile the user is revisiting
	print "checking if user has seen this tile before"
	tile = None
	tile_key= str(tile_xid)+","+str(tile_yid)
	with sbdata.user_tiles_lock:
		if user_id in sbdata.user_tiles and level in sbdata.user_tiles[user_id] and tile_key in sbdata.user_tiles[user_id][level]:
			tile = sbdata.user_tiles[user_id][level][tile_key]

	success = range(len(experts))
	#check if an expert has cached this tile
	#if tile is None:
	#	print "checking to see if this tile was prefetched"
	#	for i in range(len(experts)):
	#		temptile = experts[i].find_tile(tile_xid,tile_yid,level,user_id)
	#		if temptile is not None:
	#			success[i] = True
	#			if tile is None:
	#				tile = temptile
	#		else:
	#			success[i] = False
	#otherwise go get the tile	
	if tile is None:
		print "tile not found, fetching from database"
		tile = ti.getTileByIDXY_Labels(tile_xid,tile_yid,x_label,y_label,level,user_id)
	with sbdata.user_history_lock: # add tile to history
		if user_id not in sbdata.user_history:
			sbdata.user_history[user_id] = []
		sbdata.user_history[user_id].append({'tile_xid':tile_xid,'tile_yid':tile_yid,'level':level,'timestamp':datetime.now()})
		print sbdata.user_history[user_id]
	with sbdata.user_tiles_lock:# save tile
		if user_id not in sbdata.user_tiles:
			sbdata.user_tiles[user_id] = {}
		if level not in sbdata.user_tiles[user_id]:
			sbdata.user_tiles[user_id][level] = {}
		if tile_key not in sbdata.user_tiles[user_id][level]:
			sbdata.user_tiles[user_id][level][tile_key] = tile
	#wait for all experts to stop
	#print "waiting for experts to stop"
	#while len(expert_threads) > 0:
	#	print "total expert threads:",len(expert_threads)
	#	print expert_threads[0]
	#	expert_threads[0].join()
	#	if len(expert_threads) > 0:
	#		expert_threads.pop(0)
	#update tile prefetch distribution
	#nothing here yet
	# restart experts
	#print "restarting experts"
	#sbdata.stop_prefetch.clear()
	#expert_threads = range(len(experts))
	#for i in range(len(experts)):
	#	experts[i].remove_all_tiles(user_id) # remove prefetched tiles
	#	expert_threads[i] = threading.Thread(target=experts[i].prefetch,args=(sbdata.max_prefetched,user_id))
	#	expert_threads[i].start()
	return tile

def fetch_first_tile2(userquery,options):
	db = sdbi.scidbOpenConn()
	global experts
	query = userquery
	sdbioptions = {'afl':False,'db':db}
	saved_qpresults = sdbi.verifyQuery(query,sdbioptions)
	sdbi.scidbCloseConn(db)
	print "saved qp results, looking for error"
	if 'error' in saved_qpresults:
		print "error found, returning error:",saved_qpresults
		return saved_qpresults
	else:
		print "saved_qpresults:",saved_qpresults
	user_id = options['user_id']
	# setup metadata
	print "setting up metadata"
	with sbdata.metadata_lock:
		sbdata.backend_metadata[user_id] = {}
		sbdata.backend_metadata[user_id]['orig_query'] = query
		sbdata.backend_metadata[user_id]['saved_qpresults'] = saved_qpresults
		if 'data_threshold' in options:
			sbdata.backend_metadata[user_id]['data_threshold'] = options['data_threshold']
		else: # default is whatever is prescribed in scidb server interface code
			sbdata.backend_metadata[user_id]['data_threshold'] = sdbi.D3_DATA_THRESHOLD
		sbdata.backend_metadata[user_id]['levels'] = 0 #sbdata.default_levels #leave at default levels for now
		#TODO: let # levels vary
	#get tile
	base_id = [0] * saved_qpresults['numdims']
	print "base id:",base_id
	tile = ti.getTileByIDN(base_id,0,user_id)
	if 'error' in tile:
		return tile
	#save tile info
	tile_key = str(base_id)
	with sbdata.user_history_lock: # add tile to history
		currtime = datetime.now()
		sbdata.user_history[user_id] = [{'tile_id':base_id,'level':0,'timestamp':currtime}]
		try:
			if not os.path.isdir(history_dir):
				os.makedirs(history_dir)
			with open(history_dir +"/"+str(user_id)+".txt", "a") as myfile:
			    myfile.write(str(base_id)+'\t0\t'+str(currtime)+"\n")
		except Exception as e:
			print e # don't barf if this doesn't work
	with sbdata.user_tiles_lock:# save tile
		sbdata.user_tiles[user_id] = {0:{tile_key:tile}}
		print "added tile to sbdata.user_tiles:"#,sbdata.user_tiles
	#start prefetching
	#print "setting up prefetching experts"
	#experts = range(1)
	#expert_threads = range(1)
	#experts[0] = dumb_expert.BasicExpert()
	#expert_threads[0] = threading.Thread(target=experts[0].prefetch,args=(sbdata.max_prefetched,user_id,))
	#expert_threads[0].start()
	#sdbi.scidbCloseConn(db)
	return tile


#this is called after original query is run
def fetch_tile2(tile_id,level,options):
	global expert_threads
	print "stopping experts"
	sbdata.stop_prefetch.set() #stop the experts
	user_id = options['user_id']
	#check if this a tile the user is revisiting
	print "checking if user has seen this tile before"
	tile = None
	tile_key= str(tile_id)
	with sbdata.user_tiles_lock:
		if user_id in sbdata.user_tiles and level in sbdata.user_tiles[user_id] and tile_key in sbdata.user_tiles[user_id][level]:
			tile = sbdata.user_tiles[user_id][level][tile_key]

	success = range(len(experts))
	#check if an expert has cached this tile
	#if tile is None:
	#	print "checking to see if this tile was prefetched"
	#	for i in range(len(experts)):
	#		temptile = experts[i].find_tile(tile_xid,tile_yid,level,user_id)
	#		if temptile is not None:
	#			success[i] = True
	#			if tile is None:
	#				tile = temptile
	#		else:
	#			success[i] = False
	#otherwise go get the tile	
	if tile is None:
		print "tile not found, fetching from database"
		tile = ti.getTileByIDN(tile_id,level,user_id)
	if 'error' in tile:
		return tile
	with sbdata.user_history_lock: # add tile to history
		currtime = datetime.now()
		if user_id not in sbdata.user_history:
			sbdata.user_history[user_id] = []
		sbdata.user_history[user_id].append({'tile_id':tile_id,'level':level,'timestamp':currtime})
		try:
			if not os.path.isdir(history_dir):
				os.makedirs(history_dir)
			with open(history_dir +"/"+str(user_id)+".txt", "a") as myfile:
			    myfile.write(str(tile_id)+'\t'+str(level)+'\t'+str(currtime)+"\n")
		except Exception as e:
			print e  # don't barf if this doesn't work
		#print "history: ",sbdata.user_history[user_id]
	with sbdata.user_tiles_lock:# save tile
		if user_id not in sbdata.user_tiles:
			sbdata.user_tiles[user_id] = {}
		if level not in sbdata.user_tiles[user_id]:
			sbdata.user_tiles[user_id][level] = {}
		if tile_key not in sbdata.user_tiles[user_id][level]:
			sbdata.user_tiles[user_id][level][tile_key] = tile
	#wait for all experts to stop
	#print "waiting for experts to stop"
	#while len(expert_threads) > 0:
	#	print "total expert threads:",len(expert_threads)
	#	print expert_threads[0]
	#	expert_threads[0].join()
	#	if len(expert_threads) > 0:
	#		expert_threads.pop(0)
	#update tile prefetch distribution
	#nothing here yet
	# restart experts
	#print "restarting experts"
	#sbdata.stop_prefetch.clear()
	#expert_threads = range(len(experts))
	#for i in range(len(experts)):
	#	experts[i].remove_all_tiles(user_id) # remove prefetched tiles
	#	expert_threads[i] = threading.Thread(target=experts[i].prefetch,args=(sbdata.max_prefetched,user_id))
	#	expert_threads[i].start()
	return tile

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
 
# used to manage requests
class WSHandler(tornado.websocket.WebSocketHandler):
    def open(self):
        print 'new connection'
      
    def on_message(self, message):
        print 'message received %s' % message
	response = process_request(str(message)) # get response for client
	self.write_message(response) # send response to client
 
    def on_close(self):
      print 'connection closed'
 
 
application = tornado.web.Application([
    (r'/', WSHandler),
])
 
 
if __name__ == "__main__":
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(PORT)
    tornado.ioloop.IOLoop.instance().start()
