import threading

backend_metadata = {}
metadata_lock = threading.Lock()

stop_prefetch = threading.Event()

default_diff = 3
default_levels = 2
