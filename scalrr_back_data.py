import threading

backend_metadata = {}
metadata_lock = threading.Lock()

user_tiles = {} # for tracking the tiles this user has visited
user_tiles_lock = threading.Lock()

#id used to access the tiles: "xid,yid"
#each entry looks like: {'tile_xid':xid,'tile_yid':yid,'level':level}
user_history = {} # for recording the order in which the tiles were visited
user_history_lock = threading.Lock()

stop_prefetch = threading.Event() # for telling the experts to stop prefetching

#default number of tiles to prefetch
max_prefetched = 3

#default number of levels and difference between levels
default_diff = 3
default_levels = 2
