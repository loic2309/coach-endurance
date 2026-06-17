"""Sorties réellement réalisées (Garmin) avec analyse coach par séance."""
from __future__ import annotations

import json
from datetime import date, timedelta

from . import db

WEEKDAYS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
EMOJI = {"run": "🏃", "bike": "🚴", "swim": "🏊", "strength": "🏋️", "other": "🏅"}


def _hrmax(acts: list[dict]) -> float:
    hrs = []
    for a in acts:
        if a["raw"]:
            try:
                h = json.loads(a["raw"]).get("maxHR")
                if h:
                    hrs.append(h)
            except Exception:
                pass
    return max(hrs) if hrs else 195.0


def _fmt_pace(sp: float | None, sport: str) -> str:
    if not sp:
        return "—"
    if sport == "swim":
        s = 100 / sp; return f"{int(s//60)}:{int(s%60):02d}/100m"
    if sport == "bike":
        return f"{sp*3.6:.1f} km/h"
    s = 1000 / sp; return f"{int(s//60)}:{int(s%60):02d}/km"


def _verdict(sport, pct, zones, cad, aero_te, anaero_te, elev) -> dict:
    total = sum(zones.values()) or 1
    easy_frac = (zones["z1"] + zones["z2"]) / total
    hard_frac = (zones["z4"] + zones["z5"]) / total
    insights, score = [], 7

    if sport == "run":
        if pct:
            if pct < 76:
                insights.append(f"FC {pct}% max — bien en aérobie ✅"); score += 1
            elif pct < 86:
                insights.append(f"FC {pct}% max — effort soutenu")
            else:
                insights.append(f"FC {pct}% max — grosse intensité 🔥")
        if cad:
            if 170 <= cad <= 185:
                insights.append(f"Cadence {cad} ppm — excellent ✅"); score += 1
            else:
                insights.append(f"Cadence {cad} ppm — vise 170–180")
        if easy_frac >= 0.7 and anaero_te < 1.5:
            label, color = "Sortie aérobie maîtrisée", "ok"; score += 1
            insights.append(f"{round(easy_frac*100)}% du temps en Z1–Z2 — base bien construite")
        elif hard_frac >= 0.25 or anaero_te >= 1.5:
            label, color = "Séance de qualité", "warn"; score += 1
            insights.append(f"{round(hard_frac*100)}% en Z4–Z5 — du jus dépensé, récupère bien")
        else:
            label, color = "Sortie mixte", "cyan"
        if elev and elev >= 80:
            insights.append(f"{round(elev)} m D+ — bon stimulus de force")
    elif sport == "bike":
        label, color = "Sortie vélo", "cyan"
        if pct:
            insights.append(f"FC {pct}% max")
        if easy_frac >= 0.7:
            insights.append("majorité en endurance ✅"); score += 1
        if elev and elev >= 200:
            insights.append(f"{round(elev)} m D+ — joli relief")
    elif sport == "swim":
        label, color = "Séance natation", "cyan"; score += 1
        insights.append("contact avec l'eau maintenu — ton point de progrès")
    else:
        label, color = "Renfo / autre", "cyan"
        insights.append("travail de force/cardio — transférable aux 3 sports")

    if aero_te:
        score += 1 if aero_te >= 2 else 0
    return {"label": label, "color": color, "score": min(score, 10), "insights": insights}


def week_activities(days: int = 7) -> dict:
    all_acts = db.recent_activities(80)
    if not all_acts:
        return {"available": False, "activities": [], "week_start": None}
    hrmax = _hrmax(all_acts)
    today = date.today()
    monday = today - timedelta(days=today.weekday())

    out = []
    for a in all_acts:
        if a["activity_date"] < monday.isoformat():
            continue
        r = json.loads(a["raw"]) if a["raw"] else {}
        sport = a["sport"]
        hr = a["avg_hr"]
        pct = round(hr / hrmax * 100) if hr else None
        zones = {f"z{i}": round(r.get(f"hrTimeInZone_{i}", 0) / 60) for i in range(1, 6)}
        cad = round(r.get("averageRunningCadenceInStepsPerMinute", 0)) or None
        aero = round(r.get("aerobicTrainingEffect", 0), 1)
        anaero = round(r.get("anaerobicTrainingEffect", 0), 1)
        d = date.fromisoformat(a["activity_date"])
        out.append({
            "name": a["name"], "date": a["activity_date"], "weekday": WEEKDAYS[d.weekday()],
            "sport": sport, "emoji": EMOJI.get(sport, "🏅"),
            "km": round((a["distance_m"] or 0) / 1000, 1),
            "dur_min": round((a["duration_s"] or 0) / 60),
            "pace": _fmt_pace(a["avg_speed"], sport),
            "avg_hr": int(hr) if hr else None, "pct_max": pct,
            "max_hr": int(r["maxHR"]) if r.get("maxHR") else None,
            "zones": zones,
            "cadence": cad, "stride": round(r.get("avgStrideLength", 0)) or None,
            "steps": r.get("steps"),
            "power": round(r.get("avgPower")) if r.get("avgPower") else None,
            "elevation": round(a["elevation_m"]) if a["elevation_m"] else 0,
            "calories": int(a["calories"]) if a["calories"] else None,
            "vo2max": r.get("vO2MaxValue"),
            "aerobic_te": aero, "anaerobic_te": anaero,
            "verdict": _verdict(sport, pct, zones, cad, aero, anaero, a["elevation_m"] or 0),
        })
    out.sort(key=lambda x: x["date"])
    tot_min = sum(x["dur_min"] for x in out)
    tot_km = round(sum(x["km"] for x in out if x["sport"] in ("run", "bike")), 1)
    return {
        "available": True, "week_start": monday.isoformat(),
        "count": len(out), "total_min": tot_min, "total_km": tot_km,
        "activities": out,
    }
