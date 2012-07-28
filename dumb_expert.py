import scalrr_back_data as sbdata
import tile_interface as ti
import random
import threading
import math
import scidb_server_interface as sdbi

#this expert chooses up to c random tiles, from random levels
class BasicExpert:
	def __init__(self):
		self.prefetched_tiles = {}
		self.prefetch_lock = threading.Lock()

	#c = max # of tiles
	#user_id = user_id passed in the request received by scalrr_back
	def prefetch(self,c,user_id):
		global prefetched_tiles
		i = 0
		with sbdata.metadata_lock: # lock you need to access user metadata
			levels = sbdata.backend_metadata[user_id]['levels'] # total number of levels, currently the default is 2
			total_tiles = math.pow(sbdata.default_diff,levels) # default_diff = default difference between tiles (as a multiple, so 3x or 2x for example)
		shuffled_tiles = range(int(total_tiles))
		random.shuffle(shuffled_tiles)
		while i < c and i < total_tiles and not sbdata.stop_prefetch.is_set(): # keep checking to make sure we can still fetch more tiles
			level = random.randrange(0,levels)
			tile = ti.getTileByID(shuffled_tiles[i],level,user_id)
			with self.prefetch_lock: # lock you need to access this expert's prefetched tiles
				if user_id not in self.prefetched_tiles:
					self.prefetched_tiles[user_id] = {}
				if levels in self.prefetched_tiles[user_id]:
					self.prefetched_tiles[user_id][level].append(tile)
				else:
					self.prefetched_tiles[user_id][level] = [tile]
			# the next 3 lines are for debugging purposes
			print "tile",i,":", tile
			i += 1
		if i < c and i < total_tiles and sbdata.stop_prefetch.is_set():
			print "dumb expert stopped fetching early"
		print "dumb expert done prefetching tiles"


	def find_tile(self,tile_id,level,user_id):
		tile = None
		with self.prefetch_lock:
			if user_id in self.prefetched_tiles and level in self.prefetched_tiles[user_id] and tile_id in self.prefetched_tiles[user_id][level]:
				tile = self.prefetched_tiles[user_id][level][tile_id]
		return tile

	def remove_all_tiles(self,user_id):
		with self.prefetch_lock:
			self.prefetched_tiles[user_id]= {}
