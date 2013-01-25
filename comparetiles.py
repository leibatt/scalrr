import json
import scidb_server_interface as sdbi
import tile_interface as ti
import math

DEBUG_PRINT = False

def compare_tiles(query,threshold,zoom_diff,x_label,y_label):
	db = sdbi.scidbOpenConn()
	sdbioptions = {'afl':False,'db':db}
	saved_qpresults = sdbi.verifyQuery(query,sdbioptions)
	sdbi.scidbCloseConn(db)
	if 'error' in saved_qpresults:
		print "error found, returning error:",saved_qpresults
		return saved_qpresults
	else:
		if DEBUG_PRINT: print "saved_qpresults:",saved_qpresults
	if x_label not in saved_qpresults['dims']:
		print "x_label",x_label,"not found"
		return
	if y_label not in saved_qpresults['dims']:
		print "y_label",y_label,"not found"
		return
	n = saved_qpresults['numdims']
	root_k = math.ceil(math.pow(threshold,1.0/n))
	threshold = root_k ** 2 ## adjust to make it a nice power
	tsize = saved_qpresults['size'] # get the size of the result
	levels = 1
	if tsize > threshold: # if k happens to be larger than the total results
		levels = math.ceil(math.log(1.0*tsize/threshold)/(n*math.log(zoom_diff)))+1 # need to account for zoom diff
	if DEBUG_PRINT: print "levels:",levels

	tile_metadata = sdbi.get_complete_tile_metadata(root_k,zoom_diff,saved_qpresults)
	if DEBUG_PRINT: print "tile metadata:",tile_metadata
	if DEBUG_PRINT: return
	#_id = [0,0]
	#tile = ti.getTileNoUser(_id,query,saved_qpresults,levels,threshold)
	#if 'error' in tile:
	#	print 'error found, reeturning error:',tile
	#	return tile
	for l in range(1,int(levels)):
		total_tiles_root = int(math.pow(zoom_diff,l))
		for xid in range(0,total_tiles_root):
			for yid in range(0,total_tiles_root):
				#get tile
				tile_info = {'type':'xy','tile_xid':xid,'tile_yid':yid,'x_label':x_label,'y_label':y_label}
				tile = ti.getTileNoUser(tile_info,query,saved_qpresults,l,levels,threshold)
				if 'error' in tile:
					print 'error found, reeturning error:',tile
					return tile
				if yid+1 < total_tiles_root:
					for yid2 in range(yid+1,total_tiles_root):
						#if DEBUG_PRINT: print "comparing tile (lvl:",l,", x:",xid,", y:",yid,") and tile (lvl:",l,", x:",xid,", y:",yid2,")"
						#check rest of col: xid,yid2
						tile_info['tile_xid']=xid
						tile_info['tile_yid']=yid2
						#get other tile
						newtile = ti.getTileNoUser(tile_info,query,saved_qpresults,l,levels,threshold)
						if 'error' in newtile:
							print 'error found, reeturning error:',newtile
							return newtile
						#compare tiles
				if xid+1 < total_tiles_root:
					for xid2 in range(xid+1,total_tiles_root):
						for yid2 in range(0,total_tiles_root):
							#if DEBUG_PRINT: print "comparing tile (lvl:",l,", x:",xid,", y:",yid,") and tile (lvl:",l,", x:",xid2,", y:",yid2,")"
							#check all tiles w/ > xid: xid2,yid2
							tile_info['tile_xid']=xid2
							tile_info['tile_yid']=yid2
							#get other tile
							newtile = ti.getTileNoUser(tile_info,query,saved_qpresults,l,levels,threshold)
							if 'error' in newtile:
								print 'error found, reeturning error:',newtile
								return newtile
							#compare tiles

def compare(tile1,tile2):
	x = 1


compare_tiles("select * from test3",100,zoom_diff=2,x_label="dims.xtest3",y_label="dims.ytest3")
