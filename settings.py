"""Settings from flow_manager NApp."""
# Pooling frequency
STATS_INTERVAL = 30
FLOWS_DICT_MAX_SIZE = 10000
# Time (in seconds) to wait retrieve box from storehouse
BOX_RESTORE_TIMER = 0.1
# CONSISTENCY_INTERVAL defines the strategy and interval
# to run the consistency check
#  CONSISTENCY_INTERVAL = 0 --> run based on the flow_stats.received event
#  CONSISTENCY_INTERVAL < 0 --> disables consistency check
#  CONSISTENCY_INTERVAL > 0 --> run periodically based on the interval
CONSISTENCY_INTERVAL = 0

# List of flows ignored by the consistency check
# To filter by a cookie or `table_id` use [value]
# To filter by a cookie or `table_id` range [(value1, value2)]
CONSISTENCY_COOKIE_IGNORED_RANGE = []
CONSISTENCY_TABLE_ID_IGNORED_RANGE = []
