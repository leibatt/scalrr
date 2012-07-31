import scalrr_back_data as sbdata
import tile_interface as ti
import random
import threading
import math
import scidb_server_interface as sdbi

import scalrr_back_data.py with scalrr_back_data.user_history_lock

#this expert chooses up to c random tiles, from random levels
class BasicExpert:
	def __init__(self):
		self.prefetched_tiles = {}
		self.prefetch_lock = threading.Lock()

	# c = max # of tiles
	# user_id = user_id passed in the request received by scalrr_back
	def prefetch(self,c,user_id):
		global prefetched_tiles
		i = 0
        # lock you need to access user metadata, see scalrr_back_data.py
        # with sbdata.metadata_lock: 
			# total number of levels, currently the default is 2
            # levels = sbdata.backend_metadata[user_id]['levels']

        


        # keep checking to make sure we can still fetch more tiles
		while i < c and not sbdata.stop_prefetch.is_set():
            # default_diff = default difference between tiles
            # (as a multiple, so 3x or 2x for example)
			total_tiles = math.pow(sbdata.default_diff,2*level)

            # get tile index of last move
            n_minus1 = sbdata.user_history[user_id][len(sbdata.user_history[user_id])-1]
            # get tile index of 2 moves ago
            n_minus2 = sbdata.user_history[user_id][len(sbdata.user_history[user_id])-2]

            level = n_minus1[level]

            if n_minus1.x - n_minus2.x != 0:
                dir = n_minus1.x - n_minus2.x
                
                getTileByIDXY(n_minus1.x + dir, n_minus1.y    , level, user_id)
                getTileByIDXY(n_minus1.x      , n_minus1.y + 1, level, user_id)
                getTileByIDXY(n_minus1.x      , n_minus1.y - 1, level, user_id)
                getTileByIDXY(n_minus1.x - dir, n_minus1.y    , level, user_id)
                

            else: # change must have been in y direction
                dir = n_minus1.y - n_minus2.y

                getTileByIDXY(n_minus1.x    , n_minus1.y + dir, level, user_id)
                getTileByIDXY(n_minus1.x + 1, n_minus1.y      , level, user_id)
                getTileByIDXY(n_minus1.x - 1, n_minus1.y      , level, user_id)
                getTileByIDXY(n_minus1.x    , n_minus1.y - dir, level, user_id)




            # lock you need to access this expert's prefetched tiles
            with self.prefetch_lock:
				if user_id not in self.prefetched_tiles:
					self.prefetched_tiles[user_id] = {}
				if levels in self.prefetched_tiles[user_id]:
					self.prefetched_tiles[user_id][level].append(tile)
				else:
					self.prefetched_tiles[user_id][level] = [tile]
			# the next 3 lines are for debugging purposes
			print levels
			print "tile ",tile_id,": ", tile
			print "total tiles: ",total_tiles
			print "level: ",level
			i += 1
		if i < c and sbdata.stop_prefetch.is_set():
			print "direction expert stopped fetching early"
		print "direction expert done prefetching tiles"


	def find_tile(self,tile_id,level,user_id):
		tile = None
		with self.prefetch_lock:
			if user_id in self.prefetched_tiles and
                level in self.prefetched_tiles[user_id] and
                tile_id in self.prefetched_tiles[user_id][level]:
				tile = self.prefetched_tiles[user_id][level][tile_id]
		return tile

	def remove_all_tiles(self,user_id):
		with self.prefetch_lock:
			self.prefetched_tiles[user_id]= {}
