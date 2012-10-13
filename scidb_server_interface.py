import sys
sys.path.append('/opt/scidb/12.3/lib')
sys.path.append('/opt/scidb/12.7/lib')
import scidbapi as scidb
import string, re
import simplejson as json
import math
from datetime import datetime

LOGICAL_PHYSICAL = "explain_physical"
RESTYPE = {'AGGR': 'aggregate', 'SAMPLE': 'sample','OBJSAMPLE': 'samplebyobj','FILTER':'filter','OBJAGGR': 'aggregatebyobj', 'BSAMPLE': 'biased_sample'}
AGGR_CHUNK_DEFAULT = 10
TILE_AGGR_CHUNK_DEFAULT = 1 # don't aggregate if we're at the lowest zoom level
PROB_DEFAULT = .5
SIZE_THRESHOLD = 50
D3_DATA_THRESHOLD = 10000

#db = 0

def scidbOpenConn():
	#global db
	db = scidb.connect("localhost",1239)
	#db = scidb.connect("vise4.csail.mit.edu",1239)
	return db

def scidbCloseConn(db):
	#global db
	if db != 0:
		db.disconnect()
		db = 0

#orig_query = original user query
#cx,cy= center
#l = current zoom level
#d = resolution difference between zoom levels
#jxk = maximum dimensions handled by the front-end
#mxn = original array dimensions
def getTile(orig_query,cx,cy,l,max_l,d,x,xbase,y,ybase,threshold,aggregate_options):
	orig_query = re.sub("(\'|\")","\\\1",orig_query) #escape single and double quotes
	total_tiles = math.pow(d,2*l)
	total_tiles_root = math.sqrt(total_tiles)
	tile_x = x/total_tiles_root # figure out tile dimensions
	tile_y = y/total_tiles_root
	lower_x = xbase + int(math.floor(cx - .5*tile_x))
	lower_y = ybase + int(math.floor(cy - .5*tile_y))
	upper_x = xbase + int(math.ceil(cx + .5*tile_x))
	upper_y = ybase + int(math.ceil(cy + .5*tile_y))
	newquery = "select * from subarray(("+orig_query+"),"+str(lower_x)+","+str(lower_y)+","+str(upper_x)+","+str(upper_y)+")"
        newquery = str(newquery)
	print "newquery: ",newquery
	sdbioptions = {'db':aggregate_options['db'],'afl':False}
	qpresults = verifyQuery(newquery,sdbioptions)
	sdbioptions['reduce_res'] = qpresults['size'] > threshold
	if sdbioptions['reduce_res']:
		aggregate_options['threshold'] = threshold
		aggregate_options['qpresults'] = qpresults
		aggregate_options['tile'] = True
		sdbioptions['reduce_options'] = aggregate_options
	result = executeQuery(newquery,sdbioptions)
	result[1]['total_tiles'] = total_tiles
	result[1]['total_tiles_root'] = total_tiles_root
	return result

#orig_query = original user query
#cx,cy= center
#l = current zoom level
#d = resolution difference between zoom levels
#jxk = maximum dimensions handled by the front-end
#mxn = original array dimensions
def getTileByID(orig_query,tile_id,l,max_l,d,x,xbase,y,ybase,threshold,aggregate_options): # zero-based indexing
	orig_query = re.sub("(\'|\")","\\\1",orig_query) #escape single and double quotes
	total_tiles = math.pow(d,2*l)
	if tile_id < 0 or tile_id >= total_tiles: #default, get a middle tile
		tile_id = int(totaltiles/2)
	total_tiles_root = math.sqrt(total_tiles)
	tile_x = x/total_tiles_root # figure out tile dimensions
	tile_y = y/total_tiles_root
        x_offset = math.floor(tile_id / int(total_tiles_root)) # figure out offsets
	y_offset = tile_id % int(total_tiles_root)
	lower_x = xbase + int(x_offset*tile_x)
	lower_y = ybase + int(y_offset*tile_y)
	upper_x = xbase + lower_x+int(tile_x)
	upper_y = ybase + lower_y+int(tile_y)
	newquery = "select * from subarray(("+orig_query+"),"+str(lower_x)+","+str(lower_y)+","+str(upper_x)+","+str(upper_y)+")"
        newquery = str(newquery)
	print "newquery: ",newquery
	sdbioptions = {'db':aggregate_options['db'],'afl':False}
	qpresults = verifyQuery(newquery,sdbioptions)
	sdbioptions['reduce_res'] = qpresults['size'] > threshold
	if sdbioptions['reduce_res']:
		aggregate_options['qpresults'] = qpresults
		aggregate_options['threshold'] = threshold
		aggregate_options['tile'] = True
		sdbioptions['reduce_options'] = aggregate_options
	result = executeQuery(newquery,sdbioptions)
	result[1]['total_tiles'] = total_tiles
	result[1]['total_tiles_root'] = total_tiles_root
	return result

#orig_query = original user query
#cx,cy= center
#l = current zoom level
#d = resolution difference between zoom levels along 1 axis
#threshold = tile size, used for resolution reduction and tile computation
#mxn = original array dimensions
#TODO: just pass qpresults!!!!!
def getTileByDimID(orig_query,n,xid,yid,tile_xid,tile_yid,l,max_l,d,x,xbase,y,ybase,threshold,aggregate_options): # zero-based indexing
	print "tile id request: (",tile_xid,",",tile_yid,")"
	root_threshold = math.ceil(math.sqrt(threshold)) # assume the tiles are squares
	orig_query = re.sub("(\'|\")","\\\1",orig_query) #escape single and double quotes
	total_xtiles = math.ceil(x/root_threshold) # number of tiles along x axis on the lowest level
	total_ytiles = math.ceil(y/root_threshold) # number of tiles along y axis on the lowest level
	bottomtiles_per_currenttile = math.pow(d,max_l-l)
	total_xtiles_l = math.ceil(total_xtiles/bottomtiles_per_currenttile) # number of tiles along the x axis on the current level
	total_ytiles_l = math.ceil(total_xtiles/bottomtiles_per_currenttile) # number of tiles along the y axis on the current level
	print "level: ",l,", total levels: ",max_l
	print "total bottomtiles x: ",total_xtiles
	print "total bottomtiles y: ",total_ytiles
	print "root_threshold: ",root_threshold
	total_tiles = total_xtiles_l * total_ytiles_l
	if tile_xid < 0 or tile_xid >= total_xtiles_l: #default, get a middle tile
		tile_xid = int(total_xtiles_l/2)
	if tile_yid < 0 or tile_yid >= total_ytiles_l: #default, get a middle tile
		tile_yid = int(total_ytiles_l/2)
	tile_width = root_threshold*math.pow(d,max_l-l) # figure out tile dimensions
	# get future info about the tile
	lower_x = int(xbase + tile_width*tile_xid)
	lower_y = int(ybase + tile_width*tile_yid)
	upper_x = int(lower_x+tile_width)
	upper_y = int(lower_y+tile_width)
	bottomtiles_per_currenttile_plus1level = math.pow(d,max_l-min(l+1,max_l))
	future_xtiles = d # how many tiles at the next zoom level are in this tile along the x axis
	future_ytiles = d # how many tiles at the next zoom level are in this tile along the y axis
	print "bottomtiles_per_currenttile: ",bottomtiles_per_currenttile
	print "bottomtiles_per_currenttile_plus1level: ",bottomtiles_per_currenttile_plus1level
	if upper_x > (x + xbase): # if this tile contains less than d tiles at the next zoom level (edge case)
		total_bottomtiles_x_here = total_xtiles - (total_xtiles_l-1)*bottomtiles_per_currenttile
		print "total_bottomtiles_x_here: ",total_bottomtiles_x_here
		future_xtiles = math.ceil(total_bottomtiles_x_here/bottomtiles_per_currenttile_plus1level)
	if upper_y > (y + ybase): # if this tile contains less than d tiles at the next zoom level (edge case)
		total_bottomtiles_y_here = total_ytiles - (total_ytiles_l-1)*bottomtiles_per_currenttile
		print "total_bottomtiles_y_here: ",total_bottomtiles_y_here
		future_ytiles = math.ceil(total_bottomtiles_y_here/bottomtiles_per_currenttile_plus1level)
	print "current_xtiles: ",total_xtiles_l
	print "current_ytiles: ",total_ytiles_l
	print "future_xtiles: ",future_xtiles
	print "future_ytiles: ",future_ytiles
	newquery = "select * from subarray(("+orig_query+")"
	for i in range(n):
		if i == xid:
			newquery += "," + str(lower_x)
		elif i == yid:
			newquery += "," + str(lower_y)
		else:
			newquery += ",0"
	for i in range(n):
		if i == xid:
			newquery += "," + str(upper_x)
		elif i == yid:
			newquery += "," + str(upper_y)
		else:
			newquery += ",0"
	newquery += ")"
	#newquery = "select * from subarray(("+orig_query+"),"+str(lower_x)+","+str(lower_y)+","+str(upper_x)+","+str(upper_y)+")"
        newquery = str(newquery)
	print "newquery: ",newquery
	sdbioptions = {'db':aggregate_options['db'],'afl':False}
	qpresults = verifyQuery(newquery,sdbioptions)
	#print "qpresults:",qpresults
	sdbioptions['reduce_res'] = True #qpresults['size'] > threshold
	#if sdbioptions['reduce_res']:
	aggregate_options['qpresults'] = qpresults
	aggregate_options['resolution'] = threshold
	aggregate_options['tile'] = True
	sdbioptions['reduce_options'] = aggregate_options
	result = executeQuery(newquery,sdbioptions)
	result[1]['total_xtiles'] = total_xtiles_l
	result[1]['total_ytiles'] = total_ytiles_l
	result[1]['future_xtiles'] = future_xtiles
	result[1]['future_ytiles'] = future_ytiles
	result[1]['total_tiles'] = total_tiles
	result[1]['total_tiles_root'] = math.sqrt(total_tiles)
	return result

#orig_query = original user query
#cx,cy= center
#l = current zoom level
#d = resolution difference between zoom levels along 1 axis
#threshold = tile size, used for resolution reduction and tile computation
#mxn = original array dimensions
#TODO: just pass qpresults!!!!!
def getTileByIDXY(orig_query,n,xid,yid,tile_xid,tile_yid,l,max_l,d,x,xbase,y,ybase,threshold,aggregate_options): # zero-based indexing
	print "tile id request: (",tile_xid,",",tile_yid,")"
	root_threshold = math.ceil(math.sqrt(threshold)) # assume the tiles are squares
	orig_query = re.sub("(\'|\")","\\\1",orig_query) #escape single and double quotes
	total_xtiles = math.ceil(x/root_threshold) # number of tiles along x axis on the lowest level
	total_ytiles = math.ceil(y/root_threshold) # number of tiles along y axis on the lowest level
	bottomtiles_per_currenttile = math.pow(d,max_l-l)
	total_xtiles_l = math.ceil(total_xtiles/bottomtiles_per_currenttile) # number of tiles along the x axis on the current level
	total_ytiles_l = math.ceil(total_xtiles/bottomtiles_per_currenttile) # number of tiles along the y axis on the current level
	total_xtiles_lexact = 1.0*total_xtiles/bottomtiles_per_currenttile
	total_ytiles_lexact = 1.0*total_ytiles/bottomtiles_per_currenttile
	print "level: ",l,", total levels: ",max_l
	print "total bottomtiles x: ",total_xtiles
	print "total bottomtiles y: ",total_ytiles
	print "root_threshold: ",root_threshold
	total_tiles = total_xtiles_l * total_ytiles_l
	if tile_xid < 0 or tile_xid >= total_xtiles_l: #default, get a middle tile
		tile_xid = int(total_xtiles_l/2)
	if tile_yid < 0 or tile_yid >= total_ytiles_l: #default, get a middle tile
		tile_yid = int(total_ytiles_l/2)
	tile_width = root_threshold*math.pow(d,max_l-l) # figure out tile dimensions
	# get future info about the tile
	lower_x = int(xbase + tile_width*tile_xid)
	lower_y = int(ybase + tile_width*tile_yid)
	upper_x = int(lower_x+tile_width)
	upper_y = int(lower_y+tile_width)
	bottomtiles_per_currenttile_plus1level = math.pow(d,max_l-min(l+1,max_l))
	future_xtiles = d # how many tiles at the next zoom level are in this tile along the x axis
	future_ytiles = d # how many tiles at the next zoom level are in this tile along the y axis
	future_xtiles_exact = future_xtiles
	future_ytiles_exact = future_ytiles
	print "bottomtiles_per_currenttile: ",bottomtiles_per_currenttile
	print "bottomtiles_per_currenttile_plus1level: ",bottomtiles_per_currenttile_plus1level
	if upper_x > (x + xbase): # if this tile contains less than d tiles at the next zoom level (edge case)
		total_bottomtiles_x_here = total_xtiles - (1.0*total_xtiles_l-1)*bottomtiles_per_currenttile
		print "total_bottomtiles_x_here: ",total_bottomtiles_x_here
		future_xtiles_exact = total_bottomtiles_x_here/bottomtiles_per_currenttile_plus1level
		future_xtiles = math.ceil(future_xtiles_exact)
	print "upper_y:",upper_y,"y:",y,"ybase:",ybase
	if upper_y > (y + ybase): # if this tile contains less than d tiles at the next zoom level (edge case)
		total_bottomtiles_y_here = total_ytiles - (1.0*total_ytiles_l-1)*bottomtiles_per_currenttile
		print "total_bottomtiles_y_here: ",total_bottomtiles_y_here
		future_ytiles_exact = total_bottomtiles_y_here/bottomtiles_per_currenttile_plus1level
		future_ytiles = math.ceil(future_ytiles_exact)
	print "current_xtiles: ",total_xtiles_l
	print "current_ytiles: ",total_ytiles_l
	print "current_xtiles_exact: ",total_xtiles_l
	print "current_ytiles_exact: ",total_ytiles_l
	print "future_xtiles_exact: ",future_xtiles_exact
	print "future_ytiles_exact: ",future_ytiles_exact
	print "future_xtiles: ",future_xtiles
	print "future_ytiles: ",future_ytiles
	newquery = "select * from subarray(("+orig_query+")"
	for i in range(n):
		if i == xid:
			newquery += "," + str(lower_x)
		elif i == yid:
			newquery += "," + str(lower_y)
		else:
			newquery += ",0"
	for i in range(n):
		if i == xid:
			newquery += "," + str(upper_x)
		elif i == yid:
			newquery += "," + str(upper_y)
		else:
			newquery += ",0"
	newquery += ")"
	#newquery = "select * from subarray(("+orig_query+"),"+str(lower_x)+","+str(lower_y)+","+str(upper_x)+","+str(upper_y)+")"
        newquery = str(newquery)
	print "newquery: ",newquery
	sdbioptions = {'db':aggregate_options['db'],'afl':False}
	qpresults = verifyQuery(newquery,sdbioptions)
	#print "qpresults:",qpresults
	sdbioptions['reduce_res'] = True #qpresults['size'] > threshold
	#if sdbioptions['reduce_res']:
	aggregate_options['qpresults'] = qpresults
	aggregate_options['resolution'] = threshold
	aggregate_options['tile'] = True
	sdbioptions['reduce_options'] = aggregate_options
	result = executeQuery(newquery,sdbioptions)
	result[1]['total_xtiles'] = total_xtiles_l
	result[1]['total_ytiles'] = total_ytiles_l
	result[1]['future_xtiles'] = future_xtiles
	result[1]['future_ytiles'] = future_ytiles
	result[1]['total_tiles'] = total_tiles
	result[1]['total_tiles_root'] = math.sqrt(total_tiles)
	result[1]['total_xtiles_exact'] = total_xtiles_lexact
	result[1]['total_ytiles_exact'] = total_ytiles_lexact
	result[1]['future_xtiles_exact'] = future_xtiles_exact
	result[1]['future_ytiles_exact'] = future_ytiles_exact
	return result

#orig_query = original user query
#cx,cy= center
#l = current zoom level
#d = resolution difference between zoom levels along 1 axis
#threshold = tile size, used for resolution reduction and tile computation
#mxn = original array dimensions
def oldgetTileByIDXY(orig_query,tile_xid,tile_yid,l,max_l,d,x,xbase,y,ybase,threshold,aggregate_options): # zero-based indexing
	orig_query = re.sub("(\'|\")","\\\1",orig_query) #escape single and double quotes
	total_tiles = math.pow(d,l) # number of tiles along 1 axis (square for all tiles at this levels)
	if tile_xid < 0 or tile_xid >= total_tiles: #default, get a middle tile
		tile_xid = int(totaltiles/2)
	if tile_yid < 0 or tile_yid >= total_tiles: #default, get a middle tile
		tile_yid = int(totaltiles/2)
	tile_xwidth = x/total_tiles # figure out tile dimensions
	tile_ywidth = y/total_tiles
	lower_x = xbase + int(tile_xwidth*tile_xid)
	lower_y = ybase + int(tile_ywidth*tile_yid)
	upper_x = xbase + lower_x+int(tile_xwidth)
	upper_y = ybase + lower_y+int(tile_ywidth)
	newquery = "select * from subarray(("+orig_query+"),"+str(lower_x)+","+str(lower_y)+","+str(upper_x)+","+str(upper_y)+")"
        newquery = str(newquery)
	print "newquery: ",newquery
	sdbioptions = {'db':aggregate_options['db'],'afl':False}
	qpresults = verifyQuery(newquery,sdbioptions)
	sdbioptions['reduce_res'] = qpresults['size'] > threshold
	if sdbioptions['reduce_res']:
		aggregate_options['qpresults'] = qpresults
		aggregate_options['threshold'] = threshold
		aggregate_options['tile'] = True
		sdbioptions['reduce_options'] = aggregate_options
	result = executeQuery(newquery,sdbioptions)
	result[1]['total_tiles'] = total_tiles*total_tiles
	result[1]['total_tiles_root'] = total_tiles
	return result
	

#options: {'afl':True/False}
#required options: afl
#function to verify query query result size
def verifyQuery(query,options):
	queryplan = query_optimizer(query,options)
	return check_query_plan(queryplan) #returns a dictionary

#function to do the resolution reduction when running queries
# results from check_query_plan: [size,dims,names]
#options:{'afl':True/False,reduce_res:True/False,'reduce_options':options}
#required options: reduce_res, reduce_options if reduce_res is true, afl if reduce_res is false
def executeQuery(query,options):
	db = options['db']
	print  "executing query",datetime.now()
	final_query = query
	if(options['reduce_res']): #reduction requested
		if 'resolution' in options:
			resolution = options['resolution']
			options['reduce_options']['resolution']=resolution
		options['reduce_options']['db'] = db
		return reduce_resolution(query,options['reduce_options'])
	else:
		print  "running original query."
		#print  "final query:",final_query#,"\nexecuting query",datetime.now()
		result = []
		if options['afl']:
			result.append(db.executeQuery(final_query,'afl'))
		else:
			result.append(db.executeQuery(final_query,'aql'))
		result.append(verifyQuery(final_query,options))
		return result

#function to do the resolution reduction when running queries
# get the queryplan for the given query and return the line with info about the result matrix
def query_optimizer(query,options):
	db = options['db']
	afl = options['afl']
	query = re.sub("(\\')","\\\\\\1",query)
	# eventually want to be able to infer this
	queryplan_query = ""
	optimizer_answer = []
	if(afl):
		queryplan_query = LOGICAL_PHYSICAL+"('"+query+"','afl')"
	else:
		queryplan_query = LOGICAL_PHYSICAL+"('"+query+"','aql')"
	#print  "queryplan query: "
	#print  queryplan_query
	optimizer_answer = db.executeQuery(queryplan_query,'afl')
	#print  optimizer_answer
	# flatten the list into one big string, and then split on '\n'
	optimizer_answer_array = getOneAttrArrFromQuery(optimizer_answer,"")[0].split('\n') #should return array with one item (the query plan)
	# find the line with the first instance of 'schema' in the front
	for i, s in enumerate(optimizer_answer_array):
		if(re.search("^\s*schema", s)):
			return s

# get the matrix size (across all dimensions) and the number of dimensions of the result matrix
def check_query_plan(queryplan):
	# get the text in between the square brackets
	queryplan = str(queryplan)
	dim_string = queryplan[queryplan.find("[")+1:queryplan.find("]")]
	dim_array = dim_string.split(',')
	#print  dim_array
	dims = 0
	size = 1
	names = []
	bases= {}
	widths = {}
	indexes = {}
	for i, s in enumerate(dim_array):
		if (i % 3) == 0:
			# split on equals, get the range, split on ':'
			#print  "s:",s
			range = s.split('=')[1]
			name = s.split('=')[0]
			if name.find("(") != -1:
				name = name[:name.find("(")]
				name = "dims."+name
				rangewidth = int(range)
				bases[name] = 1 #1 by default
			else:
				name = "dims."+name
				rangevals = range.split(':')
				rangewidth = int(rangevals[1]) - int(rangevals[0]) + 1
				bases[name]=rangevals[0];
			names.append(name)
			indexes[name] = dims
			size *= rangewidth
			dims += 1
			widths[name] =rangewidth;
	return {'size': size, 'numdims': dims, 'dims': names, 'indexes':indexes, 'attrs':get_attrs(queryplan),'dimbases':bases,'dimwidths':widths}

#get all attributes of the result matrix
def get_attrs(queryplan):
	# get the text in between the angle brackets
	attr_string = queryplan[queryplan.find('<')+1:queryplan.find('>')]
	attr_array = attr_string.split(',')
	names = []
	types = []
	for i,s in enumerate(attr_array):
		name_type = (s.split(' ')[0]).split(':') # does this work?
		names.append(name_type[0])
		types.append(name_type[1])
	return {'names':names,'types':types}

#options: {'numdims':int, 'chunkdims': [ints], 'attrs':[strings],'flex':'more'/'less'/'none','afl':True/False, 'qpsize':int}
#required options: numdims, afl, attrs, attrtypes, qpsize
#NOTE: ASSUMES AVG IS THE AGG FUNCTION!
#TODO: Fix the avg func assumption
def daggregate(query,options):
	final_query = query
	if 'threshold' in options:
		threshold = options['threshold']
	else:
		threshold= D3_DATA_THRESHOLD
	dimension = options['numdims']
	chunks = ""
	if ('chunkdims' in options) and (len(options['chunkdims']) > 0): #chunkdims specified
		chunkdims = options['chunkdims']
		chunks += str(chunkdims[0])
		for i in range(1,len(chunkdims)):
			chunks += ", "+str(chunkdims[i])
	elif dimension > 0: # otherwise do default chunks
		quotient = 1.0*options['qpsize']/threshold # approximate number of base tiles
		defaultchunkval = math.pow(quotient,1.0/dimension)
		if quotient < 1.0:
			if ('tile' in options) and options['tile']:
				defaultchunkval = TILE_AGGR_CHUNK_DEFAULT
			else:
				defaultchunkval = AGGR_CHUNK_DEFAULT
		defaultchunkval = int(math.ceil(defaultchunkval)) # round up
		chunks += str(defaultchunkval)
		#chunks += options['dimnames'][0]+" "+ str(defaultchunkval)
		for i in range(1,dimension) :
			chunks += ", "+str(defaultchunkval)
			#chunks += ", "+ options['dimnames'][i]+" "+ str(defaultchunkval)
	# need to escape apostrophes or the new query will break
	attrs = options['attrs']
	#final_query = re.sub("(')","\\\1",final_query)

	#make the new query an aql query so we can rename the aggregates easily
	attraggs = ""
	#print  "options attrtypes: ",options['attrtypes']
	for i in range(0,len(attrs)):
		#print  "attr type: ",options['attrtypes'][i]
		if (options['attrtypes'][i] == "int32") or (options['attrtypes'][i] == "int64") or (options['attrtypes'][i] == "double"): # make sure types can be aggregated
			if attraggs != "":
				attraggs += ", "
			attraggs+= "avg("+str(attrs[i])+") as avg_"+attrs[i]
			attraggs+= ", min("+str(attrs[i])+") as min_"+attrs[i] # need for the color scale
			attraggs+= ", max("+str(attrs[i])+") as max_"+attrs[i] # need for the color scale
	final_query = "select "+attraggs+" from ("+ final_query +") regrid "+chunks
	#final_query = "select "+attraggs+" from ("+ final_query +") regrid as ( partition by "+chunks
	#if ('fillzeros' in options) and (options['fillzeroes']): # fill nulls with zeros
	#	
	#final_query = "regrid(("+final_query+"),"+chunks+","+attraggs+")" # afl
	print  "final query:",final_query
	#result = []
	#result = db.executeQuery(final_query,'aql')
	#return result
	return final_query

#options: {'probability':double, 'afl':True/False, 'flex':'more'/'less'/'none','qpsize':int, 'bychunk':True/False }
#required options: afl, probability OR qpsize
def dsample(query,options):
	final_query = query
	probability = PROB_DEFAULT # this will change depending on what user specified
	if 'probability' in options: #probability specified
		probability = options['probability']
	elif 'threshold' in options:
		threshold = options['threshold']
		probability = min([1,threshold * 1.0 / options['qpsize']])
	else:
		probability = min([1,D3_DATA_THRESHOLD * 1.0 / options['qpsize']])
	probability = str(probability);
	# need to escape apostrophes or the new query will break
	#final_query = re.sub("(')","\\\1",final_query)
	#if options['afl']:
	#	final_query = "bernoulli(("+final_query+"), "+probability+")"
	#else:
	final_query = "select * from bernoulli(("+ final_query +"), "+probability+")"
	#print  "final query:",final_query,"\nexecuting query..."
	#if options['afl']:
	#	result = db.executeQuery(final_query,'afl')
	#else:
	#	result = db.executeQuery(final_query,'aql')
	#return result
	return final_query

#options: {'afl':True/False,'predicate':"boolean expression"}
#required options: afl, predicate
def dfilter(query, options):
	final_query = query
	# need to escape apostrophes or the new query will break
	#final_query = re.sub("(')","\\\1",final_query)
	#if options['afl']:
	#	final_query = "filter(("+final_query+"), "+options['predicate']+")"
	#else:
	final_query = "select * from ("+final_query+") where "+options['predicate']
	#print  "final query:",final_query,"\nexecuting query..."
	#if options['afl']:
	#	result = db.executeQuery(final_query,'afl')
	#else:
	#	result = db.executeQuery(final_query,'aql')
	#return result
	return final_query

#options: {'qpresults':qpresults,'afl':afl, 'reduce_type':RES_TYPE,'predicate':"boolean expression"}
#required options: reduce_type, qpresults, afl, predicate (if RESTYPE['FILTER'] is specified)
#RESTYPE = {'AGGR': 'aggregate', 'SAMPLE': 'sample','OBJSAMPLE': 'samplebyobj','OBJAGGR': 'aggregatebyobj', 'BSAMPLE': 'biased_sample'}
def reduce_resolution(query,options):
	db = options['db']
	reduce_type = options['reduce_type']
	qpresults = options['qpresults']
	print "qpresults:",qpresults
	#add common reduce function options
	reduce_options = {'afl':options['afl'],'qpsize':qpresults['size']}
	if 'tile' in options:
		reduce_options['tile'] = options['tile']
	if 'resolution' in options:
		reduce_options['threshold'] = options['resolution']
        query = re.sub(r"[^\\](\'|\")","\\\1",query) #escape single and double quotes
	if reduce_type == RESTYPE['AGGR']:
		if 'chunkdims' in options: #user specified chunk dims
			reduce_options['chunkdims'] = options['chunkdims']
		reduce_options['numdims'] = qpresults['numdims']
		reduce_options['attrs'] = qpresults['attrs']['names']
		reduce_options['attrtypes'] = qpresults['attrs']['types']
		reduce_options['dimnames'] = qpresults['dims']
		newquery = daggregate(query,reduce_options)
	elif reduce_type == RESTYPE['SAMPLE']:
		if 'probability' in options:
			reduce_options['probability'] = options['probability']
		newquery = dsample(query,reduce_options)
	elif reduce_type == RESTYPE['FILTER']:
		reduce_options['predicate']=options['predicate']
		newquery = dfilter(query,reduce_options)
	else:
		raise Exception('reduce_type not recognized by scidb interface api')
	result =[]
        newquery = str(newquery)
	result.append(db.executeQuery(newquery,'aql'))
	result.append(verifyQuery(newquery,{'afl':False,'db':db}))
	#print  result[1]
	return result

# function used to build a python "array" out of the given
# scidb query result. attrname must be exact attribute 
# name or this defaults to first attribute
def getOneAttrArrFromQuery(query_result,attrname):
	desc = query_result.array.getArrayDesc()
	dims = desc.getDimensions() # list of DimensionDesc objects
	attrs = desc.getAttributes() # list of AttributeDesc objects

	dimlengths= []
	dimchunkintervals = []
	dimoverlaps = []
	dimindexes = []
	dimindexesbase = []

	if(dims.size() < 1):
		return [];

	for i in range(dims.size()):
		dimlengths.append(dims[i].getLength())
		dimchunkintervals.append(dims[i].getChunkInterval())
		dimoverlaps.append(dims[i].getChunkOverlap())
		dimindexes.append(0)
		dimindexesbase.append(0)

	# get arr ready
	arr = createArray(dimlengths)
	#print  "arr is initialized: ",str(arr)
	attrid = 0
	for i in range(attrs.size()): # find the right attrid
		if(attrs[i].getName() == attrname):
			attrid = i
			#print  "found attribute",attrname, ",id: %d" % attrid 
			break

	# get the iterator for this attrid
	it = query_result.array.getConstIterator(attrid)

	start = True
	while not it.end():
		#print  "iterating over items..."
		currentchunk = it.getChunk()
		# TODO: will have to fix this at some point, can't just ignore empty cells or overlaps
		chunkiter = currentchunk.getConstIterator((scidb.swig.ConstChunkIterator.IGNORE_EMPTY_CELLS |
                                               scidb.swig.ConstChunkIterator.IGNORE_OVERLAPS))

		if(not start): # don't update for the first chunk
			#update base indexes
			dimindexesbase = updateBaseIndex(dimindexesbase,dimlengths,dimchunkintervals)
			#printIndexes(dimindexesbase)
			verifyIndexes(dimindexesbase,dimlengths)
				
			#reset the indexes to new base indexes
			for i in range (dims.size()):
				dimindexes[i] = dimindexesbase[i]
		else:
			start = False

		while not chunkiter.end():
			#printIndexes(dimindexes)
			verifyIndexes(dimindexes,dimlengths)
			dataitem = chunkiter.getItem()
			# look up the value according to its attribute's typestring
			item = scidb.getTypedValue(dataitem, attrs[attrid].getType()) # TBD: eliminate 2nd arg, make method on dataitem
			#print  "Data: %s" % item

			#insert the item
			arr = insertItem(arr,item,dimindexes)
			#update the indexes
			dimindexes = updateIndexes(dimindexes,dimchunkintervals,dimindexesbase,dimlengths)
			lastpos = chunkiter.getPosition()
			#print  lastpos[0],",",lastpos[1], ",",lastpos[2]
			chunkiter.increment_to_next()
		#print  "current state of arr: ", str(arr)
		it.increment_to_next();
	return arr

# debugging function used to print the given list of indexes
def printIndexes(dimlist):
	for i in range(len(dimlist)):
		print  "dim ", str(i), "has index %d" % dimlist[i]

# function that verifies that we are not trying to use indexes
# that are out of bounds
def verifyIndexes(dimlist,dimboundaries):
	for i in range(len(dimlist)):
		assert dimlist[i] < dimboundaries[i], "indexes out of range." #" index:",str(dimlist[i]),", boundary:",str(dimboundaries[i])

# function to update to the next appropriate index location after inserting 1 item
#not to be confused with the similar updateBaseIndex, which updates by chunk lengths
def updateIndexes(dimindexes,dimchunkintervals, dimindexesbase,dimlengths):
	i = len(dimindexes) - 1
	while i > 0:
		dimindexes[i] += 1
		if((dimindexes[i] - dimindexesbase[i]) >= dimchunkintervals[i]):
			dimindexes[i] = dimindexesbase[i]
			# next dimension up will be incremented in next iteration of the while loop
			i -= 1
		elif(dimindexes[i] >= dimlengths[i]): # edge case for odd chunks
			dimindexes[i]= dimindexesbase[i]
			i-= 1
		else:
			break
	if(i == 0):
		dimindexes[i] += 1
	return dimindexes

#function to recompute the base indexes when we've completed
#traversal of the current chunk
def updateBaseIndex(dimindexesbase,dimlengths,dimchunkintervals):
	i = len(dimindexesbase) - 1
	while i > 0:
		dimindexesbase[i] += dimchunkintervals[i]
		if(dimindexesbase[i] >= dimlengths[i]):
			dimindexesbase[i] = 0
			i -= 1
		else:
			break	
	if(i == 0):
		dimindexesbase[i] += dimchunkintervals[i]
	return dimindexesbase

#exterior function to insert the given item in the the array using the given indexes
def insertItem(arr,item,dimindexes):
	#print  "inserting item %d" % item
	return insertItemHelper(arr,item,dimindexes,0,len(dimindexes))

#helper function to recursively find the appropriate list to insert the item into in the array
def insertItemHelper(arr,item,dimindexes,currdim,numdims):
	if(currdim == (numdims-1)):
		arr[dimindexes[currdim]] = item
	else:
		arr[dimindexes[currdim]] = insertItemHelper(arr[dimindexes[currdim]],item,dimindexes,currdim + 1, numdims)
	return arr

#exterior function for initializing an array of the appropriate size
def createArray(dimlengths):
	return createArrayHelper(dimlengths,0,len(dimlengths))

#helper function for createArray to do the recursive building of the array to be initialized
def createArrayHelper(dimlengths,currdim,numdims):
	arr = [0]*dimlengths[currdim]
	if(currdim < (numdims-1)):
		for i in range(dimlengths[currdim]):
			arr[i] = createArrayHelper(dimlengths,currdim+1,numdims)
	return arr
		
#returns an array of dictionaries, each dictionary contains values for all the attributes
# (probably sets some values to null or string saying null if the vals are null in the array)
def getAllAttrArrFromQuery(query_result):
	desc = query_result.array.getArrayDesc()
	dims = desc.getDimensions() # list of DimensionDesc objects
	attrs = desc.getAttributes() # list of AttributeDesc objects

	dimlengths= []
	dimchunkintervals = []
	dimoverlaps = []
	dimindexes = []
	dimindexesbase = []

	if(dims.size() < 1):
		return []

	for i in range(dims.size()):
		dimlengths.append(dims[i].getLength())
		dimchunkintervals.append(dims[i].getChunkInterval())
		dimoverlaps.append(dims[i].getChunkOverlap())
		dimindexes.append(0)
		dimindexesbase.append(0)

	# get arr ready
	arr = createArray(dimlengths)
	#print  "arr is initialized: ",str(arr)

	its = []
	attrnames = []
	for i in range(attrs.size()): # find the right attrid
		its.append(query_result.array.getConstIterator(i))
		attrnames.append(attrs[i].getName())

	start = True
	while not its[0].end():
		#get chunk iterators
		chunkiters = []
		for itindex in range(len(its)):
			#print  "itindex: ",itindex
			currentchunk =its[itindex].getChunk()
			chunkiter = currentchunk.getConstIterator((scidb.swig.ConstChunkIterator.IGNORE_EMPTY_CELLS |
		                                       scidb.swig.ConstChunkIterator.IGNORE_OVERLAPS))
			chunkiters.append(chunkiter)

		if(not start): # don't update for the first chunk
			#update base indexes
			dimindexesbase = updateBaseIndex(dimindexesbase,dimlengths,dimchunkintervals)
			#printIndexes(dimindexesbase)
			verifyIndexes(dimindexesbase,dimlengths)
			
			#reset the indexes to new base indexes
			for i in range (dims.size()):
				dimindexes[i] = dimindexesbase[i]
		else:
			start = False

		while not chunkiters[0].end():
			#printIndexes(dimindexes)
			verifyIndexes(dimindexes,dimlengths)
			item = {} #empty dictionary for the attribute values
			for chunkiterindex in range(len(chunkiters)):
				#print  "chunkiterindex: ",chunkiterindex
				dataitem = chunkiters[chunkiterindex].getItem()
				# look up the value according to its attribute's typestring
				item[attrnames[chunkiterindex]] = scidb.getTypedValue(dataitem, attrs[chunkiterindex].getType()) # TBD: eliminate 2nd arg, make method on dataitem
				#print  "Data: %s" % item
				#chunkiters[i].increment_to_next()
			chunkiters[0].increment_to_next() # OMG THIS INCREMENTS ALL THE CHUNK ITERATOR OBJECTS
			#lastpos = chunkiter.getPosition()
			#print  lastpos[0],",",lastpos[1], ",",lastpos[2]
			#print  item
			#insert the item
			arr = insertItem(arr,item,dimindexes)
			#update the indexes
			dimindexes = updateIndexes(dimindexes,dimchunkintervals,dimindexesbase,dimlengths)
			#print  "current state of arr: ", str(arr)
		its[0].increment_to_next()
	return arr

#does returns items in a nicer/more accurate format for JSON
#organization is an array of objects, where each object has a dimensions object and attributes object.
#There is one object per element in the matrix
#example:
# [
#    {
#      'dimensions': {...},
#      'attributes': {...},
#    },
#    ...
# ]
#Note that this is *not* in matrix form, it is in list form essentially
#so dimensions are not validated or anything
#dimnames: a list containing the names of the matrix dimensions
# MUST BE THE CORRECT LENGTH
#options: {'dimnames':[]}
#required options: dimnames
def getAllAttrArrFromQueryForJSON(query_result,options):
	print  "parsing query result and building json dump",datetime.now()
	dimnames = options['dimnames']
	desc = query_result.array.getArrayDesc()
	dims = desc.getDimensions() # list of DimensionDesc objects
	attrs = desc.getAttributes() # list of AttributeDesc objects
	origarrnamelen = 0#len(desc.getName()) - 2
	#print  "array name: ",desc.getName()
	#print  "array name length: ",origarrnamelen

	if(dims.size() < 1 or dims.size() != len(dimnames)):
		return []

	arr = []
	its = []
	attrnames = []
	minobj = {}
	maxobj = {}
	for i in range(attrs.size()): # find the right attrid
		if attrs[i].getName() != "EmptyTag":
			its.append(query_result.array.getConstIterator(i))
			attrnames.append(attrs[i].getName())
			currtype = attrs[i].getType()
			if (currtype == "int32") or (currtype == "int64") or (currtype == "double"):
				minobj["attrs."+attrs[i].getName()] = None
				maxobj["attrs."+attrs[i].getName()] = None

	start = True
	while not its[0].end():
		#get chunk iterators
		chunkiters = []
		#print  "start"
		for itindex in range(len(its)):
			#print  "itindex: ",itindex
			#mypos = its[itindex].getPosition()
			#print  "position:"
			#print  mypos[0],",",mypos[1]
			currentchunk =its[itindex].getChunk()
			chunkiter = currentchunk.getConstIterator((scidb.swig.ConstChunkIterator.IGNORE_EMPTY_CELLS |
		                                       scidb.swig.ConstChunkIterator.IGNORE_OVERLAPS))
			chunkiters.append(chunkiter)

		while not chunkiters[0].end():
			dataobj = {}
			dimobj= {}

			currpos = chunkiters[0].getPosition()
			for dimindex in range(len(currpos)):
				dname = dimnames[dimindex]
				dimobj[dname[:len(dname)-origarrnamelen]] = currpos[dimindex] # make sure you take off the array's name from each dimension
				#dataobj["dims."+dname[:len(dname)-origarrnamelen]] = currpos[dimindex]
				dataobj[dname[:len(dname)-origarrnamelen]] = currpos[dimindex]
			attrobj = {} #empty dictionary for the attribute values
			#print  "start"
			minval = None
			for chunkiterindex in range(len(chunkiters)):
				#print  "chunkiterindex: ",chunkiterindex
				dataitem = chunkiters[chunkiterindex].getItem()
				# look up the value according to its attribute's typestring
				currtype = attrs[chunkiterindex].getType()
				dataitem_val = scidb.getTypedValue(dataitem, currtype)
				attrobj[attrnames[chunkiterindex]] = dataitem_val # TBD: eliminate 2nd arg, make method on dataitem
				dataobj["attrs."+attrnames[chunkiterindex]] = dataitem_val
				
				if (currtype == "int32") or (currtype == "int64") or (currtype == "double"):
					if (minobj["attrs."+attrnames[chunkiterindex]] is None) or (dataitem_val < minobj["attrs."+attrnames[chunkiterindex]]):
						minobj["attrs."+attrnames[chunkiterindex]] = dataitem_val
					if (maxobj["attrs."+attrnames[chunkiterindex]] is None) or (dataitem_val > maxobj["attrs."+attrnames[chunkiterindex]]):
						maxobj["attrs."+attrnames[chunkiterindex]] = dataitem_val
				#print  "Data: %s" % item
				#chunkiters[i].increment_to_next()
				#mypos = chunkiters[chunkiterindex].getPosition()
				#myposstring = "position: "
				#for myposi in range(len(mypos)):
				#	myposstring += str(mypos[myposi])+", "
				#print  myposstring
				chunkiters[chunkiterindex].increment_to_next() # OMG THIS INCREMENTS ALL THE CHUNK ITERATOR OBJECTS
			
			#lastpos = chunkiter.getPosition()
			#print  lastpos[0],",",lastpos[1], ",",lastpos[2]
			#print  attrobj
			#insert the item
			arr.append(dataobj)
			#arr.append({'dimensions':dimobj,'attributes':attrobj})
			#print  "current state of arr: ", str(arr)
		#its[1].increment_to_next()
		for itindex in range(len(its)):		
			its[itindex].increment_to_next()
	namesobj = []
	typesobj = {}
	for attri in range(len(attrnames)):
		attrname = attrnames[attri]
		namesobj.append({'name':"attrs."+attrname,'isattr':True})
		typesobj["attrs."+attrname] = attrs[attri].getType()
	for dimname in dimnames:
		#ndimname = "dims."+dimname[:len(dimname)-origarrnamelen]
		ndimname = dimname[:len(dimname)-origarrnamelen]
		namesobj.append({'name':ndimname,'isattr':False})
		typesobj[ndimname] = "int32"
	#for attri in range(len(attrnames)):
	#	attrname = attrnames[attri]
	#	namesobj.append("attrs."+attrname)
	#	typesobj["attrs."+attrname] = attrs[attri].getType()
	#for dimname in dimnames:
	#	ndimname = "dims."+dimname[:len(dimname)-origarrnamelen]
	#	namesobj.append(ndimname)
	#	typesobj[ndimname] = "int32"
	#print  typesobj
	#print  	json.dumps({'data':arr, 'names': namesobj, 'types': typesobj})
	print  "done parsing results, returning dump-ready version",datetime.now()
	return {'data':arr, 'names': namesobj, 'types': typesobj,'max':maxobj,'min':minobj}
	#return {'data': arr, 'names': {'dimnames': dimnames, 'attrnames': attrnames}}
	
#returns items in a nicer/more accurate format for JSON
#organization is an array of objects, where each object has a dimensions object and attributes object.
#There is one object per element in the matrix
#example:
# [
#    {
#      'dimensions': {...},
#      'attributes': {...},
#    },
#    ...
# ]
#Note that this is *not* in matrix form, it is in list form essentially
#so dimensions are not validated or anything
#dimnames: a list containing the names of the matrix dimensions
# MUST BE THE CORRECT LENGTH
#options: {'dimnames':[],'attrnames':[]}
#required options: dimnames, attrnames
def getAttrArrFromQueryForJSON(query_result,options):
	dimnames = options['dimnames']
	attrnames = options['attrnames']
	desc = query_result.array.getArrayDesc()
	dims = desc.getDimensions() # list of DimensionDesc objects
	attrs = desc.getAttributes() # list of AttributeDesc objects
	origarrnamelen = len(desc.getName()) - 2
	#print  "orig name length: ",origarrnamelen

	if(dims.size() < 1 or dims.size() != len(dimnames)):
		return []

	arr = []
	its = []
	for i in range(attrs.size()): # find the right attrid
		for aname in attrnames:
			if aname == attrs[i].getName():
				its.append(query_result.array.getConstIterator(i))

	start = True
	while not its[0].end():
		#get chunk iterators
		chunkiters = []
		#print  "start"
		for itindex in range(len(its)):
			#print  "itindex: ",itindex
			#mypos = its[itindex].getPosition()
			#print  "position:"
			#print  mypos[0],",",mypos[1]
			currentchunk =its[itindex].getChunk()
			chunkiter = currentchunk.getConstIterator((scidb.swig.ConstChunkIterator.IGNORE_EMPTY_CELLS |
		                                       scidb.swig.ConstChunkIterator.IGNORE_OVERLAPS))
			chunkiters.append(chunkiter)

		while not chunkiters[0].end():
			dataobj = {}
			dimobj= {}
			currpos = chunkiters[0].getPosition()
			for dimindex in range(len(currpos)):
				dname = dimnames[dimindex]
				dimobj[dname[:len(dname)-origarrnamelen]] = currpos[dimindex] # make sure you take off the array's name from each dimension
				dataobj["dims."+dname[:len(dname)-origarrnamelen]] = currpos[dimindex]
			attrobj = {} #empty dictionary for the attribute values
			#print  "start"
			for chunkiterindex in range(len(chunkiters)):
				#print  "chunkiterindex: ",chunkiterindex
				dataitem = chunkiters[chunkiterindex].getItem()
				# look up the value according to its attribute's typestring
				attrobj[attrnames[chunkiterindex]] = scidb.getTypedValue(dataitem, attrs[chunkiterindex].getType()) # TBD: eliminate 2nd arg, make method on dataitem
				dataobj["attrs."+attrnames[chunkiterindex]] = scidb.getTypedValue(dataitem, attrs[chunkiterindex].getType())
				#print  "Data: %s" % item
				#chunkiters[i].increment_to_next()
				#mypos = chunkiters[chunkiterindex].getPosition()
				#myposstring = "position: "
				#for myposi in range(len(mypos)):
				#	myposstring += str(mypos[myposi])+", "
				#print  myposstring
				chunkiters[chunkiterindex].increment_to_next() # OMG THIS INCREMENTS ALL THE CHUNK ITERATOR OBJECTS
			#lastpos = chunkiter.getPosition()
			#print  lastpos[0],",",lastpos[1], ",",lastpos[2]
			#print  attrobj
			#insert the item
			arr.append(dataobj)
			#arr.append({'dimensions':dimobj,'attributes':attrobj})
			#print  "current state of arr: ", str(arr)
		#its[1].increment_to_next()
		for itindex in range(len(its)):		
			its[itindex].increment_to_next()
	namesobj = []
	typesobj = {}
	for attri in range(len(attrnames)):
		attrname = attrnames[attri]
		namesobj.append({'name':"attrs."+attrname,'isattr':True})
		typesobj["attrs."+attrname] = attrs[attri].getType()
	for dimname in dimnames:
		ndimname = "dims."+dimname[:len(dimname)-origarrnamelen]
		namesobj.append({'name':ndimname,'isattr':False})
		typesobj[ndimname] = "int32"
	#print  typesobj
	#print  	json.dumps({'data':arr, 'names': namesobj, 'types': typesobj})
	return {'data':arr, 'names': namesobj, 'types': typesobj}
	#return {'data': arr, 'names': {'dimnames': dimnames, 'attrnames': attrnames}}

#returns items in a nicer/more accurate format for JSON
#Note that this is *not* in matrix form, it is in list form essentially
#so dimensions are not validated or anything
#dimnames: a list containing the names of the matrix dimensions
# MUST BE THE CORRECT LENGTH
#options: {'dimnames':[]}
#required options: dimnames
def getMultiArrFromQueryForJSON(query_result,options):
	dimnames = options['dimnames']
	desc = query_result.array.getArrayDesc()
	dims = desc.getDimensions() # list of DimensionDesc objects
	attrs = desc.getAttributes() # list of AttributeDesc objects

	if(dims.size() < 1 or dims.size() != len(dimnames)):
		return []

	alldata = {}
	alldims = {}
	its = []
	for i in range(attrs.size()-1): # find the right attrid
		its.append(query_result.array.getConstIterator(i))

	for i in range(len(its)): # find the right attrid
		it = its[i]
		data = []
		dims = []
		while not it.end():
			chunk = it.getChunk()
			chunkiter = chunk.getConstIterator((scidb.swig.ConstChunkIterator.IGNORE_EMPTY_CELLS |
		                                       scidb.swig.ConstChunkIterator.IGNORE_OVERLAPS))
			while not chunkiter.end():
				temp = []
				pos = chunkiter.getPosition()
				for dimi in range(len(pos)):
					temp.append(pos[dimi])
				dims.append(temp)
				dataitem = chunkiter.getItem()
				typeddataitem = scidb.getTypedValue(dataitem, attrs[i].getType())
				data.append(typeddataitem)
				chunkiter.increment_to_next()
			it.increment_to_next()
		alldata[attrs[i].getName()] = data
		alldims[attrs[i].getName()] = dims

	namesobj = {'attrs':[],'dims':[]}
	typesobj = {'attrs':{},'dims':{}}
	dimmap = {}
	for attri in range(attrs.size()-1):
		attrname = attrs[attri].getName()
		namesobj['attrs'].append(attrname)
		typesobj['attrs'][attrname] = attrs[attri].getType()
	for index in range(len(dimnames)):
		dimname = dimnames[index]
		namesobj['dims'].append(dimname)
		typesobj['dims'][dimname] = "int32"
		dimmap[dimname] = index
	return {'attrs':alldata,'dims':alldims, 'dimmap':dimmap, 'names': namesobj, 'types': typesobj}

#scidbOpenConn()
#query = "select * from test3"
#query="select * from esmall"
#query = "select * from bernoulli(random_numbers_big,.01)"
#query = "scan(esmall)"
#myafl = False

#options = {'afl':myafl}
#qpresults = verifyQuery(query,options)
#print  qpresults
#options={'afl':myafl,'reduce_res':False}
#queryresult = executeQuery(query,options) # ignore reduce_type for now
#print  queryresult
#options={'dimnames':qpresults['dims']}
#queryresultarr = getAllAttrArrFromQueryForJSON(queryresult[0],options)

#options={'dimnames':qpresults['dims'],'attrnames':qpresults['attrs']['names'][0:4]}
#queryresultarr = getAttrArrFromQueryForJSON(queryresult,options)

#for i in range(len(queryresultarr['data'])):
#	print  queryresultarr['data'][i]
#	#print  "attributes: ",queryresultarr['data'][i]['attributes'],",dimensions: ",queryresultarr['data'][i]['dimensions']

#options={'dimnames':qpresults['dims']}
#queryresultarr = getMultiArrFromQueryForJSON(queryresult,options)

#print  queryresultarr

#print  qpresults['attrs']['names']
#options = {'numdims':qpresults['numdims'],'afl':myafl,'attrs':qpresults['attrs']['names'],'attrtypes':qpresults['attrs']['types'], 'qpsize':qpresults['size']}
#queryresult = daggregate(query,options)
#options={'dimnames':qpresults['dims']}
#queryresultarr = getAllAttrArrFromQueryForJSON(queryresult,options)
#print  queryresultarr

#options = {'afl':myafl,'qpsize':qpresults['size'], 'probability':.3}
#dsample(query,options)

#options = {'afl':myafl,'predicate':"lat > 0"}
#dfilter(query,options)

#scidbCloseConn()
