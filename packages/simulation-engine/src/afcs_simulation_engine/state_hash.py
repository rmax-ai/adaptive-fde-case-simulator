from __future__ import annotations

import hashlib
import json
from typing import Any


def compute_state_hash(state: dict[str, Any]) -> str:
    """Return a deterministic SHA-256 hex digest of a canonical state dict.

    Uses ``json.dumps`` with ``sort_keys=True`` and no whitespace so identical
    states always hash to the same value regardless of Python dict key ordering.
    """
    canonical = json.dumps(state, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
