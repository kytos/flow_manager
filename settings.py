"""Settings from flow_manager NApp."""
# Pooling frequency
STATS_INTERVAL = 30
FLOWS_DICT_MAX_SIZE = 10000
# Time (in seconds) to wait retrieve box from storehouse
BOX_RESTORE_TIMER = 0.1
CONSISTENCY_INTERVAL = 60

# List of exceptions in the consistency mechanism
# [begin, end]
CONSISTENCY_COOKIE_EXCEPTION_RANGE = []
CONSISTENCY_TABLE_ID_EXCEPTION_RANGE = []
