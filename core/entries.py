"""Entry creation workflow."""

from __future__ import annotations

from typing import Any

from .parser import parse_entry
from .storage import DEFAULT_USER_ID, append_entry


def add_entry(raw_text: str, user_id: str = DEFAULT_USER_ID) -> dict[str, Any]:
    """Parse and store one free-form daily entry."""
    entry = parse_entry(raw_text)
    return append_entry(entry, user_id=user_id)
