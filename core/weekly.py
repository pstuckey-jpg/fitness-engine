"""Weekly summary generation."""

from __future__ import annotations

from typing import Any

from .storage import DEFAULT_USER_ID, load_recent_entries
from .trends import compute_trends


def _day_score(entry: dict[str, Any]) -> int:
    score = 0
    if isinstance(entry.get("protein_g"), (int, float)):
        score += 22
    if isinstance(entry.get("calories"), (int, float)):
        score += 18
    if isinstance(entry.get("sleep_hours"), (int, float)):
        score += min(22, int(float(entry["sleep_hours"]) / 8 * 22))
    if entry.get("training_type"):
        score += 18
    if isinstance(entry.get("energy_level"), (int, float)):
        score += min(15, int(float(entry["energy_level"]) * 1.5))
    if isinstance(entry.get("stress_level"), (int, float)):
        score -= max(0, int(float(entry["stress_level"]) - 6))
    if isinstance(entry.get("soreness_level"), (int, float)):
        score -= max(0, int(float(entry["soreness_level"]) - 7))
    return max(0, min(100, score))


def _consistency_score(entries: list[dict[str, Any]]) -> int:
    if not entries:
        return 0
    return round(sum(_day_score(entry) for entry in entries) / len(entries))


def _format_frequency(frequency: dict[str, int]) -> str:
    if not frequency:
        return "Not enough training data yet."
    return ", ".join(f"{name}: {count}" for name, count in sorted(frequency.items()))


def _next_focus(trends: dict[str, Any]) -> str:
    if trends["entry_count"] < 3:
        return "Build the logging habit first: capture meals, sleep, training, and energy for at least 3 days."
    if trends["average_protein"] is None:
        return "Log protein or protein-rich foods so the assistant can judge muscle-supporting intake."
    if trends["average_sleep"] is not None and trends["average_sleep"] < 7:
        return "Protect sleep next week. Recovery is the highest-leverage improvement."
    if not trends["training_frequency"]:
        return "Log training type each day so workload and recovery become visible."
    return "Keep the structure steady and improve one measurable detail: protein timing, sleep cutoff, or one lift progression."


def generate_weekly_summary(user_id: str = DEFAULT_USER_ID) -> str:
    """Generate a concise weekly summary from the latest seven entries."""
    entries = load_recent_entries(user_id=user_id, n=7)
    if not entries:
        return "No weekly data yet. Add entries first, then generate a weekly summary."

    scored = [(entry, _day_score(entry)) for entry in entries]
    best_entry, _ = max(scored, key=lambda item: item[1])
    hardest_entry, _ = min(scored, key=lambda item: item[1])
    trends = compute_trends(user_id=user_id)

    return "\n".join(
        [
            "Weekly Summary",
            f"Best day: {best_entry.get('date', 'Unknown date')} had the strongest overall alignment.",
            f"Hardest day: {hardest_entry.get('date', 'Unknown date')} needs the closest review.",
            f"Consistency score: {_consistency_score(entries)}/100.",
            f"Protein trend: {trends['average_protein'] or 'No average yet'}g average.",
            f"Calorie trend: {trends['average_calories'] or 'No average yet'} calories average.",
            f"Sleep trend: {trends['average_sleep'] or 'No average yet'} hours average.",
            f"Training frequency: {_format_frequency(trends['training_frequency'])}.",
            f"One focus for next week: {_next_focus(trends)}",
        ]
    )
