#!/usr/bin/env python3
"""Create/update the current application schema on the configured database."""
from __future__ import annotations

import database
import whop_storage

database.init_db()
whop_storage.init_phase2_db()
print("Neural Gold schema initialised.")
