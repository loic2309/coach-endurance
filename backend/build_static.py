"""Génère une page HTML autonome (docs/index.html) pour GitHub Pages / usage hors-ligne.

Embarque un instantané des données (objectifs, allures, plan complet, charge, conseils,
gamification) dans le HTML. La page fonctionne alors SANS backend : le suivi des séances
passe par le localStorage du navigateur, et la synchro Garmin est désactivée.

Usage :  python -m backend.build_static
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from . import analytics, coaching, fitness, gamification, garmin_sync, plan_engine, db
from .config import ROOT


def build_data() -> dict:
    db.init_db()
    return {
        "built_at": datetime.now().isoformat(timespec="seconds"),
        "overview": {
            "goals": analytics.goal_summary(),
            "paces": analytics.target_paces(),
            "garmin": garmin_sync.status(),
            "best_efforts": analytics.best_efforts(),
            "plan_progress": analytics.plan_progress(),
        },
        "coaching": coaching.coaching_payload(),
        "gamification": gamification.state(),
        "progression": fitness.state(),
        "load": {"weekly": analytics.weekly_load(12)},
        "weeks": plan_engine.full_plan(),
    }


def build() -> Path:
    front = ROOT / "frontend"
    html = (front / "index.html").read_text(encoding="utf-8")
    css = (front / "styles.css").read_text(encoding="utf-8")
    js = (front / "app.js").read_text(encoding="utf-8")

    data = build_data()
    # sécurise l'insertion dans <script> (évite une fin de balise prématurée)
    data_js = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")

    html = html.replace(
        '<link rel="stylesheet" href="/static/styles.css" />',
        f"<style>\n{css}\n</style>",
    )
    html = html.replace(
        '<script src="/static/app.js"></script>',
        f"<script>window.__COACH_DATA__ = {data_js};</script>\n  <script>\n{js}\n</script>",
    )

    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)
    (docs / ".nojekyll").write_text("", encoding="utf-8")
    out = docs / "index.html"
    out.write_text(html, encoding="utf-8")
    return out


if __name__ == "__main__":
    out = build()
    size_kb = out.stat().st_size / 1024
    print(f"✅ Page statique générée : {out}  ({size_kb:.0f} Ko)")
