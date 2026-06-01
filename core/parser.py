"""Lightweight parsing for free-form daily fitness and nutrition entries."""

from __future__ import annotations

import re
from datetime import date
from typing import Any


TRAINING_TYPES = (
    "push",
    "pull",
    "legs",
    "cardio",
    "rest",
    "upper",
    "lower",
    "full body",
    "full-body",
    "strength",
    "conditioning",
    "mobility",
)


def _first_number(patterns: list[str], text: str, *, cast: type = int) -> Any | None:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1).replace(",", "")
            return cast(float(value)) if cast is int else cast(value)
    return None


def _extract_date(text: str) -> str:
    iso_match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
    if iso_match:
        return iso_match.group(1)
    return date.today().isoformat()


def _extract_training_type(text: str) -> str | None:
    lowered = text.lower()
    for training_type in TRAINING_TYPES:
        if re.search(rf"\b{re.escape(training_type)}\b", lowered):
            return "full body" if training_type == "full-body" else training_type
    return None


def _extract_energy_level(text: str) -> int | str | None:
    numeric = _first_number(
        [
            r"\benergy(?:\s+level)?\s*(?:was|is|:|-)?\s*(\d+(?:\.\d+)?)\s*/\s*10\b",
            r"\b(\d+(?:\.\d+)?)\s*/\s*10\s+energy\b",
            r"\benergy(?:\s+level)?\s*(?:was|is|:|-)?\s*(\d+(?:\.\d+)?)\b",
        ],
        text,
        cast=int,
    )
    if numeric is not None:
        return numeric

    word_match = re.search(r"\benergy(?:\s+level)?\s*(?:was|is|:|-)?\s*(low|medium|moderate|high|great|poor)\b", text, re.IGNORECASE)
    return word_match.group(1).lower() if word_match else None


def _extract_optional_future_fields(text: str) -> dict[str, Any]:
    fields: dict[str, Any] = {}

    stress = _first_number(
        [
            r"\bstress\s*(?:was|is|:|-)?\s*(\d+(?:\.\d+)?)\s*/\s*10\b",
            r"\bstress\s*(?:was|is|:|-)?\s*(\d+(?:\.\d+)?)\b",
        ],
        text,
        cast=int,
    )
    if stress is not None:
        fields["stress_level"] = stress

    steps = _first_number(
        [
            r"\b(\d{3,6})\s*steps\b",
            r"\bsteps\s*(?:were|was|:|-)?\s*(\d{3,6})\b",
        ],
        text,
        cast=int,
    )
    if steps is not None:
        fields["steps"] = steps

    hydration = _first_number(
        [
            r"\b(?:water|hydration)\s*(?:was|is|:|-)?\s*(\d+(?:\.\d+)?)\s*(?:l|liters|litres)\b",
            r"\b(\d+(?:\.\d+)?)\s*(?:l|liters|litres)\s+(?:water|hydration)\b",
        ],
        text,
        cast=float,
    )
    if hydration is not None:
        fields["hydration_l"] = hydration

    mood_match = re.search(r"\bmood\s*(?:was|is|:|-)?\s*([a-zA-Z ]+?)(?:[.,;]|$)", text, re.IGNORECASE)
    if mood_match:
        fields["mood"] = mood_match.group(1).strip().lower()

    return fields


def parse_entry(raw_text: str) -> dict[str, Any]:
    """Parse a free-form daily entry into a flexible structured record."""
    cleaned_text = raw_text.strip()
    if not cleaned_text:
        raise ValueError("Entry text cannot be empty.")

    calories = _first_number(
        [
            r"\b(\d{3,5})\s*(?:calories|calorie|cals|cal|kcal)\b",
            r"\b(?:calories|calorie|cals|cal|kcal)\s*(?:were|was|around|about|:|-)?\s*(\d{3,5})\b",
        ],
        cleaned_text,
        cast=int,
    )
    protein = _first_number(
        [
            r"\b(\d{1,3})\s*(?:g|grams?)\s+(?:of\s+)?protein\b",
            r"\bprotein\s*(?:was|is|around|about|:|-)?\s*(\d{1,3})\s*(?:g|grams?)?\b",
        ],
        cleaned_text,
        cast=int,
    )
    sleep = _first_number(
        [
            r"\b(?:slept|sleep)\s*(?:was|for|:|-)?\s*(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|h)\b",
            r"\b(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|h)\s+(?:of\s+)?sleep\b",
        ],
        cleaned_text,
        cast=float,
    )

    record: dict[str, Any] = {
        "date": _extract_date(cleaned_text),
        "raw_text": cleaned_text,
        "calories": calories,
        "protein_g": protein,
        "training_type": _extract_training_type(cleaned_text),
        "sleep_hours": sleep,
        "energy_level": _extract_energy_level(cleaned_text),
        "notes": cleaned_text,
    }
    record.update(_extract_optional_future_fields(cleaned_text))
    return record
