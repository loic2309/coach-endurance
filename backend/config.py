"""Configuration chargée depuis l'environnement (.env)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent


def _d(key: str, default: str) -> date:
    return date.fromisoformat(os.getenv(key, default))


def _i(key: str, default: int) -> int:
    return int(os.getenv(key, str(default)))


@dataclass
class Settings:
    athlete_name: str = os.getenv("ATHLETE_NAME", "Athlète")
    garmin_email: str | None = os.getenv("GARMIN_EMAIL")
    garmin_password: str | None = os.getenv("GARMIN_PASSWORD")

    # Auth de l'app (activée seulement si APP_PASSWORD est défini — utile en hébergé)
    app_user: str = os.getenv("APP_USER", "coach")
    app_password: str | None = os.getenv("APP_PASSWORD")

    race_20km_date: date = _d("RACE_20KM_DATE", "2027-05-30")
    race_703_date: date = _d("RACE_703_DATE", "2027-06-20")

    # realistic = LE but visé par les allures (1h05) ; stretch = si tout claque (1h02)
    goal_20km_realistic_min: int = _i("GOAL_20KM_REALISTIC_MIN", 65)
    goal_20km_stretch_min: int = _i("GOAL_20KM_STRETCH_MIN", 62)
    goal_703_min: int = _i("GOAL_703_MIN", 300)

    current_20km_min: int = _i("CURRENT_20KM_MIN", 81)
    current_703_min: int = _i("CURRENT_703_MIN", 315)

    data_dir: Path = Path(os.getenv("DATA_DIR", str(ROOT / "data")))

    # Le plan démarre le lundi de la semaine en cours.
    plan_start: date = date(2026, 6, 15)

    @property
    def db_path(self) -> Path:
        return self.data_dir / "coach.db"

    @property
    def garmin_token_dir(self) -> Path:
        return self.data_dir / "garmin_tokens"


settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
