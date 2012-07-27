import scalrr_back_data as sbdata
import tile_interface as ti
import random
import threading
import math
import scidb_server_interface as sdbi

prefetched_tiles = {}
prefetch_lock = threading.Lock()

#c = max # of tiles
#user_id = user_id passed in the request received by scalrr_back
def prefetch(c,user_id):
	global prefetched_tiles
	i = 0
	with sbdata.metadata_lock: # lock you need to access user metadata
		levels = sbdata.backend_metadata[user_id]['levels'] # total number of levels, currently the default is 2
		total_tiles = math.pow(sbdata.default_diff,levels) # default_diff = default difference between tiles (as a multiple, so 3x or 2x for example)
	shuffled_tiles = range(int(total_tiles))
	random.shuffle(shuffled_tiles)
	while i < c and i < total_tiles and not sbdata.stop_prefetch.is_set(): # keep checking to make sure we can still fetch more tiles
		tile = ti.getTileByID(shuffled_tiles[i],levels,user_id)
		with prefetch_lock: # lock you need to access this expert's prefetched tiles
			if user_id not in prefetched_tiles:
				prefetched_tiles[user_id] = {}
			if levels in prefetched_tiles[user_id]:
				prefetched_tiles[user_id][levels].append(tile)
			else:
				prefetched_tiles[user_id][levels] = [tile]
		# the next 3 lines are for debugging purposes
		sdbioptions={'dimnames':sbdata.backend_metadata[user_id]['saved_qpresults']['dims']}
		tiledata = sdbi.getAllAttrArrFromQueryForJSON(tile[0],sdbioptions)
		print "tile",i,":", tiledata
		i += 1
	print "dumb expert done prefetching tiles"
