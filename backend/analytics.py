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


def measured_anchors() -> tuple[float, float, bool]:
    """Retourne (allure facile, allure seuil/20km) en sec/km, depuis l'analyse Garmin.

    Fallback sur la config si aucune donnée Garmin n'a encore été analysée.
    """
    easy = db.get_meta("measured_easy_s")
    thr = db.get_meta("measured_thr_s")
    if easy and thr:
        return float(easy), float(thr), True
    ref = settings.current_20km_min * 60 / 20
    return ref + 72, ref, False


def _zones2(easy: float, thr: float) -> dict:
    """Repères (sec/km) interpolés entre l'allure facile et l'allure seuil réelles."""
    gap = easy - thr
    return {
        "easy": easy,                 # Z2 mesurée
        "long": easy - 0.18 * gap,
        "tempo": thr + 0.30 * gap,    # allure ~20km
        "threshold": thr,             # seuil ~ allure 20km actuelle
        "vo2": thr - 0.28 * gap,      # allure ~5 km
    }


def target_paces() -> dict:
    """Allures qui montent CRESCENDO depuis tes allures Garmin réelles vers le palier 1 an.

    Deux ancres mesurées (facile + seuil) ; on les fait glisser vers les ancres objectif
    proportionnellement à l'avancement du plan. Aujourd'hui = exactement tes allures réelles.
    """
    easy_now, thr_now, from_garmin = measured_anchors()
    ratio = easy_now / thr_now

    goal_thr = settings.goal_20km_realistic_min * 60 / 20   # palier 1 an
    goal_easy = goal_thr * ratio                            # facile objectif (même rapport)

    frac = plan_progress()["pct"] / 100
    cur_easy = easy_now - (easy_now - goal_easy) * frac
    cur_thr = thr_now - (thr_now - goal_thr) * frac

    now = _zones2(cur_easy, cur_thr)
    goal = _zones2(goal_easy, goal_thr)
    zones = {k: {"now": fmt_pace(now[k]), "goal": fmt_pace(goal[k])} for k in now}

    return {
        "current_20km": fmt_pace(settings.current_20km_min * 60 / 20),
        "goal_20km_realistic": fmt_pace(goal_thr),
        "goal_20km_stretch": fmt_pace(settings.goal_20km_stretch_min * 60 / 20),
        "measured_easy": fmt_pace(easy_now),
        "from_garmin": from_garmin,
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
    # formate selon le sport
    for sp, v in best.items():
        if sp == "swim":
            v["pace"] = f"{int(v['pace_s']//60)}:{int(v['pace_s']%60):02d}/100m"
        elif sp == "bike":
            v["pace"] = f"{3600 / v['pace_s']:.1f} km/h"  # vitesse plutôt qu'allure
        else:
            v["pace"] = fmt_pace(v["pace_s"])
    return best
