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

FOOD_ESTIMATES = (
    {"terms": ("egg", "eggs"), "calories": 70, "protein_g": 6, "fat_g": 5, "saturated_fat_g": 1.6, "cholesterol_mg": 185, "sodium_mg": 70},
    {"terms": ("toast", "slice of bread", "bread"), "calories": 90, "protein_g": 3, "sugar_g": 2, "fat_g": 1, "sodium_mg": 140, "fiber_g": 1},
    {"terms": ("oatmeal", "oats"), "calories": 160, "protein_g": 6, "sugar_g": 1, "fat_g": 3, "sodium_mg": 5, "fiber_g": 4},
    {"terms": ("banana",), "calories": 105, "protein_g": 1, "sugar_g": 14, "fiber_g": 3},
    {"terms": ("apple",), "calories": 95, "sugar_g": 19, "fiber_g": 4},
    {"terms": ("rice",), "calories": 205, "protein_g": 4, "fiber_g": 1},
    {"terms": ("chicken breast", "chicken"), "calories": 260, "protein_g": 45, "fat_g": 6, "saturated_fat_g": 1.5, "cholesterol_mg": 125, "sodium_mg": 90},
    {"terms": ("turkey",), "calories": 220, "protein_g": 34, "fat_g": 9, "saturated_fat_g": 2.5, "cholesterol_mg": 95, "sodium_mg": 90},
    {"terms": ("salmon",), "calories": 360, "protein_g": 39, "fat_g": 22, "saturated_fat_g": 4, "cholesterol_mg": 100, "sodium_mg": 90},
    {"terms": ("tuna",), "calories": 180, "protein_g": 40, "fat_g": 1, "cholesterol_mg": 50, "sodium_mg": 320},
    {"terms": ("steak", "beef"), "calories": 420, "protein_g": 42, "fat_g": 26, "saturated_fat_g": 10, "cholesterol_mg": 120, "sodium_mg": 95},
    {"terms": ("greek yogurt", "yogurt"), "calories": 150, "protein_g": 18, "sugar_g": 6, "fat_g": 4, "saturated_fat_g": 2.5, "cholesterol_mg": 15, "sodium_mg": 70},
    {"terms": ("protein shake", "protein powder"), "calories": 140, "protein_g": 25, "sugar_g": 2, "fat_g": 2, "cholesterol_mg": 40, "sodium_mg": 160},
    {"terms": ("cottage cheese",), "calories": 180, "protein_g": 25, "sugar_g": 6, "fat_g": 5, "saturated_fat_g": 3, "cholesterol_mg": 25, "sodium_mg": 450},
    {"terms": ("peanut butter",), "calories": 190, "protein_g": 7, "sugar_g": 3, "fat_g": 16, "saturated_fat_g": 3, "sodium_mg": 150, "fiber_g": 2},
    {"terms": ("avocado",), "calories": 240, "protein_g": 3, "sugar_g": 1, "fat_g": 22, "saturated_fat_g": 3, "sodium_mg": 10, "fiber_g": 10},
    {"terms": ("pasta",), "calories": 320, "protein_g": 11, "sugar_g": 2, "fat_g": 2, "sodium_mg": 5, "fiber_g": 3},
    {"terms": ("potato",), "calories": 160, "protein_g": 4, "sugar_g": 2, "fiber_g": 4},
    {"terms": ("sweet potato",), "calories": 180, "protein_g": 4, "sugar_g": 7, "sodium_mg": 70, "fiber_g": 6},
    {"terms": ("beans",), "calories": 220, "protein_g": 14, "sugar_g": 1, "fat_g": 1, "sodium_mg": 350, "fiber_g": 12},
    {"terms": ("lentils",), "calories": 230, "protein_g": 18, "sugar_g": 4, "fat_g": 1, "sodium_mg": 5, "fiber_g": 15},
    {"terms": ("protein bar",), "calories": 220, "protein_g": 20, "sugar_g": 8, "fat_g": 7, "saturated_fat_g": 3, "cholesterol_mg": 10, "sodium_mg": 200, "fiber_g": 5},
    {"terms": ("burrito",), "calories": 650, "protein_g": 32, "sugar_g": 5, "fat_g": 25, "saturated_fat_g": 9, "cholesterol_mg": 70, "sodium_mg": 1200, "fiber_g": 8},
    {"terms": ("chicken bowl", "rice bowl"), "calories": 650, "protein_g": 42, "sugar_g": 5, "fat_g": 18, "saturated_fat_g": 4, "cholesterol_mg": 110, "sodium_mg": 900, "fiber_g": 8},
    {"terms": ("sandwich",), "calories": 450, "protein_g": 25, "sugar_g": 6, "fat_g": 16, "saturated_fat_g": 5, "cholesterol_mg": 50, "sodium_mg": 950, "fiber_g": 4},
    {"terms": ("burger",), "calories": 700, "protein_g": 35, "sugar_g": 8, "fat_g": 40, "saturated_fat_g": 15, "cholesterol_mg": 110, "sodium_mg": 1100, "fiber_g": 3},
    {"terms": ("pizza",), "calories": 285, "protein_g": 12, "sugar_g": 3, "fat_g": 10, "saturated_fat_g": 4.5, "cholesterol_mg": 25, "sodium_mg": 640, "fiber_g": 2},
    {"terms": ("coffee",), "calories": 5, "caffeine_mg": 95},
    {"terms": ("espresso",), "calories": 5, "caffeine_mg": 65},
    {"terms": ("latte",), "calories": 180, "protein_g": 10, "sugar_g": 12, "fat_g": 7, "saturated_fat_g": 4, "cholesterol_mg": 25, "sodium_mg": 120, "caffeine_mg": 75},
    {"terms": ("soda", "coke"), "calories": 150, "sugar_g": 39, "sodium_mg": 45, "caffeine_mg": 35},
    {"terms": ("energy drink",), "calories": 110, "sugar_g": 27, "sodium_mg": 200, "caffeine_mg": 160},
    {"terms": ("candy",), "calories": 220, "protein_g": 2, "sugar_g": 30, "fat_g": 8, "saturated_fat_g": 5, "sodium_mg": 40},
    {"terms": ("ice cream",), "calories": 270, "protein_g": 5, "sugar_g": 28, "fat_g": 14, "saturated_fat_g": 9, "cholesterol_mg": 55, "sodium_mg": 100},
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

    soreness = _first_number(
        [
            r"\bsoreness\s*(?:was|is|:|-)?\s*(\d+(?:\.\d+)?)\s*/\s*10\b",
            r"\bsoreness\s*(?:was|is|:|-)?\s*(\d+(?:\.\d+)?)\b",
        ],
        text,
        cast=int,
    )
    if soreness is not None:
        fields["soreness_level"] = soreness

    mood_match = re.search(r"\bmood\s*(?:was|is|:|-)?\s*([a-zA-Z ]+?)(?:[.,;]|$)", text, re.IGNORECASE)
    if mood_match:
        fields["mood"] = mood_match.group(1).strip().lower()

    return fields


def _parse_clock_time(raw: str) -> float | None:
    match = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", raw.lower())
    if not match:
        return None
    hours = int(match.group(1))
    minutes = int(match.group(2) or 0)
    period = match.group(3)
    if period == "pm" and hours < 12:
        hours += 12
    if period == "am" and hours == 12:
        hours = 0
    return hours + minutes / 60


def _estimate_sleep_from_times(text: str) -> float | None:
    match = re.search(
        r"\b(?:slept|sleep|bed|bedtime)?\s*(?:at|from)?\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)\s*(?:to|until|-|and woke(?: up)? at|woke(?: up)? at)\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)\b",
        text,
        re.IGNORECASE,
    )
    if not match:
        return None
    start = _parse_clock_time(match.group(1))
    end = _parse_clock_time(match.group(2))
    if start is None or end is None:
        return None
    duration = end - start if end >= start else 24 - start + end
    return round(duration, 1)


def _estimate_food(text: str) -> dict[str, Any] | None:
    lowered = text.lower()
    totals: dict[str, float] = {
        "calories": 0,
        "protein_g": 0,
        "sugar_g": 0,
        "cholesterol_mg": 0,
        "fat_g": 0,
        "saturated_fat_g": 0,
        "caffeine_mg": 0,
        "sodium_mg": 0,
        "fiber_g": 0,
    }
    foods: list[str] = []
    consumed_spans: list[tuple[int, int]] = []
    candidates: list[dict[str, Any]] = []

    def overlaps_existing(span: tuple[int, int]) -> bool:
        return any(span[0] < used[1] and span[1] > used[0] for used in consumed_spans)

    for index, item in enumerate(FOOD_ESTIMATES):
        for term in item["terms"]:
            escaped = re.escape(term)
            for amount_match in re.finditer(rf"\b(\d+)\s+{escaped}s?\b", lowered):
                candidates.append(
                    {
                        "item": item,
                        "index": index,
                        "term": term,
                        "count": int(amount_match.group(1)),
                        "span": amount_match.span(),
                    }
                )
            for simple_match in re.finditer(rf"\b{escaped}s?\b", lowered):
                candidates.append(
                    {
                        "item": item,
                        "index": index,
                        "term": term,
                        "count": 1,
                        "span": simple_match.span(),
                    }
                )

    for candidate in sorted(candidates, key=lambda candidate: (-len(candidate["term"]), candidate["span"][0])):
        if overlaps_existing(candidate["span"]):
            continue
        consumed_spans.append(candidate["span"])
        item = candidate["item"]
        count = candidate["count"]
        foods.append(f"{count} {item['terms'][0]}" if count > 1 else item["terms"][0])
        for field in totals:
            totals[field] += float(item.get(field, 0)) * count

    if not foods:
        return None
    return {**{key: round(value) for key, value in totals.items()}, "foods": foods}


def _parse_workouts(text: str) -> list[dict[str, Any]]:
    exercises: list[dict[str, Any]] = []
    pattern = re.compile(
        r"([a-z][a-z\s-]{2,32}?)\s+(\d+)\s*x\s*(\d+)(?:\s*(?:at|@)?\s*(\d+(?:\.\d+)?)\s*(?:lb|lbs|pounds|kg)?)?",
        re.IGNORECASE,
    )
    for match in pattern.finditer(text):
        name = re.sub(r"\b(and|then|with|plus)\b", "", match.group(1), flags=re.IGNORECASE).strip()
        sets = int(match.group(2))
        reps = int(match.group(3))
        weight = float(match.group(4)) if match.group(4) else None
        exercises.append(
            {
                "name": name,
                "sets": sets,
                "reps": reps,
                "weight": weight,
                "volume": round(sets * reps * weight) if weight else None,
            }
        )
    return exercises


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
    sleep_from_times = _estimate_sleep_from_times(cleaned_text)
    food_estimate = _estimate_food(cleaned_text)
    workouts = _parse_workouts(cleaned_text)

    record: dict[str, Any] = {
        "date": _extract_date(cleaned_text),
        "raw_text": cleaned_text,
        "calories": calories if calories is not None else food_estimate.get("calories") if food_estimate else None,
        "protein_g": protein if protein is not None else food_estimate.get("protein_g") if food_estimate else None,
        "training_type": _extract_training_type(cleaned_text),
        "sleep_hours": sleep if sleep is not None else sleep_from_times,
        "energy_level": _extract_energy_level(cleaned_text),
        "notes": cleaned_text,
    }
    record.update(_extract_optional_future_fields(cleaned_text))

    direct_fields = {
        "sugar_g": [
            r"\bsugar\s*(?:was|is|around|about|:|-)?\s*(\d+(?:\.\d+)?)\s*(?:g|grams?)?\b",
            r"\b(\d+(?:\.\d+)?)\s*(?:g|grams?)\s+sugar\b",
        ],
        "cholesterol_mg": [
            r"\bcholesterol\s*(?:was|is|around|about|:|-)?\s*(\d+(?:\.\d+)?)\s*(?:mg)?\b",
            r"\b(\d+(?:\.\d+)?)\s*mg\s+cholesterol\b",
        ],
        "fat_g": [
            r"\b(?:total\s+)?fat\s*(?:was|is|around|about|:|-)?\s*(\d+(?:\.\d+)?)\s*(?:g|grams?)?\b",
            r"\b(\d+(?:\.\d+)?)\s*(?:g|grams?)\s+(?:total\s+)?fat\b",
        ],
        "saturated_fat_g": [
            r"\b(?:saturated\s+fat|sat\s+fat)\s*(?:was|is|around|about|:|-)?\s*(\d+(?:\.\d+)?)\s*(?:g|grams?)?\b",
            r"\b(\d+(?:\.\d+)?)\s*(?:g|grams?)\s+(?:saturated\s+fat|sat\s+fat)\b",
        ],
        "caffeine_mg": [
            r"\bcaffeine\s*(?:was|is|around|about|:|-)?\s*(\d+(?:\.\d+)?)\s*(?:mg)?\b",
            r"\b(\d+(?:\.\d+)?)\s*mg\s+caffeine\b",
        ],
        "sodium_mg": [
            r"\bsodium\s*(?:was|is|around|about|:|-)?\s*(\d+(?:\.\d+)?)\s*(?:mg)?\b",
            r"\b(\d+(?:\.\d+)?)\s*mg\s+sodium\b",
        ],
        "fiber_g": [
            r"\b(?:fiber|fibre)\s*(?:was|is|around|about|:|-)?\s*(\d+(?:\.\d+)?)\s*(?:g|grams?)?\b",
            r"\b(\d+(?:\.\d+)?)\s*(?:g|grams?)\s+(?:fiber|fibre)\b",
        ],
    }
    for field, patterns in direct_fields.items():
        direct_value = _first_number(patterns, cleaned_text, cast=float)
        if direct_value is not None:
            record[field] = direct_value
        elif food_estimate and food_estimate.get(field, 0) > 0:
            record[field] = food_estimate[field]
            record[f"{field}_estimated"] = True

    if calories is None and food_estimate:
        record["calories_estimated"] = True
    if protein is None and food_estimate:
        record["protein_estimated"] = True
    if food_estimate:
        record["estimated_foods"] = food_estimate["foods"]
    if sleep_from_times is not None:
        record["sleep_estimated_from_times"] = True
    if workouts:
        record["exercises"] = workouts
        record["training_volume"] = sum(exercise["volume"] or 0 for exercise in workouts) or None
    return record
