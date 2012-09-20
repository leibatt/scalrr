import scalrr_back_data as sbdata
import tile_interface as ti
import random
import threading
import math
import scidb_server_interface as sdbi
import dumb_expert as basicexpert

import scalrr_back_data.py with scalrr_back_data.user_history_lock

#this expert chooses up to c random tiles, from random levels
class UserDirectionExpert(basicexpert.BasicExpert):
	def __init__(self):
		super(UserDirectionExpert,self).__init__()

	# c = max # of tiles
	# user_id = user_id passed in the request received by scalrr_back
	def prefetch(self,c,user_id):
		global prefetched_tiles

		#each entry looks like: {'tile_xid':xid,'tile_yid':yid,'level':level,'timestamp':timestamp}
		with user_history.lock():
			last_tile_index = len(sbdata.user_history['user_id'])-1
			# get tile index of last move
			n_minus1_entry = sbdata.user_history[user_id][last_tile_index]
			# get tile index of 2 moves ago
			n_minus2_entry = sbdata.user_history[user_id][last_tile_index-1]

		level = n_minus1['level']
		n_minus1.x = n_minus1_entry['tile_xid']
		n_minus1.y = n_minus1_entry['tile_yid']
		n_minus1.t = n_minus1_entry['timestamp']

		n_minus2.x = n_minus2_entry['tile_xid']
		n_minus2.y = n_minus2_entry['tile_yid']
		n_minus2.t = n_minus2_entry['timestamp']

		# default_diff = default difference between tiles
		# (as a multiple, so 3x or 2x for example)
		total_tiles = math.pow(sbdata.default_diff,level) # total tiles along x axis, or along y axis

		xdir = n_minus1.x - n_minus2.x
		ydir = n_minus1.y - n_minus2.y
		in_xdir = xdir != 0

        	# keep checking to make sure we can still fetch more tiles
		i = 0
		while i < c and not sbdata.stop_prefetch.is_set():
			tile = None
			if in_xdir:
				if i == 0:
					tile = getTileByIDXY(n_minus1.x + xdir, n_minus1.y    , level, user_id)
				elif i == 1:
					tile = getTileByIDXY(n_minus1.x       , n_minus1.y + 1, level, user_id)
				elif i == 2:
					tile = getTileByIDXY(n_minus1.x       , n_minus1.y - 1, level, user_id)
				elif i == 3:
					tile = getTileByIDXY(n_minus1.x - xdir, n_minus1.y    , level, user_id)
				else break
			else: # change must have been in y direction
				if i == 0:
					tile = getTileByIDXY(n_minus1.x    , n_minus1.y + ydir, level, user_id)
				elif i == 1:				
					tile = getTileByIDXY(n_minus1.x + 1, n_minus1.y      , level, user_id)
				elif i == 2:				
					tile = getTileByIDXY(n_minus1.x - 1, n_minus1.y      , level, user_id)
				elif i == 3:				
					tile = getTileByIDXY(n_minus1.x    , n_minus1.y - ydir, level, user_id)
				else break

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

	def __get_correct_indices(x,y,total_tiles):
		diffx = total_tiles - 1 - x
		diffy = total_tiles - 1 - y
		if diffx < 0: # if x is larger than max index, wrap around for now
			diffx = -diffx
		if diffy < 0: # if y is larger than max index, wrap around for now
			diffy = -diffy
		result.x
