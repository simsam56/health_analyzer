"""Bord API — FastAPI server (remplace cockpit_server.py)."""

from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from datetime import date, timedelta
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse

from analytics import planner
from analytics.training_load import (
    build_daily_tss,
    compute_acwr,
    compute_pmc,
    compute_wakeboard_score,
    get_health_metrics,
    analyze_running,
)
from analytics.muscle_groups import (
    get_cumulative_volume,
    get_weekly_volume,
    analyze_imbalances,
)
from api import deps
from api.routes import activities, calendar, health, muscles, planner as planner_routes, training
from pipeline.schema import get_connection, migrate_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup : migration DB + config."""
    # Config depuis .env ou variables d'environnement
    db_path = Path(os.getenv("BORD_DB", "athlete.db"))
    dashboard_path = Path(os.getenv("BORD_DASHBOARD", "reports/dashboard.html"))
    api_token = os.getenv("BORD_API_TOKEN", "")

    deps.DB_PATH = db_path
    deps.DASHBOARD_PATH = dashboard_path
    deps.API_TOKEN = api_token

    # Migration DB au démarrage
    try:
        conn = get_connection(db_path)
        migrate_db(conn)
        conn.close()
        print(f"✅ DB migrée : {db_path}")
    except Exception as e:
        print(f"⚠️  Migration DB: {e}")

    print(f"🚀 Bord API démarrée")
    print(f"   DB: {db_path}")
    print(f"   Dashboard: {dashboard_path}")
    if api_token:
        print("   API write protection: enabled")

    yield


app = FastAPI(
    title="Bord API",
    description="API du tableau de bord personnel",
    version="4.0.0",
    lifespan=lifespan,
)

# CORS pour Next.js (port configurable via BORD_FRONTEND_PORT)
_frontend_port = os.getenv("BORD_FRONTEND_PORT", "3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"http://localhost:{_frontend_port}",
        f"http://127.0.0.1:{_frontend_port}",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enregistrer les routers
app.include_router(planner_routes.router)
app.include_router(calendar.router)
app.include_router(health.router)
app.include_router(training.router)
app.include_router(muscles.router)
app.include_router(activities.router)


# ── Ancien dashboard (backward-compat) ─────────────────────────────


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
@app.get("/index.html", response_class=HTMLResponse, include_in_schema=False)
@app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
def serve_dashboard():
    """Sert l'ancien dashboard HTML (backward-compat)."""
    path = deps.DASHBOARD_PATH
    if not path.exists():
        return HTMLResponse("<h1>Dashboard non généré</h1><p>Lancez main.py d'abord.</p>", status_code=404)
    raw = path.read_text("utf-8")
    if deps.API_TOKEN:
        token_js = json.dumps(deps.API_TOKEN, ensure_ascii=False)
        raw = raw.replace("__API_TOKEN_JS__", token_js)
    return HTMLResponse(raw)


# ── Endpoint agrégat /api/dashboard ────────────────────────────────


@app.get("/api/dashboard", tags=["dashboard"])
def dashboard_aggregate():
    """
    Agrégat complet : toutes les données pour le frontend en 1 requête.
    Remplace les 91 template variables de generator.py.
    """
    conn = deps.get_db()
    try:
        # Métriques santé
        metrics = get_health_metrics(conn)

        # PMC
        daily_tss = build_daily_tss(conn)
        pmc = compute_pmc(daily_tss)
        current_pmc = pmc[-1] if pmc else {}

        # ACWR
        acwr = compute_acwr(daily_tss)

        # Readiness
        freshness = {
            "hrv": metrics.get("hrv_freshness", 0),
            "sleep": metrics.get("sleep_freshness", 0),
            "rhr": metrics.get("rhr_freshness", 0),
            "body_battery": metrics.get("body_battery_freshness", 0),
        }
        readiness = compute_wakeboard_score(
            hrv_val=metrics.get("hrv"),
            hrv_baseline=metrics.get("hrv_baseline"),
            sleep_h=metrics.get("sleep_h"),
            acwr_val=acwr.get("acwr", 0),
            rhr_val=metrics.get("rhr"),
            rhr_baseline=metrics.get("rhr_baseline"),
            body_battery=metrics.get("body_battery"),
            freshness=freshness,
        )

        # Running
        running = analyze_running(conn, weeks=12)

        # Muscles
        muscle_cumul = get_cumulative_volume(conn, weeks=4)
        muscle_weekly = get_weekly_volume(conn, weeks=8)
        muscle_alerts = analyze_imbalances(muscle_cumul, weeks=4)

        # Heatmap zones
        max_sets = max(
            (v.get("sets_per_week", 0) for v in muscle_cumul.values()),
            default=1,
        ) or 1
        zones = {}
        for mg, data in muscle_cumul.items():
            spw = data.get("sets_per_week", 0)
            zones[mg] = round(min(1.0, max(0.05, spw / max_sets)) if spw > 0 else 0.05, 2)

        # Planner events (semaine courante ± marge)
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        events_start = (week_start - timedelta(days=7)).strftime("%Y-%m-%dT00:00:00")
        events_end = (week_start + timedelta(days=21)).strftime("%Y-%m-%dT23:59:59")
        events = planner.get_planner_events_db(deps.DB_PATH, start_at=events_start, end_at=events_end)

        # Résumé hebdo
        week_summary = planner.weekly_category_summary(events, week_start)

        # Board (kanban)
        board = planner.get_board_tasks_db(deps.DB_PATH)

        # Activités récentes
        recent = conn.execute(
            """
            SELECT id, source, type, name, started_at, duration_s, distance_m,
                   calories, avg_hr, tss_proxy
            FROM activities WHERE started_at IS NOT NULL
            ORDER BY started_at DESC LIMIT 10
            """,
        ).fetchall()
        recent_activities = [
            {
                "id": r[0], "source": r[1], "type": r[2], "name": r[3],
                "started_at": r[4], "duration_s": r[5], "distance_m": r[6],
                "calories": r[7], "avg_hr": r[8], "tss": round(r[9], 1) if r[9] else None,
            }
            for r in recent
        ]

        # PMC série (6 derniers mois)
        pmc_series = [
            {"date": d["date"], "ctl": round(d.get("ctl", 0), 1),
             "atl": round(d.get("atl", 0), 1), "tsb": round(d.get("tsb", 0), 1)}
            for d in pmc[-180:]
        ]

        # Heures hebdo (série temporelle)
        hours_series = [
            dict(r) for r in conn.execute(
                """
                SELECT strftime('%Y-W%W', started_at) AS week,
                       ROUND(SUM(COALESCE(duration_s,0))/3600.0, 2) AS hours
                FROM activities WHERE started_at IS NOT NULL
                GROUP BY week ORDER BY week DESC LIMIT 12
                """
            ).fetchall()
        ]
        hours_series.reverse()

        return {
            "ok": True,
            "health": metrics,
            "readiness": readiness,
            "acwr": acwr,
            "pmc": {
                "current": {
                    "ctl": current_pmc.get("ctl", 0),
                    "atl": current_pmc.get("atl", 0),
                    "tsb": current_pmc.get("tsb", 0),
                },
                "series": pmc_series,
            },
            "running": running,
            "muscles": {
                "zones": zones,
                "weekly_volume": muscle_weekly,
                "alerts": muscle_alerts,
            },
            "week": {
                "start": str(week_start),
                "summary": week_summary,
                "events": events,
                "board": board,
            },
            "activities": {
                "recent": recent_activities,
                "hours_series": hours_series,
            },
        }
    finally:
        conn.close()


# ── Lancement direct ───────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("BORD_PORT", "8765"))
    uvicorn.run(
        "api.main:app",
        host="127.0.0.1",
        port=port,
        reload=True,
    )
