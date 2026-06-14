"""Gamification : niveau, XP, série hebdomadaire et badges, calculés sur les activités réelles."""
from __future__ import annotations

import json
import math
from datetime import date, datetime, timedelta

from . import db


def _xp_of(a: dict) -> int:
    mins = (a["duration_s"] or 0) / 60
    km = (a["distance_m"] or 0) / 1000
    elev = a["elevation_m"] or 0
    return round(mins * 0.5 + km * 2 + elev / 30)


def _need(level: int) -> int:
    """XP cumulé requis pour atteindre `level` (niveau 1 = 0)."""
    return round(400 * (level - 1) ** 1.6)


def _level_for(xp: int) -> tuple[int, int, int]:
    lvl = 1
    while _need(lvl + 1) <= xp:
        lvl += 1
    return lvl, _need(lvl), _need(lvl + 1)


def _iso_weeks(acts: list[dict]) -> set[tuple[int, int]]:
    weeks = set()
    for a in acts:
        try:
            d = date.fromisoformat(a["activity_date"])
            iso = d.isocalendar()
            weeks.add((iso[0], iso[1]))
        except Exception:
            pass
    return weeks


def _current_streak(acts: list[dict]) -> int:
    """Nombre de semaines consécutives (jusqu'à cette semaine ou la précédente) avec ≥1 activité."""
    weeks = _iso_weeks(acts)
    if not weeks:
        return 0
    streak = 0
    cursor = date.today()
    # tolère que la semaine en cours soit encore vide : on démarre au plus tard la semaine passée
    start_iso = cursor.isocalendar()
    if (start_iso[0], start_iso[1]) not in weeks:
        cursor -= timedelta(days=7)
    while True:
        iso = cursor.isocalendar()
        if (iso[0], iso[1]) in weeks:
            streak += 1
            cursor -= timedelta(days=7)
        else:
            break
    return streak


def _aggregates(acts: list[dict]) -> dict:
    runs = [a for a in acts if a["sport"] == "run"]
    rides = [a for a in acts if a["sport"] == "bike"]
    swims = [a for a in acts if a["sport"] == "swim"]
    today = date.today()

    def km_block(rs, weeks):
        cut = today - timedelta(weeks=weeks)
        return sum((a["distance_m"] or 0) for a in rs
                   if date.fromisoformat(a["activity_date"]) >= cut) / 1000

    max_run_km = max(((a["distance_m"] or 0) / 1000 for a in runs), default=0)
    max_ride_km = max(((a["distance_m"] or 0) / 1000 for a in rides), default=0)
    max_elev = max((a["elevation_m"] or 0 for a in acts), default=0)
    # course rapide : meilleure allure sur ≥5km
    fast = None
    for a in runs:
        if (a["distance_m"] or 0) >= 5000 and a["avg_pace_s"]:
            fast = a["avg_pace_s"] if fast is None else min(fast, a["avg_pace_s"])

    last8 = today - timedelta(weeks=8)
    sports_8w = {a["sport"] for a in acts if date.fromisoformat(a["activity_date"]) >= last8}

    return {
        "max_run_km": max_run_km, "max_ride_km": max_ride_km, "max_elev": max_elev,
        "run_km_4w": km_block(runs, 4), "run_km_12w": km_block(runs, 12),
        "fast_pace_s": fast, "sports_8w": sports_8w,
        "n_runs": len(runs), "n_rides": len(rides), "n_swims": len(swims),
    }


def _badges(agg: dict, streak: int) -> list[dict]:
    """Liste de badges : earned + progression (0..1) pour les verrouillés."""
    def b(key, icon, title, desc, value, target, earned=None):
        prog = 1.0 if (earned is True) else min(1.0, value / target) if target else 0
        return {"key": key, "icon": icon, "title": title, "desc": desc,
                "earned": bool(earned if earned is not None else value >= target),
                "progress": round(prog, 2), "value": round(value, 1), "target": target}

    triple = len({"run", "bike", "swim"} & agg["sports_8w"])
    return [
        b("first", "🎬", "Premiers pas", "Enregistrer une activité", agg["n_runs"] + agg["n_rides"], 1),
        b("long20", "📏", "Longue distance", "Une course ≥ 20 km", agg["max_run_km"], 20),
        b("vol100", "🔥", "Gros mois", "100 km de course sur 4 semaines", agg["run_km_4w"], 100),
        b("vol300", "🏗️", "Socle solide", "300 km de course sur 12 semaines", agg["run_km_12w"], 300),
        b("regular", "📅", "Régulier", "4 semaines d'affilée actives", streak, 4),
        b("machine", "🦾", "Machine", "12 semaines d'affilée actives", streak, 12),
        b("triple", "🏅", "Triple discipline", "Course + vélo + natation sur 8 sem", triple, 3),
        b("climber", "🏔️", "Grimpeur", "800 m de D+ sur une sortie", agg["max_elev"], 800),
        b("centurion", "🚴", "Rouleur", "Une sortie vélo ≥ 80 km", agg["max_ride_km"], 80),
        b("speed", "⚡", "Vitesse pure", "Une course ≥ 5 km sous 4:15/km",
          (255 - agg["fast_pace_s"]) if agg["fast_pace_s"] else 0, 0.0001,
          earned=bool(agg["fast_pace_s"] and agg["fast_pace_s"] <= 255)),
    ]


def state() -> dict:
    acts = db.recent_activities(400)
    total_xp = sum(_xp_of(a) for a in acts)
    level, base, nxt = _level_for(total_xp)
    streak = _current_streak(acts)
    agg = _aggregates(acts)
    badges = _badges(agg, streak)

    span = nxt - base
    into = total_xp - base
    return {
        "xp": total_xp,
        "level": level,
        "level_progress_pct": round(into / span * 100) if span else 100,
        "xp_into_level": into,
        "xp_for_next": span,
        "streak_weeks": streak,
        "badges_earned": sum(1 for x in badges if x["earned"]),
        "badges_total": len(badges),
        "badges": badges,
        "weekly_volume_km": round(agg["run_km_4w"] / 4, 1),
    }
