"""Plugin adapters.

Each adapter module is executed with ``python -m`` inside the plugin's own
virtual environment. At module import time adapters may only use the standard
library plus the pure-stdlib protocol helpers; heavy upstream imports must
happen lazily inside functions so structured errors can be produced when the
upstream package is missing or its API changed.
"""

from __future__ import annotations
