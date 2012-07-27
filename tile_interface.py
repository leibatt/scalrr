import scalrr_back_data as sbdata
import scidb_server_interface as sdbi

#   y-------->
#x  0  1  2 ...
#| 10 11 12 ...
#| 20 21 22...
#v
def getTileByID(tile_id,l,user_id):
	tile_info = {'type':'id','tile_id':tile_id}
	return getTileHelper(tile_info,user_id)

#def getTile(orig_query,cx,cy,l,d,x,y,options):
def getTile(cx,cy,l,user_id):
	tile_info = {'type':'center','cx':cx,'cy':cy}
	return getTileHelper(tile_info,user_id)

def getTileHelper(tile_info,user_id):
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
		l = sbdata.backend_metadata[user_id]['levels']
	setup_aggr_options = {'afl':False,'saved_qpresults':saved_qpresults}
	if tile_info['type'] == "center":
		return sdbi.getTile(orig_query,tile_info['cx'],tile_info['cy'],l,sbdata.default_diff,x,xbase,y,ybase,setup_reduce_type('AGGR',setup_aggr_options))
	else:
		return sdbi.getTileByID(orig_query,tile_info['tile_id'],l,sbdata.default_diff,x,xbase,y,ybase,setup_reduce_type('AGGR',setup_aggr_options))

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

