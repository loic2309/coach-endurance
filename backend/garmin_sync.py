"""Synchronisation des activités depuis Garmin Connect.

Utilise la librairie open-source `garminconnect` (basée sur `garth`). À la première
connexion, un token de session est sauvegardé dans data/garmin_tokens pour éviter de
se ré-authentifier (et de re-déclencher d'éventuels MFA) à chaque synchro.

Sécurité : les identifiants restent en local (.env). Le token aussi. Rien n'est envoyé
ailleurs que vers Garmin Connect.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta

from .config import settings
from . import db


class GarminError(RuntimeError):
    pass


def _client():
    try:
        from garminconnect import Garmin
    except ImportError as e:  # pragma: no cover
        raise GarminError("Librairie garminconnect manquante (pip install garminconnect).") from e

    token_dir = str(settings.garmin_token_dir)
    settings.garmin_token_dir.mkdir(parents=True, exist_ok=True)

    # 1) Essai via token sauvegardé
    try:
        g = Garmin()
        g.login(token_dir)
        return g
    except Exception:
        pass

    # 2) Login complet via identifiants
    if not settings.garmin_email or not settings.garmin_password:
        raise GarminError(
            "Aucun token valide et identifiants Garmin absents. "
            "Renseigne GARMIN_EMAIL / GARMIN_PASSWORD dans .env."
        )
    try:
        g = Garmin(settings.garmin_email, settings.garmin_password)
        g.login()
        g.garth.dump(token_dir)  # sauvegarde le token pour la prochaine fois
        return g
    except Exception as e:  # pragma: no cover - dépend du réseau
        raise GarminError(f"Échec de connexion Garmin : {e}") from e


def _sport_of(raw: dict) -> str:
    t = (raw.get("activityType") or {}).get("typeKey", "") or ""
    t = t.lower()
    if "run" in t or "treadmill" in t:
        return "run"
    if "cycl" in t or "bik" in t or "ride" in t:
        return "bike"
    if "swim" in t:
        return "swim"
    if "strength" in t or "cardio" in t or "hiit" in t or "training" in t:
        return "strength"
    return "other"


def _pace_s(raw: dict, sport: str) -> float | None:
    speed = raw.get("averageSpeed")  # m/s
    if not speed:
        return None
    if sport == "swim":
        return 100.0 / speed  # sec / 100m
    return 1000.0 / speed      # sec / km


def normalize(raw: dict) -> dict:
    sport = _sport_of(raw)
    start = raw.get("startTimeLocal") or raw.get("startTimeGMT") or ""
    try:
        d_iso = datetime.fromisoformat(start.replace("Z", "")).date().isoformat()
    except Exception:
        d_iso = date.today().isoformat()
    return {
        "activity_id": raw.get("activityId"),
        "start_time": start,
        "activity_date": d_iso,
        "sport": sport,
        "name": raw.get("activityName"),
        "distance_m": raw.get("distance"),
        "duration_s": raw.get("duration"),
        "avg_hr": raw.get("averageHR"),
        "avg_pace_s": _pace_s(raw, sport),
        "avg_speed": raw.get("averageSpeed"),
        "elevation_m": raw.get("elevationGain"),
        "calories": raw.get("calories"),
        "raw": json.dumps(raw),
    }


def sync(days_back: int = 120, limit: int = 200) -> dict:
    """Importe les activités des `days_back` derniers jours dans SQLite."""
    g = _client()
    activities = g.get_activities(0, limit)
    cutoff = date.today() - timedelta(days=days_back)

    imported = 0
    with db.connect() as conn:
        for raw in activities:
            try:
                norm = normalize(raw)
                if not norm["activity_id"]:
                    continue
                if date.fromisoformat(norm["activity_date"]) < cutoff:
                    continue
                db.upsert_activity(conn, norm)
                imported += 1
            except Exception:
                continue

    db.set_meta("last_sync", datetime.now().isoformat(timespec="seconds"))
    return {"imported": imported, "fetched": len(activities)}


def status() -> dict:
    return {
        "configured": bool(settings.garmin_email and settings.garmin_password),
        "token_present": settings.garmin_token_dir.exists()
        and any(settings.garmin_token_dir.iterdir()) if settings.garmin_token_dir.exists() else False,
        "last_sync": db.get_meta("last_sync"),
    }
