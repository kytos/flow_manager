"""Tests from flow_manager napp."""

import sys
import os
from pathlib import Path

if 'VIRTUAL_ENV' in os.environ:
    BASE_ENV = Path(os.environ['VIRTUAL_ENV'])
else:
    BASE_ENV = Path('/')

NAPPS_PATH = BASE_ENV / '/var/lib/kytos/'

sys.path.insert(0, str(NAPPS_PATH))


