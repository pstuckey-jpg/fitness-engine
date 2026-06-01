"""Profile helpers for user-specific targets and preferences."""

from __future__ import annotations

from typing import Any

from .storage import DEFAULT_USER_ID, load_profile as _load_profile, save_profile as _save_profile


PROFILE_FIELDS = (
    "calorie_target",
    "protein_target",
    "goal_direction",
    "diet_preferences",
    "equipment",
    "injuries",
)


def load_profile(user_id: str = DEFAULT_USER_ID) -> dict[str, Any]:
    """Load the user's profile."""
    return _load_profile(user_id=user_id)


def save_profile(profile: dict[str, Any], user_id: str = DEFAULT_USER_ID) -> dict[str, Any]:
    """Save only the current basic profile fields plus future flexible fields."""
    cleaned = {
        key: value.strip() if isinstance(value, str) else value
        for key, value in profile.items()
        if value not in ("", None)
    }
    return _save_profile(cleaned, user_id=user_id)
