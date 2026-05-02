from __future__ import annotations

import hashlib
import uuid


def _validate_prefix(prefix: str) -> str:
    if not prefix:
        raise ValueError("prefix must be non-empty")
    return prefix


def create_run_id(prefix: str = "run") -> str:
    """Create a random run ID using a UUID4 suffix."""
    normalized_prefix = _validate_prefix(prefix)
    return f"{normalized_prefix}-{uuid.uuid4().hex}"


def create_deterministic_run_id(seed: str, prefix: str = "run") -> str:
    """Create a deterministic run ID stable for the same seed and prefix."""
    normalized_prefix = _validate_prefix(prefix)
    digest = hashlib.sha256(f"{normalized_prefix}:{seed}".encode("utf-8")).hexdigest()
    return f"{normalized_prefix}-{digest[:16]}"


def validate_run_id(run_id: str) -> str:
    """Validate and return a run ID."""
    if not run_id:
        raise ValueError("run_id must be non-empty")
    return run_id
