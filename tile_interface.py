import scalrr_back_data as sbdata
import scidb_server_interface as sdbi
import math

def getTileByIDXY(tile_xid,tile_yid,l,user_id):
	tile_info = {'type':'xy','tile_xid':tile_xid,'tile_yid':tile_yid}
	return getTileHelper(tile_info,l,user_id)

#   y-------->
#x  0  1  2 ...
#| 10 11 12 ...
#| 20 21 22...
#v
def getTileByID(tile_id,l,user_id):
	tile_info = {'type':'id','tile_id':tile_id}
	return getTileHelper(tile_info,l,user_id)

#def getTile(orig_query,cx,cy,l,d,x,y,options):
def getTile(cx,cy,l,user_id):
	tile_info = {'type':'center','cx':cx,'cy':cy}
	return getTileHelper(tile_info,l,user_id)

def getTileHelper(tile_info,l,user_id):
	db = sdbi.scidbOpenConn()
	with sbdata.metadata_lock:
		orig_query = sbdata.backend_metadata[user_id]['orig_query']
		saved_qpresults = sbdata.backend_metadata[user_id]['saved_qpresults']
		xbase = 0
		ybase = 0
		if len(saved_qpresults['dimbases']) > 0: # adjust bases for array if possible
			xbase = int(saved_qpresults['dimbases'][saved_qpresults['dims'][0]])
			ybase = int(saved_qpresults['dimbases'][saved_qpresults['dims'][1]])
		x = saved_qpresults['dimwidths'][saved_qpresults['dims'][0]]
		y = saved_qpresults['dimwidths'][saved_qpresults['dims'][1]]
		k = sbdata.backend_metadata[user_id]['data_threshold']
		levels = sbdata.backend_metadata[user_id]['levels']
		if levels == 0: # need to compute # of levels
			tsize = saved_qpresults['size'] # get the size of the result
			if tsize <= k: # if k happens to be larger than the total results
				levels = 1
			else: # round up to include the topmost level
				levels = math.ceil(math.log(tsize)/math.log(k))+1
			sbdata.backend_metadata[user_id]['levels'] = levels # store this computed value
	setup_aggr_options = {'afl':False,'saved_qpresults':saved_qpresults}
	aggr_options = setup_reduce_type('AGGR',setup_aggr_options)
	aggr_options['db'] = db
	if tile_info['type'] == "center":
		queryresultobj = sdbi.getTile(orig_query,tile_info['cx'],tile_info['cy'],l,levels-1,sbdata.default_diff,x,xbase,y,ybase,k,aggr_options)
	elif tile_info['type'] == "xy":
		queryresultobj = sdbi.getTileByIDXY(orig_query,tile_info['tile_xid'],tile_info['tile_yid'],l,levels-1,sbdata.default_diff,x,xbase,y,ybase,k,aggr_options)
	else:
		queryresultobj = sdbi.getTileByID(orig_query,tile_info['tile_id'],l,levels-1,sbdata.default_diff,x,xbase,y,ybase,k,aggr_options)
	total_tiles = queryresultobj[1]['total_tiles']
	total_tiles_root = queryresultobj[1]['total_tiles_root']
	print "total_tiles_root:",total_tiles_root
	sdbioptions={'dimnames':saved_qpresults['dims']}
	queryresultarr = sdbi.getAllAttrArrFromQueryForJSON(queryresultobj[0],sdbioptions)
	saved_qpresults = queryresultobj[1] # don't need local saved_qpresults anymore, so reuse
	# get the new dim info
	queryresultarr['dimnames'] = saved_qpresults['dims']
	queryresultarr['dimbases'] = saved_qpresults['dimbases']
	queryresultarr['dimwidths'] = saved_qpresults['dimwidths']
	queryresultarr['saved_qpresults'] = saved_qpresults
	queryresultarr['max_zoom'] = levels
	queryresultarr['total_tiles'] = total_tiles
	queryresultarr['total_tiles_root'] = total_tiles_root
	queryresultarr['zoom_diff'] = sbdata.default_diff
	sdbi.scidbCloseConn(db)
	return queryresultarr

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

