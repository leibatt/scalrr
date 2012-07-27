import scalrr_back_data as sbdata
import tile_interface as ti
import random

prefetched_tiles = {}
prefetch_lock = threading.Lock()

def dumbExpert(c,user_id):
	global prefetched_tiles
	i = 0
	with sbdata.metadata_lock: # lock you need to access user metadata
		levels = sbdata.backend_metadata[user_id]['levels'] # total number of levels
		total_tiles = math.pow(sbdata.default_diff,)
	shuffled_tiles = range(total_tiles)
	random.shuffle(shuffled_tiles)
	while i < c and !sbdata.stop_prefetch.is_set():
		tile = ti.getTileByID(shuffled_tiles[i],user_id)
		with prefetch_lock: # lock you need to access this expert's prefetched tiles
			if levels in prefetched_tiles[user_id]:
				prefetched_tiles[user_id][levels].append(tile)
			else:
				prefetched_tiles[user_id][levels] = [tile]
		i++
	print "dumb expert done prefetching tiles"
