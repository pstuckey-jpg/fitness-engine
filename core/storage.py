"""Storage abstraction for entries, profiles, settings, and users."""

from __future__ import annotations

import json
import sqlite3
import uuid
from abc import ABC, abstractmethod
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
ENTRIES_PATH = DATA_DIR / "entries.json"
PROFILES_PATH = DATA_DIR / "profiles.json"
DATABASE_PATH = DATA_DIR / "app.db"
DEFAULT_USER_ID = "demo_user"


ENTRY_COLUMNS = (
    "entry_id",
    "user_id",
    "date",
    "raw_text",
    "calories",
    "protein_g",
    "sleep_hours",
    "energy_level",
    "training_type",
    "steps",
    "mood",
    "stress",
    "notes",
    "created_at",
    "extra_json",
)


PROFILE_FIELDS = (
    "calorie_target",
    "protein_target",
    "goal_direction",
    "diet_preferences",
    "equipment",
    "injuries",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class DataStore(ABC):
    """Interface for user-scoped persistence."""

    @abstractmethod
    def save_entry(self, user_id: str, entry: dict[str, Any]) -> dict[str, Any]:
        """Save one structured entry for a user."""

    @abstractmethod
    def update_entry(self, user_id: str, entry_id: str, entry: dict[str, Any]) -> dict[str, Any] | None:
        """Update one structured entry for a user."""

    @abstractmethod
    def delete_entry(self, user_id: str, entry_id: str) -> bool:
        """Delete one entry for a user."""

    @abstractmethod
    def get_entry(self, user_id: str, entry_id: str) -> dict[str, Any] | None:
        """Load one entry for a user."""

    @abstractmethod
    def load_entries(self, user_id: str) -> list[dict[str, Any]]:
        """Load all entries for a user."""

    @abstractmethod
    def load_recent_entries(self, user_id: str, n: int) -> list[dict[str, Any]]:
        """Load the latest n entries for a user."""

    @abstractmethod
    def save_profile(self, user_id: str, profile: dict[str, Any]) -> dict[str, Any]:
        """Save a user profile."""

    @abstractmethod
    def load_profile(self, user_id: str) -> dict[str, Any]:
        """Load a user profile."""

    @abstractmethod
    def save_settings(self, user_id: str, settings: dict[str, Any]) -> dict[str, Any]:
        """Save user settings."""

    @abstractmethod
    def load_settings(self, user_id: str) -> dict[str, Any]:
        """Load user settings."""

    @abstractmethod
    def create_user(self, email: str, password_hash: str) -> dict[str, Any]:
        """Create a user account."""

    @abstractmethod
    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        """Find a user by email."""

    @abstractmethod
    def get_user(self, user_id: str) -> dict[str, Any] | None:
        """Find a user by id."""


class SQLiteDataStore(DataStore):
    """SQLite-backed store with a schema that can later move to a cloud database."""

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
                    updated_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
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
                    extra_json TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                );

                CREATE INDEX IF NOT EXISTS idx_entries_user_created
                    ON entries(user_id, created_at);

                CREATE TABLE IF NOT EXISTS settings (
                    user_id TEXT PRIMARY KEY,
                    settings_json TEXT,
                    updated_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                );
                """
            )

    def save_entry(self, user_id: str, entry: dict[str, Any]) -> dict[str, Any]:
        saved_entry = self._entry_for_storage(user_id, entry)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO entries (
                    entry_id, user_id, date, raw_text, calories, protein_g, sleep_hours,
                    energy_level, training_type, steps, mood, stress, notes, created_at, extra_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                tuple(saved_entry[column] for column in ENTRY_COLUMNS),
            )
        return self._entry_from_row(saved_entry)

    def update_entry(self, user_id: str, entry_id: str, entry: dict[str, Any]) -> dict[str, Any] | None:
        if self.get_entry(user_id, entry_id) is None:
            return None
        saved_entry = self._entry_for_storage(user_id, {**entry, "entry_id": entry_id})
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE entries SET
                    date = ?, raw_text = ?, calories = ?, protein_g = ?, sleep_hours = ?,
                    energy_level = ?, training_type = ?, steps = ?, mood = ?, stress = ?,
                    notes = ?, extra_json = ?
                WHERE user_id = ? AND entry_id = ?
                """,
                (
                    saved_entry["date"],
                    saved_entry["raw_text"],
                    saved_entry["calories"],
                    saved_entry["protein_g"],
                    saved_entry["sleep_hours"],
                    saved_entry["energy_level"],
                    saved_entry["training_type"],
                    saved_entry["steps"],
                    saved_entry["mood"],
                    saved_entry["stress"],
                    saved_entry["notes"],
                    saved_entry["extra_json"],
                    user_id,
                    entry_id,
                ),
            )
        return self.get_entry(user_id, entry_id)

    def delete_entry(self, user_id: str, entry_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM entries WHERE user_id = ? AND entry_id = ?",
                (user_id, entry_id),
            )
            return cursor.rowcount > 0

    def get_entry(self, user_id: str, entry_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM entries WHERE user_id = ? AND entry_id = ?",
                (user_id, entry_id),
            ).fetchone()
        return self._entry_from_row(dict(row)) if row else None

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
        saved_profile = {field: profile.get(field) for field in PROFILE_FIELDS}
        extra = {key: value for key, value in profile.items() if key not in PROFILE_FIELDS and key != "user_id"}
        saved_profile.update({"user_id": user_id, "profile_json": json.dumps(extra), "updated_at": utc_now()})
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO profiles (
                    user_id, calorie_target, protein_target, goal_direction, diet_preferences,
                    equipment, injuries, profile_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                (
                    saved_profile["user_id"],
                    saved_profile["calorie_target"],
                    saved_profile["protein_target"],
                    saved_profile["goal_direction"],
                    saved_profile["diet_preferences"],
                    saved_profile["equipment"],
                    saved_profile["injuries"],
                    saved_profile["profile_json"],
                    saved_profile["updated_at"],
                ),
            )
        return self._profile_from_row(saved_profile)

    def load_profile(self, user_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,)).fetchone()
        if row is None:
            return {"user_id": user_id}
        return self._profile_from_row(dict(row))

    def save_settings(self, user_id: str, settings: dict[str, Any]) -> dict[str, Any]:
        saved_settings = {"user_id": user_id, **settings}
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO settings (user_id, settings_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    settings_json = excluded.settings_json,
                    updated_at = excluded.updated_at
                """,
                (user_id, json.dumps(settings), utc_now()),
            )
        return saved_settings

    def load_settings(self, user_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute("SELECT settings_json FROM settings WHERE user_id = ?", (user_id,)).fetchone()
        if row is None:
            return {"user_id": user_id}
        return {"user_id": user_id, **json.loads(row["settings_json"] or "{}")}

    def create_user(self, email: str, password_hash: str) -> dict[str, Any]:
        user = {
            "user_id": str(uuid.uuid4()),
            "email": email.lower().strip(),
            "password_hash": password_hash,
            "created_at": utc_now(),
        }
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO users (user_id, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
                (user["user_id"], user["email"], user["password_hash"], user["created_at"]),
            )
        return user

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM users WHERE email = ?", (email.lower().strip(),)).fetchone()
        return dict(row) if row else None

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        return dict(row) if row else None

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

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
        extra = {
            key: value
            for key, value in entry.items()
            if key not in known and key not in {"id", "stress_level", "user_id", "entry_id"}
        }
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


class LocalJsonDataStore(DataStore):
    """JSON-backed fallback store for local development."""

    def __init__(self, entries_path: Path = ENTRIES_PATH, profiles_path: Path = PROFILES_PATH) -> None:
        self.entries_path = entries_path
        self.profiles_path = profiles_path

    def save_entry(self, user_id: str, entry: dict[str, Any]) -> dict[str, Any]:
        entries = self._load_all_entries()
        saved_entry = {**entry, "entry_id": entry.get("entry_id") or str(uuid.uuid4()), "user_id": user_id}
        entries.append(saved_entry)
        self._save_json(self.entries_path, entries)
        return saved_entry

    def update_entry(self, user_id: str, entry_id: str, entry: dict[str, Any]) -> dict[str, Any] | None:
        entries = self._load_all_entries()
        updated_entry = {**entry, "entry_id": entry_id, "user_id": user_id}
        did_update = False
        for index, existing in enumerate(entries):
            if existing.get("user_id", DEFAULT_USER_ID) == user_id and existing.get("entry_id") == entry_id:
                entries[index] = updated_entry
                did_update = True
        if not did_update:
            return None
        self._save_json(self.entries_path, entries)
        return updated_entry

    def delete_entry(self, user_id: str, entry_id: str) -> bool:
        entries = self._load_all_entries()
        kept = [
            entry for entry in entries
            if not (entry.get("user_id", DEFAULT_USER_ID) == user_id and entry.get("entry_id") == entry_id)
        ]
        if len(kept) == len(entries):
            return False
        self._save_json(self.entries_path, kept)
        return True

    def get_entry(self, user_id: str, entry_id: str) -> dict[str, Any] | None:
        for entry in self.load_entries(user_id):
            if entry.get("entry_id") == entry_id:
                return entry
        return None

    def load_entries(self, user_id: str) -> list[dict[str, Any]]:
        entries = [self._normalize_entry(entry) for entry in self._load_all_entries()]
        return [entry for entry in entries if entry.get("user_id") == user_id]

    def load_recent_entries(self, user_id: str, n: int) -> list[dict[str, Any]]:
        return self.load_entries(user_id)[-n:]

    def save_profile(self, user_id: str, profile: dict[str, Any]) -> dict[str, Any]:
        profiles = self._load_profiles()
        saved_profile = {**profile, "user_id": user_id}
        profiles[user_id] = saved_profile
        self._save_json(self.profiles_path, profiles)
        return saved_profile

    def load_profile(self, user_id: str) -> dict[str, Any]:
        return self._load_profiles().get(user_id, {"user_id": user_id})

    def save_settings(self, user_id: str, settings: dict[str, Any]) -> dict[str, Any]:
        return {"user_id": user_id, **settings}

    def load_settings(self, user_id: str) -> dict[str, Any]:
        return {"user_id": user_id}

    def create_user(self, email: str, password_hash: str) -> dict[str, Any]:
        return {"user_id": str(uuid.uuid4()), "email": email.lower().strip(), "password_hash": password_hash, "created_at": utc_now()}

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        return None

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        return None

    def _load_all_entries(self) -> list[dict[str, Any]]:
        if not self.entries_path.exists():
            return []
        data = self._load_json(self.entries_path, default=[])
        if not isinstance(data, list):
            raise ValueError(f"Expected a list of entries in {self.entries_path}.")
        return data

    def _load_profiles(self) -> dict[str, dict[str, Any]]:
        if not self.profiles_path.exists():
            return {}
        data = self._load_json(self.profiles_path, default={})
        if not isinstance(data, dict):
            raise ValueError(f"Expected a profile mapping in {self.profiles_path}.")
        return data

    def _normalize_entry(self, entry: dict[str, Any]) -> dict[str, Any]:
        return {"user_id": DEFAULT_USER_ID, **entry}

    def _load_json(self, path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def _save_json(self, path: Path, data: Any) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
            file.write("\n")


class PlaceholderCloudDataStore(DataStore):
    """Future PostgreSQL/Supabase/Firebase/PlanetScale-style store placeholder."""

    def save_entry(self, user_id: str, entry: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("Cloud database storage is not implemented yet.")

    def update_entry(self, user_id: str, entry_id: str, entry: dict[str, Any]) -> dict[str, Any] | None:
        raise NotImplementedError("Cloud database storage is not implemented yet.")

    def delete_entry(self, user_id: str, entry_id: str) -> bool:
        raise NotImplementedError("Cloud database storage is not implemented yet.")

    def get_entry(self, user_id: str, entry_id: str) -> dict[str, Any] | None:
        raise NotImplementedError("Cloud database storage is not implemented yet.")

    def load_entries(self, user_id: str) -> list[dict[str, Any]]:
        raise NotImplementedError("Cloud database storage is not implemented yet.")

    def load_recent_entries(self, user_id: str, n: int) -> list[dict[str, Any]]:
        raise NotImplementedError("Cloud database storage is not implemented yet.")

    def save_profile(self, user_id: str, profile: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("Cloud database storage is not implemented yet.")

    def load_profile(self, user_id: str) -> dict[str, Any]:
        raise NotImplementedError("Cloud database storage is not implemented yet.")

    def save_settings(self, user_id: str, settings: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("Cloud database storage is not implemented yet.")

    def load_settings(self, user_id: str) -> dict[str, Any]:
        raise NotImplementedError("Cloud database storage is not implemented yet.")

    def create_user(self, email: str, password_hash: str) -> dict[str, Any]:
        raise NotImplementedError("Cloud database storage is not implemented yet.")

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        raise NotImplementedError("Cloud database storage is not implemented yet.")

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        raise NotImplementedError("Cloud database storage is not implemented yet.")


DEFAULT_DATA_STORE: DataStore = SQLiteDataStore()


def load_entries(user_id: str = DEFAULT_USER_ID, data_store: DataStore = DEFAULT_DATA_STORE) -> list[dict[str, Any]]:
    return data_store.load_entries(user_id)


def load_recent_entries(
    user_id: str = DEFAULT_USER_ID,
    n: int = 7,
    data_store: DataStore = DEFAULT_DATA_STORE,
) -> list[dict[str, Any]]:
    return data_store.load_recent_entries(user_id, n)


def append_entry(
    entry: dict[str, Any],
    user_id: str = DEFAULT_USER_ID,
    data_store: DataStore = DEFAULT_DATA_STORE,
) -> dict[str, Any]:
    return data_store.save_entry(user_id, entry)


def update_entry(
    entry_id: str,
    entry: dict[str, Any],
    user_id: str = DEFAULT_USER_ID,
    data_store: DataStore = DEFAULT_DATA_STORE,
) -> dict[str, Any] | None:
    return data_store.update_entry(user_id, entry_id, entry)


def delete_entry(
    entry_id: str,
    user_id: str = DEFAULT_USER_ID,
    data_store: DataStore = DEFAULT_DATA_STORE,
) -> bool:
    return data_store.delete_entry(user_id, entry_id)


def get_entry(
    entry_id: str,
    user_id: str = DEFAULT_USER_ID,
    data_store: DataStore = DEFAULT_DATA_STORE,
) -> dict[str, Any] | None:
    return data_store.get_entry(user_id, entry_id)


def save_profile(
    profile: dict[str, Any],
    user_id: str = DEFAULT_USER_ID,
    data_store: DataStore = DEFAULT_DATA_STORE,
) -> dict[str, Any]:
    return data_store.save_profile(user_id, profile)


def load_profile(
    user_id: str = DEFAULT_USER_ID,
    data_store: DataStore = DEFAULT_DATA_STORE,
) -> dict[str, Any]:
    return data_store.load_profile(user_id)


def save_settings(
    settings: dict[str, Any],
    user_id: str = DEFAULT_USER_ID,
    data_store: DataStore = DEFAULT_DATA_STORE,
) -> dict[str, Any]:
    return data_store.save_settings(user_id, settings)


def load_settings(
    user_id: str = DEFAULT_USER_ID,
    data_store: DataStore = DEFAULT_DATA_STORE,
) -> dict[str, Any]:
    return data_store.load_settings(user_id)


def create_user(email: str, password_hash: str, data_store: DataStore = DEFAULT_DATA_STORE) -> dict[str, Any]:
    return data_store.create_user(email, password_hash)


def get_user_by_email(email: str, data_store: DataStore = DEFAULT_DATA_STORE) -> dict[str, Any] | None:
    return data_store.get_user_by_email(email)


def get_user(user_id: str, data_store: DataStore = DEFAULT_DATA_STORE) -> dict[str, Any] | None:
    return data_store.get_user(user_id)
