"""Calcul de forme et de progression à partir des données Garmin (FC + vitesse).

- Forme (modèle CTL/ATL/TSB façon TrainingPeaks) : Fitness, Fatigue, Forme.
- Efficacité aérobie (EF = vitesse / FC) : progresses-tu à FC égale ?
- Prédictions de temps (Riegel) pour le 20km, le semi, et estimation 70.3.
"""
from __future__ import annotations

import json
import statistics as st
from datetime import date, timedelta

from . import db


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
    return max(hrs) if hrs else 190.0


# ----------------------------------------------------------------- Forme

def form_state() -> dict:
    acts = db.recent_activities(400)
    if not acts:
        return {"available": False}
    hrmax = _hrmax(acts)
    lthr = 0.88 * hrmax

    daily: dict[str, float] = {}
    for a in acts:
        dur_h = (a["duration_s"] or 0) / 3600
        if dur_h <= 0:
            continue
        hr = a["avg_hr"]
        intensity = (hr / lthr) if hr else 0.72
        intensity = max(0.5, min(intensity, 1.15))
        load = dur_h * intensity * intensity * 100   # TSS approximé
        daily[a["activity_date"]] = daily.get(a["activity_date"], 0) + load

    today = date.today()
    start = today - timedelta(days=180)
    ctl = atl = 0.0
    hist: dict[str, float] = {}
    d = start
    while d <= today:
        load = daily.get(d.isoformat(), 0.0)
        ctl += (load - ctl) / 42
        atl += (load - atl) / 7
        hist[d.isoformat()] = ctl
        d += timedelta(days=1)

    tsb = ctl - atl
    ctl_4w = hist.get((today - timedelta(days=28)).isoformat(), 0.0)
    weekly = []
    for w in range(11, -1, -1):
        dd = today - timedelta(weeks=w)
        weekly.append({"label": dd.strftime("%d/%m"), "ctl": round(hist.get(dd.isoformat(), 0.0), 1)})

    if tsb >= 8:
        status, label = "fresh", "Frais / affûté"
    elif tsb >= -12:
        status, label = "optimal", "Équilibré — bonne fenêtre pour progresser"
    else:
        status, label = "loaded", "Charge élevée — surveille la récup"

    return {
        "available": True,
        "fitness": round(ctl, 1),      # CTL
        "fatigue": round(atl, 1),      # ATL
        "form": round(tsb, 1),         # TSB
        "fitness_4w_ago": round(ctl_4w, 1),
        "fitness_trend": round(ctl - ctl_4w, 1),
        "status": status,
        "status_label": label,
        "weekly": weekly,
    }


# ------------------------------------------------------- Efficacité aérobie

def efficiency() -> dict:
    acts = db.recent_activities(400)
    if not acts:
        return {"available": False, "series": []}
    hrmax = _hrmax(acts)
    runs = [a for a in acts if a["sport"] == "run" and a["avg_hr"] and a["avg_speed"]
            and (a["distance_m"] or 0) >= 4000]

    monthly: dict[str, list[float]] = {}
    for r in runs:
        if r["avg_hr"] > 0.88 * hrmax:   # garde l'aérobie (réduit le bruit)
            continue
        ef = (r["avg_speed"] * 60) / r["avg_hr"]   # mètres/min par battement
        monthly.setdefault(r["activity_date"][:7], []).append(ef)

    months = sorted(monthly)[-6:]
    series = [{"month": m, "ef": round(st.mean(monthly[m]), 3), "n": len(monthly[m])} for m in months]

    trend = None
    verdict = "Pas encore assez de données."
    if len(series) >= 2:
        old = st.mean([s["ef"] for s in series[: max(1, len(series) // 2)]])
        new = st.mean([s["ef"] for s in series[-max(1, len(series) // 2):]])
        trend = round((new - old) / old * 100, 1)
        if trend >= 2:
            verdict = f"En progrès 📈 +{trend}% : tu vas plus vite à FC égale."
        elif trend <= -2:
            verdict = f"En baisse ({trend}%) : fatigue, météo chaude, ou manque de fraîcheur ?"
        else:
            verdict = "Stable : ton efficacité aérobie se maintient."
    return {"available": len(series) >= 2, "series": series, "trend": trend, "verdict": verdict}


# ------------------------------------------------------------- Prédictions

def _riegel(t_sec: float, d_m: float, target_m: float, exp: float = 1.06) -> float:
    return t_sec * (target_m / d_m) ** exp


def _fmt_t(sec: float | None) -> str:
    if not sec:
        return "—"
    s = int(round(sec))
    return f"{s // 3600}h{(s % 3600) // 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"


def predictions() -> dict:
    acts = db.recent_activities(400)
    today = date.today()
    runs = [a for a in acts if a["sport"] == "run" and a["avg_pace_s"] and (a["distance_m"] or 0) >= 5000]
    recent = [r for r in runs if date.fromisoformat(r["activity_date"]) >= today - timedelta(days=70)]
    pool = recent or runs
    best = min(pool, key=lambda r: r["avg_pace_s"]) if pool else None

    pred20 = _riegel(best["duration_s"], best["distance_m"], 20000) if best else None
    pred_half = _riegel(best["duration_s"], best["distance_m"], 21100) if best else None

    swims = [a for a in acts if a["sport"] == "swim" and a["avg_pace_s"]]
    rides = [a for a in acts if a["sport"] == "bike" and a["avg_speed"]]
    swim_pace = st.median([a["avg_pace_s"] for a in swims]) if swims else 120.0   # s/100m
    ride_speed = st.median([a["avg_speed"] for a in rides]) if rides else 7.4      # m/s

    tri = None
    if pred_half:
        swim_s = 1900 / 100 * swim_pace
        bike_s = 90000 / ride_speed
        run_s = pred_half * 1.08          # course du 70.3 plus lente (fatigue vélo)
        tri = swim_s + bike_s + run_s + 360   # +6 min transitions
        tri_parts = {"swim": _fmt_t(swim_s), "bike": _fmt_t(bike_s), "run": _fmt_t(run_s)}
    else:
        tri_parts = None

    return {
        "available": best is not None,
        "based_on": {"pace": f"{int(best['avg_pace_s']//60)}:{int(best['avg_pace_s']%60):02d}/km",
                     "km": round(best["distance_m"] / 1000, 1),
                     "date": best["activity_date"], "recent": bool(recent)} if best else None,
        "pred_20km": {"sec": pred20, "txt": _fmt_t(pred20)},
        "pred_half": {"sec": pred_half, "txt": _fmt_t(pred_half)},
        "pred_703": {"sec": tri, "txt": _fmt_t(tri), "parts": tri_parts},
    }


def state() -> dict:
    return {"form": form_state(), "efficiency": efficiency(), "predictions": predictions()}
