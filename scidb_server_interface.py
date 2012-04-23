import sys
sys.path.append('/opt/scidb/11.12/lib')
import scidbapi as scidb
import string, re
import simplejson as json

LOGICAL_PHYSICAL = "explain_physical"
RESTYPE = {'AGGR': 'aggregate', 'SAMPLE': 'sample', 'BSAMPLE': 'biased_sample'}
SIZE_THRESHOLD = 50
db = 0

def scidbOpenConn():
	global db
	db = scidb.connect("localhost",1239)

def scidbCloseConn():
	global db
	if db != 0:
		db.disconnect()
		db = 0

#function to verify query query result size
def verifyQuery(query,afl=False):
	queryplan = query_optimizer(query,afl)
	return check_query_plan(queryplan) #returns a dictionary

#function to do the resolution reduction when running queries
# results from check_query_plan: [size,dims,names]
def executeQuery(query,qpresults={},afl=False,reduce_res=False,reduce_type='',reduce_val=1):
	final_query = query
	if(reduce_res):
		#assume aggregation for now
		dimension = qpresults['dims']
		chunks = ""+user_input
		while(dimension > 1):
			chunks = chunks+","+reduce_val
			dimension -= 1
		if afl:
			# need to escape apostrophes or the new query will break
			#final_query = re.sub("(\\')","\\\\\\1",final.query)
			final_query = re.sub("(')","\\\1",final_query)
			#print "substitution to escape apostrophes:",final_query
			final_query = "regrid(("+query+"),"+chunks+",avg("+get_attrs(queryplan)[0][0]+"))"
		else:
			final_query = "select regrid(x,"+chunks+",avg("+get_attrs(queryplan)[0][0]+")) from ("+query+") as x"
	else:
		print "running original query."
	print "final query:",final_query,"\nexecuting query..."
	result = []
	if afl:
		result = db.executeQuery(final_query,'afl')
	else:
		result = db.executeQuery(final_query,'aql')
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
	print "queryplan query: "
	print queryplan_query
	optimizer_answer = db.executeQuery(queryplan_query,'afl')
	#print optimizer_answer
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
	#print dim_array
	dims = 0
	size = 1
	names = [];
	for i, s in enumerate(dim_array):
		if (i % 3) == 0:
			# split on equals, get the range, split on ':'
			#print "s:",s
			range = s.split('=')[1]
			names.append(s.split('=')[0])
			rangevals = range.split(':')
			rangewidth = int(rangevals[1]) - int(rangevals[0]) + 1
			size *= rangewidth
			dims += 1
	return {'size': size, 'dims': dims, 'names': names}

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
	return [names,types]

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
	#print "arr is initialized: ",str(arr)
	attrid = 0
	for i in range(attrs.size()): # find the right attrid
		if(attrs[i].getName() == attrname):
			attrid = i
			#print "found attribute",attrname, ",id: %d" % attrid 
			break

	# get the iterator for this attrid
	it = query_result.array.getConstIterator(attrid)

	start = True
	while not it.end():
		#print "iterating over items..."
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
			#print "Data: %s" % item

			#insert the item
			arr = insertItem(arr,item,dimindexes)
			#update the indexes
			dimindexes = updateIndexes(dimindexes,dimchunkintervals,dimindexesbase,dimlengths)
			lastpos = chunkiter.getPosition()
			#print lastpos[0],",",lastpos[1], ",",lastpos[2]
			chunkiter.increment_to_next()
		#print "current state of arr: ", str(arr)
		it.increment_to_next();
	return arr

# debugging function used to print the given list of indexes
def printIndexes(dimlist):
	for i in range(len(dimlist)):
		print "dim ", str(i), "has index %d" % dimlist[i]

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
	#print "inserting item %d" % item
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
	#print "arr is initialized: ",str(arr)

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
			#print "itindex: ",itindex
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
				#print "chunkiterindex: ",chunkiterindex
				dataitem = chunkiters[chunkiterindex].getItem()
				# look up the value according to its attribute's typestring
				item[attrnames[chunkiterindex]] = scidb.getTypedValue(dataitem, attrs[chunkiterindex].getType()) # TBD: eliminate 2nd arg, make method on dataitem
				#print "Data: %s" % item
				#chunkiters[i].increment_to_next()
			chunkiters[0].increment_to_next() # OMG THIS INCREMENTS ALL THE CHUNK ITERATOR OBJECTS
			#lastpos = chunkiter.getPosition()
			#print lastpos[0],",",lastpos[1], ",",lastpos[2]
			#print item
			#insert the item
			arr = insertItem(arr,item,dimindexes)
			#update the indexes
			dimindexes = updateIndexes(dimindexes,dimchunkintervals,dimindexesbase,dimlengths)
			#print "current state of arr: ", str(arr)
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
def getAllAttrArrFromQueryForJSON(query_result,dimnames):
	desc = query_result.array.getArrayDesc()
	dims = desc.getDimensions() # list of DimensionDesc objects
	attrs = desc.getAttributes() # list of AttributeDesc objects
	origarrnamelen = len(desc.getName()) - 2
	#print "orig name length: ",origarrnamelen

	if(dims.size() < 1 or dims.size() != len(dimnames)):
		return []

	arr = []
	its = []
	attrnames = []
	for i in range(attrs.size()): # find the right attrid
		its.append(query_result.array.getConstIterator(i))
		attrnames.append(attrs[i].getName())

	start = True
	while not its[0].end():
		#get chunk iterators
		chunkiters = []
		#print "start"
		for itindex in range(len(its)):
			#print "itindex: ",itindex
			#mypos = its[itindex].getPosition()
			#print "position:"
			#print mypos[0],",",mypos[1]
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
			#print "start"
			for chunkiterindex in range(len(chunkiters)):
				#print "chunkiterindex: ",chunkiterindex
				dataitem = chunkiters[chunkiterindex].getItem()
				# look up the value according to its attribute's typestring
				attrobj[attrnames[chunkiterindex]] = scidb.getTypedValue(dataitem, attrs[chunkiterindex].getType()) # TBD: eliminate 2nd arg, make method on dataitem
				dataobj["attrs."+attrnames[chunkiterindex]] = scidb.getTypedValue(dataitem, attrs[chunkiterindex].getType())
				#print "Data: %s" % item
				#chunkiters[i].increment_to_next()
				#mypos = chunkiters[chunkiterindex].getPosition()
				#myposstring = "position: "
				#for myposi in range(len(mypos)):
				#	myposstring += str(mypos[myposi])+", "
				#print myposstring
				chunkiters[chunkiterindex].increment_to_next() # OMG THIS INCREMENTS ALL THE CHUNK ITERATOR OBJECTS
			#lastpos = chunkiter.getPosition()
			#print lastpos[0],",",lastpos[1], ",",lastpos[2]
			#print attrobj
			#insert the item
			arr.append(dataobj)
			#arr.append({'dimensions':dimobj,'attributes':attrobj})
			#print "current state of arr: ", str(arr)
		#its[1].increment_to_next()
		for itindex in range(len(its)):		
			its[itindex].increment_to_next()
	namesobj = []
	typesobj = {}
	for attri in range(len(attrnames)):
		attrname = attrnames[attri]
		namesobj.append("attrs."+attrname)
		typesobj["attrs."+attrname] = attrs[attri].getType()
	for dimname in dimnames:
		ndimname = "dims."+dimname[:len(dimname)-origarrnamelen]
		namesobj.append(ndimname)
		typesobj[ndimname] = "int32"
	#print typesobj
	#print 	json.dumps({'data':arr, 'names': namesobj, 'types': typesobj})
	return {'data':arr, 'names': namesobj, 'types': typesobj}
	#return {'data': arr, 'names': {'dimnames': dimnames, 'attrnames': attrnames}}
	

#db = scidb.connect("localhost", 1239)
#query = "scan(test1)"
#result = reduce_res(db,query,True,1)
#newarr = getOneAttrArrFromQuery(result[0],"a")
#newarr = getAllAttrArrFromQuery(result[0])
#newarr = getAllAttrArrFromQueryForJSON(result[0],result[1])
#print "new array: ", str(newarr)
#db.disconnect()


print "start"
scidbOpenConn()
query="select a,x,y from test0"
qpresults = verifyQuery(query,False)
queryresult = executeQuery(query,qpresults,False,False,RESTYPE['AGGR'],10) # ignore reduce_type for now
queryresultarr = getAllAttrArrFromQueryForJSON(queryresult,qpresults['names'])
scidbCloseConn()
for i in range(len(queryresultarr['data'])):
	print queryresultarr['data'][i]
	#print "attributes: ",queryresultarr['data'][i]['attributes'],",dimensions: ",queryresultarr['data'][i]['dimensions']
