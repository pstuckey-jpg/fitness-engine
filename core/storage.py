"""SQLite-backed storage for entries, profiles, settings, and users."""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
DATABASE_PATH = DATA_DIR / "app.db"
DEFAULT_USER_ID = "demo_user"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SQLiteDataStore:
    def __init__(self, database_path: Path = DATABASE_PATH) -> None:
        self.database_path = database_path
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS profiles (
                    user_id TEXT PRIMARY KEY,
                    calorie_target TEXT,
                    protein_target TEXT,
                    goal_direction TEXT,
                    diet_preferences TEXT,
                    equipment TEXT,
                    injuries TEXT,
                    profile_json TEXT,
                    updated_at TEXT
                );
                CREATE TABLE IF NOT EXISTS entries (
                    entry_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    date TEXT,
                    raw_text TEXT,
                    calories REAL,
                    protein_g REAL,
                    sleep_hours REAL,
                    energy_level REAL,
                    training_type TEXT,
                    steps REAL,
                    mood TEXT,
                    stress REAL,
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    extra_json TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_entries_user_created ON entries(user_id, created_at);
                CREATE TABLE IF NOT EXISTS settings (
                    user_id TEXT PRIMARY KEY,
                    settings_json TEXT,
                    updated_at TEXT
                );
                """
            )

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def save_entry(self, user_id: str, entry: dict[str, Any]) -> dict[str, Any]:
        saved = self._entry_for_storage(user_id, entry)
        columns = list(saved.keys())
        placeholders = ", ".join("?" for _ in columns)
        with self._connect() as connection:
            connection.execute(
                f"INSERT INTO entries ({', '.join(columns)}) VALUES ({placeholders})",
                tuple(saved[column] for column in columns),
            )
        return self._entry_from_row(saved)

    def load_entries(self, user_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM entries WHERE user_id = ? ORDER BY created_at ASC",
                (user_id,),
            ).fetchall()
        return [self._entry_from_row(dict(row)) for row in rows]

    def load_recent_entries(self, user_id: str, n: int) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM entries WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
                (user_id, n),
            ).fetchall()
        return [self._entry_from_row(dict(row)) for row in reversed(rows)]

    def save_profile(self, user_id: str, profile: dict[str, Any]) -> dict[str, Any]:
        known_fields = ["calorie_target", "protein_target", "goal_direction", "diet_preferences", "equipment", "injuries"]
        known = {field: profile.get(field) for field in known_fields}
        extra = {key: value for key, value in profile.items() if key not in known_fields and key != "user_id"}
        saved = {**known, "user_id": user_id, "profile_json": json.dumps(extra), "updated_at": utc_now()}
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO profiles (user_id, calorie_target, protein_target, goal_direction, diet_preferences, equipment, injuries, profile_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    calorie_target = excluded.calorie_target,
                    protein_target = excluded.protein_target,
                    goal_direction = excluded.goal_direction,
                    diet_preferences = excluded.diet_preferences,
                    equipment = excluded.equipment,
                    injuries = excluded.injuries,
                    profile_json = excluded.profile_json,
                    updated_at = excluded.updated_at
                """,
                (saved["user_id"], saved["calorie_target"], saved["protein_target"], saved["goal_direction"], saved["diet_preferences"], saved["equipment"], saved["injuries"], saved["profile_json"], saved["updated_at"]),
            )
        return self._profile_from_row(saved)

    def load_profile(self, user_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,)).fetchone()
        return self._profile_from_row(dict(row)) if row else {"user_id": user_id}

    def save_settings(self, user_id: str, settings: dict[str, Any]) -> dict[str, Any]:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO settings (user_id, settings_json, updated_at) VALUES (?, ?, ?) ON CONFLICT(user_id) DO UPDATE SET settings_json = excluded.settings_json, updated_at = excluded.updated_at",
                (user_id, json.dumps(settings), utc_now()),
            )
        return {"user_id": user_id, **settings}

    def load_settings(self, user_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute("SELECT settings_json FROM settings WHERE user_id = ?", (user_id,)).fetchone()
        return {"user_id": user_id, **json.loads(row["settings_json"] or "{}")} if row else {"user_id": user_id}

    def create_user(self, email: str, password_hash: str) -> dict[str, Any]:
        user = {"user_id": str(uuid.uuid4()), "email": email.lower().strip(), "password_hash": password_hash, "created_at": utc_now()}
        with self._connect() as connection:
            connection.execute("INSERT INTO users (user_id, email, password_hash, created_at) VALUES (?, ?, ?, ?)", (user["user_id"], user["email"], user["password_hash"], user["created_at"]))
        return user

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM users WHERE email = ?", (email.lower().strip(),)).fetchone()
        return dict(row) if row else None

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        return dict(row) if row else None

    def _entry_for_storage(self, user_id: str, entry: dict[str, Any]) -> dict[str, Any]:
        known = {
            "entry_id": entry.get("entry_id") or entry.get("id") or str(uuid.uuid4()),
            "user_id": user_id,
            "date": entry.get("date"),
            "raw_text": entry.get("raw_text"),
            "calories": entry.get("calories"),
            "protein_g": entry.get("protein_g"),
            "sleep_hours": entry.get("sleep_hours"),
            "energy_level": entry.get("energy_level"),
            "training_type": entry.get("training_type"),
            "steps": entry.get("steps"),
            "mood": entry.get("mood"),
            "stress": entry.get("stress_level", entry.get("stress")),
            "notes": entry.get("notes"),
            "created_at": entry.get("created_at") or utc_now(),
        }
        extra = {key: value for key, value in entry.items() if key not in known and key not in {"id", "stress_level", "user_id", "entry_id"}}
        known["extra_json"] = json.dumps(extra)
        return known

    def _entry_from_row(self, row: dict[str, Any]) -> dict[str, Any]:
        extra = json.loads(row.get("extra_json") or "{}")
        entry = {key: value for key, value in row.items() if key != "extra_json"}
        entry["stress_level"] = entry.get("stress")
        return {**extra, **entry}

    def _profile_from_row(self, row: dict[str, Any]) -> dict[str, Any]:
        extra = json.loads(row.get("profile_json") or "{}")
        profile = {key: value for key, value in row.items() if key != "profile_json"}
        return {**extra, **profile}


DEFAULT_DATA_STORE = SQLiteDataStore()


def load_entries(user_id: str = DEFAULT_USER_ID, data_store=DEFAULT_DATA_STORE) -> list[dict[str, Any]]:
    return data_store.load_entries(user_id)


def load_recent_entries(user_id: str = DEFAULT_USER_ID, n: int = 7, data_store=DEFAULT_DATA_STORE) -> list[dict[str, Any]]:
    return data_store.load_recent_entries(user_id, n)


def append_entry(entry: dict[str, Any], user_id: str = DEFAULT_USER_ID, data_store=DEFAULT_DATA_STORE) -> dict[str, Any]:
    return data_store.save_entry(user_id, entry)


def save_profile(profile: dict[str, Any], user_id: str = DEFAULT_USER_ID, data_store=DEFAULT_DATA_STORE) -> dict[str, Any]:
    return data_store.save_profile(user_id, profile)


def load_profile(user_id: str = DEFAULT_USER_ID, data_store=DEFAULT_DATA_STORE) -> dict[str, Any]:
    return data_store.load_profile(user_id)


def save_settings(settings: dict[str, Any], user_id: str = DEFAULT_USER_ID, data_store=DEFAULT_DATA_STORE) -> dict[str, Any]:
    return data_store.save_settings(user_id, settings)


def load_settings(user_id: str = DEFAULT_USER_ID, data_store=DEFAULT_DATA_STORE) -> dict[str, Any]:
    return data_store.load_settings(user_id)


def create_user(email: str, password_hash: str, data_store=DEFAULT_DATA_STORE) -> dict[str, Any]:
    return data_store.create_user(email, password_hash)


def get_user_by_email(email: str, data_store=DEFAULT_DATA_STORE) -> dict[str, Any] | None:
    return data_store.get_user_by_email(email)


def get_user(user_id: str, data_store=DEFAULT_DATA_STORE) -> dict[str, Any] | None:
    return data_store.get_user(user_id)
