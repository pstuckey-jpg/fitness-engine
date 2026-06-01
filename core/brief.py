"""Daily advice brief generation."""

from __future__ import annotations

from statistics import mean
from typing import Any

from .storage import DEFAULT_USER_ID, load_entries
from .trends import compute_trends


def _numbers(entries: list[dict[str, Any]], field: str) -> list[float]:
    values: list[float] = []
    for entry in entries:
        value = entry.get(field)
        if isinstance(value, (int, float)):
            values.append(float(value))
    return values


def _trend_label(current: float | None, previous_values: list[float], unit: str) -> str:
    if current is None:
        return f"No current {unit} logged."
    if not previous_values:
        return f"Current: {current:g} {unit}. No trend yet."
    average = mean(previous_values)
    difference = current - average
    if abs(difference) < max(5, average * 0.05):
        return f"Current: {current:g} {unit}, close to recent average ({average:.0f})."
    direction = "above" if difference > 0 else "below"
    return f"Current: {current:g} {unit}, {abs(difference):.0f} {unit} {direction} recent average."


def _training_recommendation(latest: dict[str, Any], recent: list[dict[str, Any]]) -> str:
    training = latest.get("training_type")
    sleep = latest.get("sleep_hours")
    energy = latest.get("energy_level")
    recent_training = [entry.get("training_type") for entry in recent if entry.get("training_type")]
    rest_count = recent_training.count("rest")

    low_energy = isinstance(energy, int) and energy <= 4
    low_sleep = isinstance(sleep, (int, float)) and sleep < 6.5

    if training == "rest":
        return "Rest day logged. Keep movement easy and prepare for the next quality session."
    if low_energy or low_sleep:
        return "Keep training submaximal today: reduce volume, avoid grinding sets, and prioritize clean technique."
    if rest_count == 0 and len(recent_training) >= 5:
        return "You have trained several days without a logged rest day. Plan an easy day soon."
    if training:
        return f"{training.title()} logged. Progress with one focused variable: reps, load, or form quality."
    return "No training type logged. Add push, pull, legs, cardio, or rest so recommendations improve."


def _recovery_note(latest: dict[str, Any], recent: list[dict[str, Any]]) -> str:
    sleep = latest.get("sleep_hours")
    sleep_values = _numbers(recent, "sleep_hours")
    energy = latest.get("energy_level")

    if isinstance(sleep, (int, float)) and sleep < 6.5:
        return "Recovery is constrained by sleep. Aim for an earlier cutoff tonight."
    if sleep_values and mean(sleep_values) < 7:
        return "Recent sleep is running under 7 hours on average. Treat recovery as a training input."
    if isinstance(energy, int) and energy >= 8:
        return "Energy is strong. Good day for a focused session if soreness is manageable."
    return "Recovery looks workable. Keep hydration and bedtime consistent."


def _small_improvement(latest: dict[str, Any]) -> str:
    if latest.get("protein_g") is None:
        return "Log protein grams tomorrow so the brief can track muscle-supporting intake."
    if latest.get("calories") is None:
        return "Add calories tomorrow, even as an estimate, to sharpen balance feedback."
    if latest.get("sleep_hours") is None:
        return "Add sleep hours tomorrow so recovery guidance gets more precise."
    if latest.get("training_type") is None:
        return "Tag the session type tomorrow to improve training recommendations."
    return "Make one meal protein-forward earlier in the day to reduce evening catch-up."


def generate_brief(user_id: str = DEFAULT_USER_ID) -> str:
    """Generate a concise, actionable brief from the latest entry and recent trends."""
    entries = load_entries(user_id=user_id)
    if not entries:
        return "No entries yet. Add a daily entry first, then run the brief."

    latest = entries[-1]
    recent = entries[-7:]
    previous = recent[:-1]

    protein_values = _numbers(previous, "protein_g")
    calorie_values = _numbers(previous, "calories")

    protein_line = _trend_label(latest.get("protein_g"), protein_values, "g protein")
    calorie_line = _trend_label(latest.get("calories"), calorie_values, "calories")
    training_line = _training_recommendation(latest, recent)
    recovery_line = _recovery_note(latest, recent)
    improvement_line = _small_improvement(latest)
    trends = compute_trends(user_id=user_id)
    trend_context = ""
    if trends["average_sleep"] is not None:
        trend_context = (
            f"Trend context: Last 7 entries average {trends['average_sleep']}h sleep, "
            f"{trends['average_protein'] or 'unknown'}g protein, and "
            f"{trends['average_calories'] or 'unknown'} calories."
        )

    lines = [
        f"Daily Advice Brief - {latest.get('date', 'latest entry')}",
        f"Protein trend: {protein_line}",
        f"Calorie balance: {calorie_line}",
        f"Training recommendation: {training_line}",
        f"Recovery note: {recovery_line}",
    ]
    if trend_context:
        lines.append(trend_context)
    lines.append(f"Small improvement: {improvement_line}")
    return "\n".join(lines)
