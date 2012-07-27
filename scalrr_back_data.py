import threading

backend_metadata = {}
metadata_lock = threading.Lock()

default_diff = 3
default_levels = 2
