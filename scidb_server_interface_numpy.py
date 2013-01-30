import scidbapi as scidb
import numpy as np
import numpy.ma as ma
from datetime import datetime

DEBUG_PRINT = True

#options: {queryresult from sdbi, attrnames}
#required options: query_result
#attrnames is a list of string identifiers used to fetch only specific attributes
# if attrnames not passed, return all attributes
def getAllAttrArrFromQueryForNP(query_result,attrnames=None,usenan=False):
	#if DEBUG_PRINT: print  "parsing query result and building json dump",datetime.now()
	desc = query_result.array.getArrayDesc()
	dims = desc.getDimensions() # list of DimensionDesc objects
	attrs = desc.getAttributes() # list of AttributeDesc objects

	if(dims.size() < 1):
		return None

	dimtuple = []
	for i,dim in enumerate(dims):
		dimtuple.append(dim.getCurrLength())
	dimtuple = tuple(dimtuple)

	arrs = []
	itemsets = []
	its = []
	getattrnames = False
	if attrnames is None:
		attrnames = []
		getattrnames = True
	minobj = {}
	maxobj = {}
	for i in range(attrs.size()): # find the right attrid, "EmptyTag" should always be at the end
		if attrs[i].getName() != "EmptyTag":
			arrs.append(np.zeros(dimtuple)) # new array for each attribute
			itemsets.append(arrs[i].itemset) #used to insert items)
			if usenan:
				arrs[i].fill(np.nan) # fill with nulls if necessary
			its.append(query_result.array.getConstIterator(i))
			if getattrnames:
				attrnames.append(attrs[i].getName())
			#currtype = attrs[i].getType()

	while not its[0].end():
		#get chunk iterators
		chunkiters = []
		for itindex in range(len(its)):
			#if DEBUG_PRINT: print  "itindex: ",itindex
			#mypos = its[itindex].getPosition()
			#if DEBUG_PRINT: print  "position:"
			#if DEBUG_PRINT: print  mypos[0],",",mypos[1]
			currentchunk =its[itindex].getChunk()
			chunkiter = currentchunk.getConstIterator((scidb.swig.ConstChunkIterator.IGNORE_EMPTY_CELLS |
		                                       scidb.swig.ConstChunkIterator.IGNORE_OVERLAPS))
			chunkiters.append(chunkiter)

		while not chunkiters[0].end():
			currpos = chunkiters[0].getPosition()
			cpl = len(currpos)
			currpostuple = [0]*cpl
			for i in range(cpl):
				currpostuple[i] = currpos[i]
			currpostuple = tuple(currpostuple)
			#testcurrpos = tuple(currpos) #this is bad! causes memory leaks...

			for chunkiterindex in range(len(chunkiters)):
				#if DEBUG_PRINT: print  "chunkiterindex: ",chunkiterindex
				dataitem = chunkiters[chunkiterindex].getItem()
				# look up the value according to its attribute's typestring
				currtype = attrs[chunkiterindex].getType()
				dataitem_val = scidb.getTypedValue(dataitem, currtype)
				itemsets[chunkiterindex](currpostuple,dataitem_val) # insert into every numpy array
				
				chunkiters[chunkiterindex].increment_to_next() # OMG THIS INCREMENTS ALL THE CHUNK ITERATOR OBJECTS
			
		for itindex in range(len(its)):		
			its[itindex].increment_to_next()

	#if DEBUG_PRINT: print  "done parsing results, returning dump-ready version",datetime.now()
	#if DEBUG_PRINT: print arrs
	if DEBUG_PRINT: print arrs[0].shape
	return {'data':arrs,'attrnames':attrnames,'stats':get_stats(arrs)}


def get_stats(arrs,interpolatenans=False):
	arrslen = len(arrs)
	if DEBUG_PRINT: print "array nums:", arrslen
	stats = [0] * arrslen
	for i,arr in enumerate(arrs):
		if(len(arrs[i].shape) > 2):
			stats[i] = None
		else:
			maskedarr = ma.masked_array(arrs[i],fill_value=0)
			if interpolatenans:
				arr = interpolate_nans(arr)
			else:
				arr = maskedarr.filled() # check and see what happens when you interpolate
			stats[i] = {'avgs':[np.mean(arr,axis=0),np.mean(arr,axis=1)],
					'stdevs':[np.std(arr,axis=0),np.std(arr,axis=1)],
					'cov':[0,0]}

			xlen = arr.shape[0]
			ylen = arr.shape[1]
			# get specific covariance values along x axis
			covx = np.zeros(xlen)
			covar = np.cov(arr) # get the covariance values by row for dim 1
			for x in range(1,xlen):
				covx[x-1] = covar[x][x-1]
			stats[i]['cov'][0] = covx
			# get specific covariance values along y axis
			covy = np.zeros(ylen)
			covar = np.cov(arr,rowvar=0)  # get the covariance values by col for dim 2
			for y in range(1,ylen):
				covy[y-1] = covar[y][y-1]
			stats[i]['cov'][1] = covy
	return stats

#replace the holes by interpolating
#may want to also test interpolation on transpose
def interpolate_nans(arr):
	mask = np.isnan(arr)
	arr[mask] = np.interp(np.flatnonzero(mask), np.flatnonzero(~mask), arr[~mask])
	return arr

def arrs_to_json(arrs):
	for i,arr in enumerate(arrs):
		temp = arr.tolist()
		arrs[i] = temp
	return arrs

def stats_to_json(stats):
	for i,stat in enumerate(stats):
		avgs = stat['avgs']
		stdevs = stat['stdevs']
		cov = stat['cov']
		for j in range(len(avgs)):
			temp = avgs[j].tolist()
			avgs[j] = temp
		for j in range(len(stdevs)):
			temp = stdevs[j].tolist()
			stdevs[j] = temp
		for j in range(len(cov)):
			temp = cov[j].tolist()
			cov[j] = temp
		stat['avgs'] = avgs
		stat['stdevs'] = stdevs
		stat['cov'] = cov
		stats[i] = stat
	return stats
