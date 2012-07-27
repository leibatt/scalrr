import scalrr_back_data as sbdata
import tile_interface as ti
import random
import threading
import math
import scidb_server_interface as sdbi

prefetched_tiles = {}
prefetch_lock = threading.Lock()

def prefetch(c,user_id):
	global prefetched_tiles
	i = 0
	with sbdata.metadata_lock: # lock you need to access user metadata
		levels = sbdata.backend_metadata[user_id]['levels'] # total number of levels
		total_tiles = math.pow(sbdata.default_diff,levels)
	shuffled_tiles = range(int(total_tiles))
	random.shuffle(shuffled_tiles)
	while i < c and i < total_tiles and not sbdata.stop_prefetch.is_set():
		tile = ti.getTileByID(shuffled_tiles[i],levels,user_id)
		with prefetch_lock: # lock you need to access this expert's prefetched tiles
			if user_id not in prefetched_tiles:
				prefetched_tiles[user_id] = {}
			if levels in prefetched_tiles[user_id]:
				prefetched_tiles[user_id][levels].append(tile[0])
			else:
				prefetched_tiles[user_id][levels] = [tile[0]]
		sdbioptions={'dimnames':sbdata.backend_metadata[user_id]['saved_qpresults']['dims']}
		tiledata = sdbi.getAllAttrArrFromQueryForJSON(tile[0],sdbioptions)
		print "tile",i,":", tiledata
		i += 1
	print "dumb expert done prefetching tiles"
