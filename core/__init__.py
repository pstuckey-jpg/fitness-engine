"""Core logic for the fitness and nutrition insight engine."""

from .brief import generate_brief
from .entries import add_entry
from .intake import generate_intake_guidance
from .profile import load_profile, save_profile
from .trends import compute_trends
from .weekly import generate_weekly_summary

__all__ = [
    "add_entry",
    "compute_trends",
    "generate_brief",
    "generate_intake_guidance",
    "generate_weekly_summary",
    "load_profile",
    "save_profile",
]
