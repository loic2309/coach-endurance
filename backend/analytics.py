"""Analyse : allures cibles, charge d'entrainement, progression vers les objectifs."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from .config import settings
from . import db


def fmt_pace(sec_per_km: float | None) -> str:
    if not sec_per_km:
        return "—"
    m = int(sec_per_km // 60)
    s = int(round(sec_per_km % 60))
    if s == 60:
        m, s = m + 1, 0
    return f"{m}:{s:02d}/km"


def _zones_from_ref(ref: float) -> dict:
    """Repères d'entrainement (sec/km) dérivés d'une allure de référence 20km."""
    return {
        "easy": ref + 75,        # endurance Z2
        "long": ref + 60,
        "tempo": ref + 15,       # allure ~20km
        "threshold": ref,        # seuil ~ allure semi/20km
        "vo2": ref - 25,         # allure ~5 km
    }


def target_paces() -> dict:
    """Allures d'entrainement qui montent CRESCENDO du niveau actuel vers l'objectif.

    L'allure de référence interpole entre l'allure 20km actuelle et l'allure objectif
    en fonction de l'avancement dans le plan : aujourd'hui = niveau actuel, jour de course = objectif.
    """
    current = settings.current_20km_min * 60 / 20   # sec/km actuels
    goal = settings.goal_20km_realistic_min * 60 / 20
    stretch = settings.goal_20km_stretch_min * 60 / 20

    frac = plan_progress()["pct"] / 100             # 0 au début, 1 à la course
    ref_now = current - (current - goal) * frac     # référence du moment

    now = _zones_from_ref(ref_now)
    goal_zones = _zones_from_ref(goal)
    zones = {
        k: {"now": fmt_pace(now[k]), "goal": fmt_pace(goal_zones[k])}
        for k in now
    }
    return {
        "current_20km": fmt_pace(current),
        "goal_20km_realistic": fmt_pace(goal),
        "goal_20km_stretch": fmt_pace(stretch),
        "ref_now": fmt_pace(ref_now),
        "progress_pct": round(frac * 100),
        "zones": zones,
    }


def goal_summary() -> dict:
    days_20 = (settings.race_20km_date - date.today()).days
    days_70 = (settings.race_703_date - date.today()).days
    return {
        "athlete": settings.athlete_name,
        "today": date.today().isoformat(),
        "race_20km": {
            "date": settings.race_20km_date.isoformat(),
            "days_left": days_20,
            "weeks_left": round(days_20 / 7, 1),
            "current_min": settings.current_20km_min,
            "goal_realistic_min": settings.goal_20km_realistic_min,
            "goal_stretch_min": settings.goal_20km_stretch_min,
        },
        "race_703": {
            "date": settings.race_703_date.isoformat(),
            "days_left": days_70,
            "weeks_left": round(days_70 / 7, 1),
            "current_min": settings.current_703_min,
            "goal_min": settings.goal_703_min,
        },
    }


def plan_progress() -> dict:
    """Avancement dans le plan (temps écoulé entre le début et la dernière course)."""
    last_race = max(settings.race_20km_date, settings.race_703_date)
    total = (last_race - settings.plan_start).days
    elapsed = (date.today() - settings.plan_start).days
    pct = max(0, min(100, round(elapsed / total * 100))) if total else 0
    return {
        "start": settings.plan_start.isoformat(),
        "end": last_race.isoformat(),
        "total_weeks": round(total / 7),
        "elapsed_weeks": max(0, round(elapsed / 7)),
        "pct": pct,
    }


def _week_bounds(d: date) -> tuple[date, date]:
    monday = d - timedelta(days=d.weekday())
    return monday, monday + timedelta(days=6)


def weekly_load(weeks_back: int = 12) -> list[dict]:
    """Charge réelle (durée par sport) sur les N dernières semaines, depuis Garmin."""
    today = date.today()
    out = []
    for w in range(weeks_back - 1, -1, -1):
        ref = today - timedelta(weeks=w)
        mon, sun = _week_bounds(ref)
        acts = db.activities_between(mon.isoformat(), sun.isoformat())
        by_sport: dict[str, float] = {}
        total = 0.0
        for a in acts:
            mins = (a["duration_s"] or 0) / 60
            by_sport[a["sport"]] = by_sport.get(a["sport"], 0) + mins
            total += mins
        out.append({
            "week_start": mon.isoformat(),
            "label": mon.strftime("%d/%m"),
            "total_min": round(total),
            "by_sport_min": {k: round(v) for k, v in by_sport.items()},
        })
    return out


def best_efforts() -> dict:
    """Meilleures allures moyennes récentes par sport (proxy de forme)."""
    acts = db.recent_activities(120)
    best: dict[str, dict] = {}
    for a in acts:
        sp = a["sport"]
        if sp not in ("run", "bike", "swim"):
            continue
        dist = a["distance_m"] or 0
        if dist < 1000:  # ignore les séances trop courtes
            continue
        pace = a["avg_pace_s"]
        if pace is None:
            continue
        if sp not in best or pace < best[sp]["pace_s"]:
            best[sp] = {
                "pace_s": pace,
                "name": a["name"],
                "date": a["activity_date"],
                "distance_km": round(dist / 1000, 1),
            }
    # formate
    for sp, v in best.items():
        v["pace"] = fmt_pace(v["pace_s"]) if sp != "swim" else f"{int(v['pace_s']//60)}:{int(v['pace_s']%60):02d}/100m"
    return best
