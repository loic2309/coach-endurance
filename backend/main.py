"""Application FastAPI : API de coaching + service du dashboard."""
from __future__ import annotations

import secrets
from datetime import date
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import analytics, coaching, db, fitness, gamification, garmin_sync, plan_engine, week_review
from .config import settings

app = FastAPI(title="Coach Endurance — 20km & 70.3")

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"


@app.on_event("startup")
def _startup() -> None:
    db.init_db()


@app.middleware("http")
async def basic_auth(request: Request, call_next):
    """Auth HTTP basique, activée uniquement si APP_PASSWORD est défini (déploiement public)."""
    if settings.app_password:
        header = request.headers.get("authorization", "")
        ok = False
        if header.startswith("Basic "):
            import base64
            try:
                user, _, pwd = base64.b64decode(header[6:]).decode().partition(":")
                ok = secrets.compare_digest(user, settings.app_user) and \
                     secrets.compare_digest(pwd, settings.app_password)
            except Exception:
                ok = False
        if not ok:
            return Response("Auth requise", status_code=401,
                            headers={"WWW-Authenticate": 'Basic realm="Coach Endurance"'})
    return await call_next(request)


# ---------------------------------------------------------------- API

@app.get("/api/overview")
def overview():
    return {
        "goals": analytics.goal_summary(),
        "paces": analytics.target_paces(),
        "garmin": garmin_sync.status(),
        "best_efforts": analytics.best_efforts(),
        "plan_progress": analytics.plan_progress(),
    }


@app.get("/api/coaching")
def coaching_content():
    return coaching.coaching_payload()


@app.get("/api/gamification")
def gamification_state():
    return gamification.state()


@app.get("/api/progression")
def progression_state():
    return fitness.state()


@app.get("/api/week-activities")
def week_activities_state():
    return week_review.week_activities()


@app.get("/api/plan")
def plan():
    return {"phases": [p.__dict__ for p in plan_engine.PHASES], "weeks": plan_engine.full_plan()}


@app.get("/api/week")
def week(d: Optional[str] = None):
    ref = date.fromisoformat(d) if d else date.today()
    wk = plan_engine.week_containing(ref)
    mon = wk["days"][0]["date"]
    sun = wk["days"][-1]["date"]
    statuses = db.session_statuses(mon, sun)
    for day in wk["days"]:
        for s in day["sessions"]:
            s["status"] = statuses.get(f"{day['date']}::{s['slug']}", "planned")
    return wk


@app.get("/api/load")
def load(weeks: int = 12):
    return {"weekly": analytics.weekly_load(weeks)}


@app.get("/api/activities")
def activities(limit: int = 40):
    return {"activities": db.recent_activities(limit)}


class StatusIn(BaseModel):
    plan_date: str
    slug: str
    status: str  # done / skipped / planned
    note: Optional[str] = None


@app.post("/api/session-status")
def session_status(body: StatusIn):
    if body.status not in ("done", "skipped", "planned"):
        raise HTTPException(400, "status invalide")
    db.set_session_status(body.plan_date, body.slug, body.status, body.note)
    return {"ok": True}


@app.post("/api/sync")
def sync(days_back: int = 120):
    try:
        return garmin_sync.sync(days_back=days_back)
    except garmin_sync.GarminError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


# ---------------------------------------------------------------- Frontend

if FRONTEND.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND)), name="static")


@app.get("/")
def index():
    idx = FRONTEND / "index.html"
    if idx.exists():
        return FileResponse(str(idx))
    return JSONResponse({"msg": "Frontend non trouvé. Lance depuis la racine du projet."})
