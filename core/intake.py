"""Estimated intake guidance for nutrition signals beyond calories and protein."""

from __future__ import annotations

from typing import Any

from .storage import DEFAULT_USER_ID, load_recent_entries


TARGETS = {
    "sugar_g": (50, "g", "lower"),
    "cholesterol_mg": (300, "mg", "lower"),
    "fat_g": (78, "g", "lower"),
    "saturated_fat_g": (20, "g", "lower"),
    "caffeine_mg": (400, "mg", "lower"),
    "sodium_mg": (2300, "mg", "lower"),
    "fiber_g": (28, "g", "higher"),
}


def _status(value: Any, target: float, unit: str, direction: str) -> str:
    if not isinstance(value, (int, float)):
        return "No estimate yet."
    rounded = round(float(value))
    if direction == "higher":
        if value >= target:
            return f"{rounded}{unit}, on target."
        return f"{rounded}{unit}, below the rough target of {target:g}{unit}."
    if value <= target * 0.75:
        return f"{rounded}{unit}, comfortably under the rough limit."
    if value <= target:
        return f"{rounded}{unit}, close to the rough limit of {target:g}{unit}."
    return f"{rounded}{unit}, above the rough limit of {target:g}{unit}."


def generate_intake_guidance(user_id: str = DEFAULT_USER_ID) -> str:
    entries = load_recent_entries(user_id=user_id, n=1)
    if not entries:
        return "No intake guidance yet. Add a meal entry first."

    latest = entries[-1]
    foods = latest.get("estimated_foods") or []
    lines = ["Estimated Intake Guidance"]
    if foods:
        lines.append(f"Estimate basis: {', '.join(foods)}.")

    lines.extend(
        [
            f"Sugar: {_status(latest.get('sugar_g'), *TARGETS['sugar_g'])} If high, keep the next meal protein- and fiber-forward.",
            f"Cholesterol: {_status(latest.get('cholesterol_mg'), *TARGETS['cholesterol_mg'])} If high, choose leaner protein next.",
            f"Fats: {_status(latest.get('fat_g'), *TARGETS['fat_g'])} Favor fish, avocado, nuts, olive oil, and lean proteins.",
            f"Saturated fat: {_status(latest.get('saturated_fat_g'), *TARGETS['saturated_fat_g'])} If high, go lighter on cheese, butter, fried foods, and fatty cuts.",
            f"Caffeine: {_status(latest.get('caffeine_mg'), *TARGETS['caffeine_mg'])} If sleep has been weak, avoid more caffeine today.",
            f"Sodium: {_status(latest.get('sodium_mg'), *TARGETS['sodium_mg'])} If high, push water and reduce processed foods next meal.",
            f"Fiber: {_status(latest.get('fiber_g'), *TARGETS['fiber_g'])} If low, add fruit, oats, beans, lentils, potatoes, or vegetables.",
        ]
    )
    return "\n".join(lines)
