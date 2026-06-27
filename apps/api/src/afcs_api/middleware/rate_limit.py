"""Rate limiting configuration for the AFCS API.

Uses slowapi to provide per-route and global rate limits.
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

# Shared limiter instance — use `@limiter.limit(...)` on individual routes
# for custom limits, or the default below applies globally.
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
