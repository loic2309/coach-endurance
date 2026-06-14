"""Stockage SQLite (stdlib, aucune dépendance lourde).

Deux tables :
- activities : activités importées de Garmin (1 ligne par séance réalisée)
- session_log : statut des séances planifiées (fait / sauté), saisi manuellement
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterator

from .config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS activities (
    activity_id   INTEGER PRIMARY KEY,
    start_time    TEXT    NOT NULL,        -- ISO datetime
    activity_date TEXT    NOT NULL,        -- ISO date (pour regrouper par jour)
    sport         TEXT,                    -- running / cycling / swimming / other
    name          TEXT,
    distance_m    REAL,
    duration_s    REAL,
    avg_hr        REAL,
    avg_pace_s    REAL,                    -- secondes / km (course) ou /100m (natation)
    avg_speed     REAL,                    -- m/s
    elevation_m   REAL,
    calories      REAL,
    raw           TEXT                     -- JSON brut Garmin
);

CREATE TABLE IF NOT EXISTS session_log (
    plan_date  TEXT NOT NULL,             -- ISO date de la séance planifiée
    slug       TEXT NOT NULL,             -- identifiant de la séance dans la journée
    status     TEXT NOT NULL,             -- done / skipped
    note       TEXT,
    PRIMARY KEY (plan_date, slug)
);

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)


def upsert_activity(conn: sqlite3.Connection, a: dict) -> None:
    conn.execute(
        """
        INSERT INTO activities (activity_id, start_time, activity_date, sport, name,
            distance_m, duration_s, avg_hr, avg_pace_s, avg_speed, elevation_m, calories, raw)
        VALUES (:activity_id, :start_time, :activity_date, :sport, :name,
            :distance_m, :duration_s, :avg_hr, :avg_pace_s, :avg_speed, :elevation_m, :calories, :raw)
        ON CONFLICT(activity_id) DO UPDATE SET
            start_time=excluded.start_time, activity_date=excluded.activity_date,
            sport=excluded.sport, name=excluded.name, distance_m=excluded.distance_m,
            duration_s=excluded.duration_s, avg_hr=excluded.avg_hr, avg_pace_s=excluded.avg_pace_s,
            avg_speed=excluded.avg_speed, elevation_m=excluded.elevation_m,
            calories=excluded.calories, raw=excluded.raw
        """,
        a,
    )


def recent_activities(limit: int = 60) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM activities ORDER BY start_time DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def activities_between(start_iso: str, end_iso: str) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM activities WHERE activity_date >= ? AND activity_date <= ? "
            "ORDER BY start_time ASC",
            (start_iso, end_iso),
        ).fetchall()
    return [dict(r) for r in rows]


def set_session_status(plan_date: str, slug: str, status: str, note: str | None = None) -> None:
    with connect() as conn:
        if status == "planned":
            conn.execute(
                "DELETE FROM session_log WHERE plan_date=? AND slug=?", (plan_date, slug)
            )
        else:
            conn.execute(
                "INSERT INTO session_log (plan_date, slug, status, note) VALUES (?,?,?,?) "
                "ON CONFLICT(plan_date, slug) DO UPDATE SET status=excluded.status, note=excluded.note",
                (plan_date, slug, status, note),
            )


def session_statuses(start_iso: str, end_iso: str) -> dict[str, str]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT plan_date, slug, status FROM session_log WHERE plan_date >= ? AND plan_date <= ?",
            (start_iso, end_iso),
        ).fetchall()
    return {f"{r['plan_date']}::{r['slug']}": r["status"] for r in rows}


def get_meta(key: str) -> str | None:
    with connect() as conn:
        row = conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return row["value"] if row else None


def set_meta(key: str, value: str) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO meta (key, value) VALUES (?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
