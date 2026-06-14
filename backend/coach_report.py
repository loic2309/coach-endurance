"""Analyse 'coach' de l'historique Garmin : allures réelles, zones, charge, potentiel.

Usage :
    python -m backend.coach_report --sync     # synchronise puis analyse
    python -m backend.coach_report            # analyse les données déjà en base
"""
from __future__ import annotations

import json
import statistics as st
import sys
from datetime import date, datetime, timedelta

from . import db, garmin_sync
from .analytics import fmt_pace


def _runs(acts: list[dict], min_km: float = 3.0) -> list[dict]:
    out = []
    for a in acts:
        if a["sport"] != "run":
            continue
        if (a["distance_m"] or 0) < min_km * 1000:
            continue
        if not a["avg_pace_s"]:
            continue
        out.append(a)
    return out


def riegel(t_sec: float, d_m: float, target_m: float, exp: float = 1.06) -> float:
    """Projette un temps de course d'une distance vers une autre (formule de Riegel)."""
    return t_sec * (target_m / d_m) ** exp


def analyze() -> dict:
    acts = db.recent_activities(400)
    if not acts:
        return {"error": "Aucune activité en base. Lance avec --sync."}

    runs = _runs(acts)
    rides = [a for a in acts if a["sport"] == "bike" and a["avg_speed"]]
    swims = [a for a in acts if a["sport"] == "swim" and a["avg_pace_s"]]

    dates = [date.fromisoformat(a["activity_date"]) for a in acts]
    span = (max(dates) - min(dates)).days if len(dates) > 1 else 0

    # HR max estimé (max des FC max observées)
    hrmaxes = [a["raw"] and json.loads(a["raw"]).get("maxHR") for a in runs]
    hrmaxes = [h for h in hrmaxes if h]
    hrmax_est = max(hrmaxes) if hrmaxes else None

    # Classement facile / dur via FC
    easy, hard = [], []
    for r in runs:
        hr = r["avg_hr"]
        if hrmax_est and hr:
            (easy if hr < 0.80 * hrmax_est else hard).append(r)
    # fallback si pas de FC : moitié la plus lente = facile
    if not easy:
        srt = sorted(runs, key=lambda r: r["avg_pace_s"], reverse=True)
        easy = srt[: max(1, len(srt) // 2)]

    def med_pace(rs):
        return st.median([r["avg_pace_s"] for r in rs]) if rs else None

    easy_pace = med_pace(easy)
    all_pace = med_pace(runs)

    # Meilleur effort soutenu (≥6 km, allure la plus rapide)
    long_runs = [r for r in runs if (r["distance_m"] or 0) >= 6000]
    best = min(long_runs, key=lambda r: r["avg_pace_s"]) if long_runs else None

    # Plus longue sortie
    longest = max(runs, key=lambda r: r["distance_m"]) if runs else None

    # Charge récente (4 et 12 dernières semaines, en km course)
    today = date.today()
    def km_since(weeks):
        cut = today - timedelta(weeks=weeks)
        return sum((r["distance_m"] or 0) for r in runs
                   if date.fromisoformat(r["activity_date"]) >= cut) / 1000
    vol4 = km_since(4)
    vol12 = km_since(12)

    # Projection 20km depuis le meilleur effort long
    proj20 = None
    if best:
        proj20 = riegel(best["duration_s"], best["distance_m"], 20000)

    # Vélo / natation
    ride_speed = st.median([a["avg_speed"] * 3.6 for a in rides]) if rides else None
    swim_pace = st.median([a["avg_pace_s"] for a in swims]) if swims else None

    return {
        "counts": {"activities": len(acts), "runs": len(runs), "rides": len(rides),
                    "swims": len(swims), "span_days": span},
        "hrmax_est": hrmax_est,
        "easy_pace_s": easy_pace, "median_run_pace_s": all_pace,
        "n_easy": len(easy), "n_hard": len(hard),
        "best": best, "longest": longest,
        "vol4_km": round(vol4), "vol12_km": round(vol12),
        "vol_week_avg_km": round(vol12 / 12, 1),
        "proj20_s": proj20,
        "ride_speed_kmh": round(ride_speed, 1) if ride_speed else None,
        "swim_pace_s": swim_pace,
    }


def _fmt_t(sec):
    if not sec:
        return "—"
    s = int(round(sec)); return f"{s // 3600}h{(s % 3600) // 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"


def print_report(r: dict) -> None:
    if r.get("error"):
        print(r["error"]); return
    c = r["counts"]
    print("=" * 60)
    print(f"ANALYSE GARMIN — {c['activities']} activités sur {c['span_days']} j")
    print(f"  Course: {c['runs']} | Vélo: {c['rides']} | Natation: {c['swims']}")
    print(f"  FC max estimée: {r['hrmax_est'] or '—'} bpm")
    print("-" * 60)
    print("COURSE À PIED")
    print(f"  Allure facile (Z2 réelle): {fmt_pace(r['easy_pace_s'])}  [{r['n_easy']} sorties faciles]")
    print(f"  Allure médiane toutes sorties: {fmt_pace(r['median_run_pace_s'])}")
    if r["best"]:
        b = r["best"]
        print(f"  Meilleur effort long: {fmt_pace(b['avg_pace_s'])} sur {round(b['distance_m']/1000,1)} km "
              f"({_fmt_t(b['duration_s'])}) — {b['name']} {b['activity_date']}")
    if r["longest"]:
        lo = r["longest"]
        print(f"  Plus longue sortie: {round(lo['distance_m']/1000,1)} km en {_fmt_t(lo['duration_s'])}")
    print(f"  Volume: {r['vol4_km']} km / 4 sem · {r['vol12_km']} km / 12 sem (~{r['vol_week_avg_km']} km/sem)")
    if r["proj20_s"]:
        print(f"  → Projection 20km (Riegel): {_fmt_t(r['proj20_s'])} ({fmt_pace(r['proj20_s']/20)})")
    print("-" * 60)
    print(f"VÉLO  vitesse médiane: {r['ride_speed_kmh'] or '—'} km/h")
    print(f"NATATION  allure médiane: {fmt_pace(r['swim_pace_s']) if r['swim_pace_s'] else '—'} /100m"
          if r['swim_pace_s'] else "NATATION  —")
    print("=" * 60)


def save_measured(r: dict) -> None:
    """Persiste les repères mesurés pour que le moteur d'allures s'y appuie."""
    if r.get("error"):
        return
    if r.get("easy_pace_s"):
        db.set_meta("measured_easy_s", str(round(r["easy_pace_s"], 1)))
    if r.get("proj20_s"):
        db.set_meta("measured_thr_s", str(round(r["proj20_s"] / 20, 1)))
    if r.get("vol_week_avg_km") is not None:
        db.set_meta("vol_week_avg_km", str(r["vol_week_avg_km"]))
    db.set_meta("analyzed_at", datetime.now().isoformat(timespec="seconds"))


if __name__ == "__main__":
    db.init_db()
    if "--sync" in sys.argv:
        print("Synchronisation Garmin (12 mois)…")
        res = garmin_sync.sync(days_back=420, limit=300)
        print(f"  {res['imported']} activités importées sur {res['fetched']} récupérées.")
    report = analyze()
    save_measured(report)
    print_report(report)
