import string, re
#import simplejson as json
import json
import math
import MySQLdb as mysqldb
import decimal # to check for decimals, bc they are not serializable
import datetime # to check for datetimes, bc they are not serializable
import time # to convert to timestamps

LOGICAL_PHYSICAL = "explain_physical"
RESTYPE = {'AGGR': 'aggregate', 'SAMPLE': 'sample','OBJSAMPLE': 'samplebyobj','FILTER':'filter','OBJAGGR': 'aggregatebyobj', 'BSAMPLE': 'biased_sample'}
AGGR_CHUNK_DEFAULT = 10
PROB_DEFAULT = .5
SIZE_THRESHOLD = 50
D3_DATA_THRESHOLD = 10000#20000 #TODO: tune this to be accurate
#DBHOST = "localhost"
#DBUSERNAME = "failsafe"
#DBPASSWD = "password"
#DBNAME = "TNDriveToData"

DBHOST = "drivedb.byledge.net"
DBUSERNAME = "test1user"
DBPASSWD = "test1pass"
DBNAME = "TNDriveData"

#converts Python data type strings to scidb data type strings
#TODO: change server interface code to map to python types?
DATATYPE = {
	mysqldb.constants.FIELD_TYPE.CHAR:'string',
	mysqldb.constants.FIELD_TYPE.DATE:'datetime',
	mysqldb.constants.FIELD_TYPE.DATETIME:'datetime',
	mysqldb.constants.FIELD_TYPE.DECIMAL:'double',
	mysqldb.constants.FIELD_TYPE.FLOAT:'double',
	mysqldb.constants.FIELD_TYPE.INT24:'int32',
	mysqldb.constants.FIELD_TYPE.LONG:'int64',
	mysqldb.constants.FIELD_TYPE.LONGLONG:'int64',
	mysqldb.constants.FIELD_TYPE.NEWDATE:'datetime',
	mysqldb.constants.FIELD_TYPE.NEWDECIMAL:'double',
	mysqldb.constants.FIELD_TYPE.SHORT:'int32',
	mysqldb.constants.FIELD_TYPE.STRING:'string',
	mysqldb.constants.FIELD_TYPE.TIMESTAMP:'datetime',
	mysqldb.constants.FIELD_TYPE.TINY:'int32',
	mysqldb.constants.FIELD_TYPE.VAR_STRING:'string',
	mysqldb.constants.FIELD_TYPE.VARCHAR:'string',
	mysqldb.constants.FIELD_TYPE.YEAR:'int32'
}

db = 0
cur = None

def mysqlOpenConn():
	global db
	#db = MySQLdb.connect(host="localhost", # your host, usually localhost
        #             user="scidb", # your username
        #              passwd="scidb", # your password
        #              db="jonhydb") # name of the data base
	#db = scidb.connect("localhost",1239)
	#db = scidb.connect("vise4.csail.mit.edu",1239)
	db = mysqldb.connect(host=DBHOST, # your host, usually localhost
                     user=DBUSERNAME, # your username
                      passwd=DBPASSWD, # your password
                      db=DBNAME) # name of the data base

def mysqlCloseConn():
	global db
	if db != 0:
		db.close()
		db = 0

def mysqlExecuteQuery(query,options):
	global cur
	if cur is not None:
		cur.close()
		cur = None
	cur = db.cursor()
	cur.execute(query)
	#return cur.fetchall() # returns an array?
	return 0

#options: {'afl':True/False}
#required options: afl
#function to verify query query result size
def verifyQuery(query,options):
	queryplan = query_optimizer(query,options['afl'])
	return check_query_plan(queryplan) #returns a dictionary

#function to do the resolution reduction when running queries
# results from check_query_plan: [size,dims,names]
#options:{'afl':True/False,reduce_res:True/False,'reduce_options':options}
#required options: reduce_res, reduce_options if reduce_res is true, afl if reduce_res is false
def executeQuery(query,options):
	final_query = query
	if(options['reduce_res']): #reduction requested
		return reduce_resolution(query,options['reduce_options'])
	else:
		print >> sys.stderr, "running original query."
		print >> sys.stderr, "final query:",final_query,"\nexecuting query..."
		result = []
		if options['afl']:
			result.append(db.executeQuery(final_query,'afl'))
		else:
			result.append(db.executeQuery(final_query,'aql'))
		result.append(0)
		return result

#function to do the resolution reduction when running queries
# get the queryplan for the given query and return the line with info about the result matrix
def query_optimizer(query,afl):
	query = re.sub("(\\')","\\\\\\1",query)
	# eventually want to be able to infer this
	queryplan_query = ""
	optimizer_answer = []
	if(afl):
		queryplan_query = LOGICAL_PHYSICAL+"('"+query+"',\'afl\')"
	else:
		queryplan_query = LOGICAL_PHYSICAL+"('"+query+"',\'aql\')"
	print >> sys.stderr, "queryplan query: "
	print >> sys.stderr, queryplan_query
	optimizer_answer = db.executeQuery(queryplan_query,'afl')
	#print >> sys.stderr, optimizer_answer
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
	#print >> sys.stderr, dim_array
	dims = 0
	size = 1
	names = []
	bases= {}
	widths = {}
	for i, s in enumerate(dim_array):
		if (i % 3) == 0:
			# split on equals, get the range, split on ':'
			#print >> sys.stderr, "s:",s
			range = s.split('=')[1]
			name = s.split('=')[0]
			if name.find("(") != -1:
				name = name[:name.find("(")]
				rangewidth = int(range)
				bases[name] = 1 #0 by default
			else:
				rangevals = range.split(':')
				rangewidth = int(rangevals[1]) - int(rangevals[0]) + 1
				bases[name]=rangevals[0];
			names.append(name)
			size *= rangewidth
			dims += 1
			widths[name] =rangewidth;
	return {'size': size, 'numdims': dims, 'dims': names, 'attrs':get_attrs(queryplan),'dimbases':bases,'dimwidths':widths}

#options: {'afl':True/False}
#required options: afl
#function to return the array definition from the query's SciDB query plan
# to be used with regrid to fill zeroes using the merge function
def get_arr_def(query,options):
	queryplan = query_optimizer(query,options['afl'])
	queryplan = str(queryplan)
	return queryplan[queryplan.find("<"):queryplan.find("]")+1]

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
	dimension = options['numdims']
	chunks = ""
	if ('chunkdims' in options) and (len(options['chunkdims']) > 0): #chunkdims specified
		chunkdims = options['chunkdims']
		chunks += str(chunkdims[0])
		for i in range(1,len(chunkdims)):
			chunks += ", "+str(chunkdims[i])
	elif dimension > 0: # otherwise do default chunks
		defaultchunkval = math.pow(1.0*options['qpsize']/D3_DATA_THRESHOLD,1.0/dimension) if (1.0*options['qpsize']/D3_DATA_THRESHOLD) > 1 else AGGR_CHUNK_DEFAULT
		defaultchunkval = int(math.ceil(defaultchunkval)) # round up
		chunks += str(defaultchunkval)
		for i in range(1,dimension) :
			chunks += ", "+str(defaultchunkval)
	# need to escape apostrophes or the new query will break
	attrs = options['attrs']
	final_query = re.sub("(')","\\\1",final_query)

	#make the new query an aql query so we can rename the aggregates easily
	attraggs = ""
	print >> sys.stderr, "options attrtypes: ",options['attrtypes']
	for i in range(0,len(attrs)):
		print >> sys.stderr, "attr type: ",options['attrtypes'][i]
		if (options['attrtypes'][i] == "int32") or (options['attrtypes'][i] == "int64") or (options['attrtypes'][i] == "double"): # make sure types can be aggregated
			if attraggs != "":
				attraggs += ", "
			attraggs+= "avg("+str(attrs[i])+") as avg_"+attrs[i]
	final_query = "select "+attraggs+" from ("+ final_query +") regrid "+chunks

	#if ('fillzeros' in options) and (options['fillzeroes']): # fill nulls with zeros
	#	
	#final_query = "regrid(("+final_query+"),"+chunks+","+attraggs+")" # afl
	#print >> sys.stderr, "final query:",final_query,"\nexecuting query..."
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
	else:
		probability = min([1,D3_DATA_THRESHOLD * 1.0 / options['qpsize']])
	probability = str(probability);
	# need to escape apostrophes or the new query will break
	final_query = re.sub("(')","\\\1",final_query)
	#if options['afl']:
	#	final_query = "bernoulli(("+final_query+"), "+probability+")"
	#else:
	final_query = "select * from bernoulli(("+ final_query +"), "+probability+")"
	print >> sys.stderr, "final query:",final_query,"\nexecuting query..."
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
	final_query = re.sub("(')","\\\1",final_query)
	#if options['afl']:
	#	final_query = "filter(("+final_query+"), "+options['predicate']+")"
	#else:
	final_query = "select * from ("+final_query+") where "+options['predicate']
	print >> sys.stderr, "final query:",final_query,"\nexecuting query..."
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
	reduce_type = options['reduce_type']
	qpresults = options['qpresults']
	#add common reduce function options
	reduce_options = {'afl':options['afl'],'qpsize':qpresults['size']}
	if reduce_type == RESTYPE['AGGR']:
		if 'chunkdims' in options: #user specified chunk dims
			reduce_options['chunkdims'] = options['chunkdims']
		reduce_options['numdims'] = qpresults['numdims']
		reduce_options['attrs'] = qpresults['attrs']['names']
		reduce_options['attrtypes'] = qpresults['attrs']['types']
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
	result.append(db.executeQuery(newquery,'aql'))
	result.append(verifyQuery(newquery,{'afl':False}))
	print >> sys.stderr, result[1]
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
	#print >> sys.stderr, "arr is initialized: ",str(arr)
	attrid = 0
	for i in range(attrs.size()): # find the right attrid
		if(attrs[i].getName() == attrname):
			attrid = i
			#print >> sys.stderr, "found attribute",attrname, ",id: %d" % attrid 
			break

	# get the iterator for this attrid
	it = query_result.array.getConstIterator(attrid)

	start = True
	while not it.end():
		#print >> sys.stderr, "iterating over items..."
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
			#print >> sys.stderr, "Data: %s" % item

			#insert the item
			arr = insertItem(arr,item,dimindexes)
			#update the indexes
			dimindexes = updateIndexes(dimindexes,dimchunkintervals,dimindexesbase,dimlengths)
			lastpos = chunkiter.getPosition()
			#print >> sys.stderr, lastpos[0],",",lastpos[1], ",",lastpos[2]
			chunkiter.increment_to_next()
		#print >> sys.stderr, "current state of arr: ", str(arr)
		it.increment_to_next();
	return arr

# debugging function used to print the given list of indexes
def printIndexes(dimlist):
	for i in range(len(dimlist)):
		print >> sys.stderr, "dim ", str(i), "has index %d" % dimlist[i]

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
	#print >> sys.stderr, "inserting item %d" % item
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
	#print >> sys.stderr, "arr is initialized: ",str(arr)

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
			#print >> sys.stderr, "itindex: ",itindex
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
			#print >> sys.stderr,Indexes(dimindexes)
			verifyIndexes(dimindexes,dimlengths)
			item = {} #empty dictionary for the attribute values
			for chunkiterindex in range(len(chunkiters)):
				#print >> sys.stderr, "chunkiterindex: ",chunkiterindex
				dataitem = chunkiters[chunkiterindex].getItem()
				# look up the value according to its attribute's typestring
				item[attrnames[chunkiterindex]] = scidb.getTypedValue(dataitem, attrs[chunkiterindex].getType()) # TBD: eliminate 2nd arg, make method on dataitem
				#print >> sys.stderr, "Data: %s" % item
				#chunkiters[i].increment_to_next()
			chunkiters[0].increment_to_next() # OMG THIS INCREMENTS ALL THE CHUNK ITERATOR OBJECTS
			#lastpos = chunkiter.getPosition()
			#print >> sys.stderr, lastpos[0],",",lastpos[1], ",",lastpos[2]
			#print >> sys.stderr, item
			#insert the item
			arr = insertItem(arr,item,dimindexes)
			#update the indexes
			dimindexes = updateIndexes(dimindexes,dimchunkintervals,dimindexesbase,dimlengths)
			#print >> sys.stderr, "current state of arr: ", str(arr)
		its[0].increment_to_next()
	return arr

#def mysql identify_datatype(int field_type):
#	#ints
#	if field_type == mysqldb.constants.FIELD_TYPE.INT24
#		or mysqldb.constants.FIELD_TYPE.
#
#	#doubles
#
#	#strings
#
#	#dates

def mysqlGetAllAttrArrFromQueryForJSON(options):
	step = 1000
	attrnames = []
	dimnames = []
	desc = cur.description

	arr = []
	#print >> sys.stderr, desc
	for i in range(len(desc)):
		#print >> sys.stderr, "desc[",i,"][0]:",desc[i][0]
		attrnames.append(desc[i][0]) # get attr name
	rows = cur.fetchmany(step)
	if len(rows) > 0:
		typerow = rows[0]
		while len(rows) > 0:
			#print >> sys.stderr, rows
			for i in range(len(rows)):
				dataobj = {}
				row = rows[i]
				#print >> sys.stderr, row
				for j in range(len(row)):
					#print >> sys.stderr, type(row[j]).__name__ # use python's translated types
					if type(row[j]) == decimal.Decimal:
						dataobj["attrs."+attrnames[j]] = float(row[j])
					elif type(row[j]) == datetime.datetime:
						dataobj["attrs."+attrnames[j]] = long(time.mktime(row[j].timetuple()))
					else:
						dataobj["attrs."+attrnames[j]] = row[j]
				arr.append(dataobj)
			rows = cur.fetchmany(step)

	namesobj = []
	typesobj = {}
	for attri in range(len(attrnames)):
		attrname = attrnames[attri]
		namesobj.append({'name':"attrs."+attrname,'isattr':True})
		typesobj["attrs."+attrname] = DATATYPE[desc[attri][1]]
		#print >> sys.stderr, desc[attri][1],",",DATATYPE[desc[attri][1]]
	#currently no dims
	for dimname in dimnames:
		namesobj.append({'name':'dims.'+dimname,'isattr':False})
		typesobj[ndimname] = "int32"

	#print >> sys.stderr, typesobj
	#print >> sys.stderr, 	{'data':arr, 'names': namesobj, 'types': typesobj}
	return {'data':arr, 'names': namesobj, 'types': typesobj}
	return 0	

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
	dimnames = options['dimnames']
	desc = query_result.array.getArrayDesc()
	dims = desc.getDimensions() # list of DimensionDesc objects
	attrs = desc.getAttributes() # list of AttributeDesc objects
	origarrnamelen = 0#len(desc.getName()) - 2
	print >> sys.stderr, "array name: ",desc.getName()
	print >> sys.stderr, "array name length: ",origarrnamelen

	if(dims.size() < 1 or dims.size() != len(dimnames)):
		return []

	arr = []
	its = []
	attrnames = []
	for i in range(attrs.size()): # find the right attrid
		if attrs[i].getName() != "EmptyTag":
			its.append(query_result.array.getConstIterator(i))
			attrnames.append(attrs[i].getName())

	start = True
	while not its[0].end():
		#get chunk iterators
		chunkiters = []
		#print >> sys.stderr, "start"
		for itindex in range(len(its)):
			#print >> sys.stderr, "itindex: ",itindex
			#mypos = its[itindex].getPosition()
			#print >> sys.stderr, "position:"
			#print >> sys.stderr, mypos[0],",",mypos[1]
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
			#print >> sys.stderr, "start"
			for chunkiterindex in range(len(chunkiters)):
				#print >> sys.stderr, "chunkiterindex: ",chunkiterindex
				dataitem = chunkiters[chunkiterindex].getItem()
				# look up the value according to its attribute's typestring
				#attrobj[attrnames[chunkiterindex]] = scidb.getTypedValue(dataitem, attrs[chunkiterindex].getType()) # TBD: eliminate 2nd arg, make method on dataitem
				dataobj["attrs."+attrnames[chunkiterindex]] = scidb.getTypedValue(dataitem, attrs[chunkiterindex].getType())
				#print >> sys.stderr, "Data: %s" % item
				#chunkiters[i].increment_to_next()
				#mypos = chunkiters[chunkiterindex].getPosition()
				#myposstring = "position: "
				#for myposi in range(len(mypos)):
				#	myposstring += str(mypos[myposi])+", "
				#print >> sys.stderr, myposstring
				chunkiters[chunkiterindex].increment_to_next() # OMG THIS INCREMENTS ALL THE CHUNK ITERATOR OBJECTS
			#lastpos = chunkiter.getPosition()
			#print >> sys.stderr, lastpos[0],",",lastpos[1], ",",lastpos[2]
			#print >> sys.stderr, attrobj
			#insert the item
			arr.append(dataobj)
			#arr.append({'dimensions':dimobj,'attributes':attrobj})
			#print >> sys.stderr, "current state of arr: ", str(arr)
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
	#for attri in range(len(attrnames)):
	#	attrname = attrnames[attri]
	#	namesobj.append("attrs."+attrname)
	#	typesobj["attrs."+attrname] = attrs[attri].getType()
	#for dimname in dimnames:
	#	ndimname = "dims."+dimname[:len(dimname)-origarrnamelen]
	#	namesobj.append(ndimname)
	#	typesobj[ndimname] = "int32"
	#print >> sys.stderr, typesobj
	#print >> sys.stderr, 	json.dumps({'data':arr, 'names': namesobj, 'types': typesobj})
	return {'data':arr, 'names': namesobj, 'types': typesobj}
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
	#print >> sys.stderr, "orig name length: ",origarrnamelen

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
		#print >> sys.stderr, "start"
		for itindex in range(len(its)):
			#print >> sys.stderr, "itindex: ",itindex
			#mypos = its[itindex].getPosition()
			#print >> sys.stderr, "position:"
			#print >> sys.stderr, mypos[0],",",mypos[1]
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
			#print >> sys.stderr, "start"
			for chunkiterindex in range(len(chunkiters)):
				#print >> sys.stderr, "chunkiterindex: ",chunkiterindex
				dataitem = chunkiters[chunkiterindex].getItem()
				# look up the value according to its attribute's typestring
				attrobj[attrnames[chunkiterindex]] = scidb.getTypedValue(dataitem, attrs[chunkiterindex].getType()) # TBD: eliminate 2nd arg, make method on dataitem
				dataobj["attrs."+attrnames[chunkiterindex]] = scidb.getTypedValue(dataitem, attrs[chunkiterindex].getType())
				#print >> sys.stderr, "Data: %s" % item
				#chunkiters[i].increment_to_next()
				#mypos = chunkiters[chunkiterindex].getPosition()
				#myposstring = "position: "
				#for myposi in range(len(mypos)):
				#	myposstring += str(mypos[myposi])+", "
				#print >> sys.stderr, myposstring
				chunkiters[chunkiterindex].increment_to_next() # OMG THIS INCREMENTS ALL THE CHUNK ITERATOR OBJECTS
			#lastpos = chunkiter.getPosition()
			#print >> sys.stderr, lastpos[0],",",lastpos[1], ",",lastpos[2]
			#print >> sys.stderr, attrobj
			#insert the item
			arr.append(dataobj)
			#arr.append({'dimensions':dimobj,'attributes':attrobj})
			#print >> sys.stderr, "current state of arr: ", str(arr)
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
	#print >> sys.stderr, typesobj
	#print >> sys.stderr, 	json.dumps({'data':arr, 'names': namesobj, 'types': typesobj})
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

#mysqlOpenConn()
#query = "select create_time,recent_stop_id,lat,lon from vis limit 10"
#query = "select * from earthquake limit 10"
#options={}
#mysqlExecuteQuery(query,options)
#mysqlGetAllAttrArrFromQueryForJSON(options)

#query = "select * from test3"
#query="select * from esmall"
#query = "select * from bernoulli(random_numbers_big,.01)"
#query = "scan(esmall)"
#myafl = False

#options = {'afl':myafl}
#qpresults = verifyQuery(query,options)
#print >> sys.stderr, qpresults
#options={'afl':myafl,'reduce_res':False}
#queryresult = executeQuery(query,options) # ignore reduce_type for now
#print >> sys.stderr, queryresult
#options={'dimnames':qpresults['dims']}
#queryresultarr = getAllAttrArrFromQueryForJSON(queryresult[0],options)

#options={'dimnames':qpresults['dims'],'attrnames':qpresults['attrs']['names'][0:4]}
#queryresultarr = getAttrArrFromQueryForJSON(queryresult,options)

#for i in range(len(queryresultarr['data'])):
#	print >> sys.stderr, queryresultarr['data'][i]
#	#print >> sys.stderr, "attributes: ",queryresultarr['data'][i]['attributes'],",dimensions: ",queryresultarr['data'][i]['dimensions']

#options={'dimnames':qpresults['dims']}
#queryresultarr = getMultiArrFromQueryForJSON(queryresult,options)
#print >> sys.stderr, queryresultarr

#print >> sys.stderr, qpresults['attrs']['names']
#options = {'numdims':qpresults['numdims'],'afl':myafl,'attrs':qpresults['attrs']['names'],'attrtypes':qpresults['attrs']['types'], 'qpsize':qpresults['size']}
#queryresult = daggregate(query,options)
#options={'dimnames':qpresults['dims']}
#queryresultarr = getAllAttrArrFromQueryForJSON(queryresult,options)
#print >> sys.stderr, queryresultarr

#options = {'afl':myafl,'qpsize':qpresults['size'], 'probability':.3}
#dsample(query,options)

#options = {'afl':myafl,'predicate':"lat > 0"}
#dfilter(query,options)

#mysqlCloseConn()
