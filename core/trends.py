"""Trend detection for recent fitness and nutrition entries."""

from __future__ import annotations

from collections import Counter
from statistics import mean
from typing import Any

from .storage import DEFAULT_USER_ID, load_recent_entries


def _numbers(entries: list[dict[str, Any]], field: str) -> list[float]:
    return [float(entry[field]) for entry in entries if isinstance(entry.get(field), (int, float))]


def _average(entries: list[dict[str, Any]], field: str, digits: int = 0) -> float | None:
    values = _numbers(entries, field)
    if not values:
        return None
    return round(mean(values), digits)


def _numeric_trend(entries: list[dict[str, Any]], field: str) -> str:
    values = _numbers(entries, field)
    if len(values) < 2:
        return "Not enough data yet."
    midpoint = max(1, len(values) // 2)
    early = values[:midpoint]
    late = values[midpoint:]
    if not late:
        return "Not enough data yet."
    change = mean(late) - mean(early)
    if abs(change) < 0.4:
        return "Stable."
    return "Trending up." if change > 0 else "Trending down."


def compute_trends(user_id: str = DEFAULT_USER_ID, days: int = 7) -> dict[str, Any]:
    """Compute recent trend signals while gracefully handling missing fields."""
    recent = load_recent_entries(user_id=user_id, n=days)
    training_frequency = Counter(
        entry["training_type"] for entry in recent if entry.get("training_type")
    )
    mood_frequency = Counter(entry["mood"] for entry in recent if entry.get("mood"))

    return {
        "entry_count": len(recent),
        "average_calories": _average(recent, "calories"),
        "average_protein": _average(recent, "protein_g"),
        "average_sleep": _average(recent, "sleep_hours", digits=1),
        "average_steps": _average(recent, "steps"),
        "training_frequency": dict(training_frequency),
        "energy_trend": _numeric_trend(recent, "energy_level"),
        "mood_trend": dict(mood_frequency),
    }
