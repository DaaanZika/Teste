"""Filename/path safety helpers used before anything touches disk."""
from __future__ import annotations

import re
import unicodedata
import uuid
from pathlib import Path

_SAFE_CHARS_RE = re.compile(r"[^A-Za-z0-9._-]+")


def sanitize_filename(filename: str) -> str:
    """Strip any path component and normalize to a safe, storable name.

    This is defense against path traversal (`../../etc/passwd`) and against
    exotic characters that could confuse a filesystem or a later shell call.
    """
    name = Path(filename).name  # drop any directory components
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    name = _SAFE_CHARS_RE.sub("_", name).strip("._") or "arquivo"
    return name[:200]


def unique_storage_name(original_filename: str) -> str:
    """A collision-proof name to use on disk, keeping the original extension."""
    safe = sanitize_filename(original_filename)
    suffix = Path(safe).suffix.lower()
    return f"{uuid.uuid4().hex}{suffix}"


def resolve_within(base_dir: Path, relative_path: str) -> Path:
    """Resolve `relative_path` under `base_dir`, raising if it escapes it."""
    candidate = (base_dir / relative_path).resolve()
    base_resolved = base_dir.resolve()
    if base_resolved not in candidate.parents and candidate != base_resolved:
        raise ValueError(f"Path escapes storage root: {relative_path}")
    return candidate
