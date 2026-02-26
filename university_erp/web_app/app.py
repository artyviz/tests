"""
University ERP — FastAPI Web Frontend

Server-rendered Jinja2 templates that proxy to the Rust API.
This layer NEVER touches the database directly.
"""

import os
import psutil

import httpx
from fastapi import FastAPI, Request, Form, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="University ERP", docs_url=None, redoc_url=None)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

API = os.environ.get("RUST_API_URL", "http://localhost:3000")

async def api_post(path: str, data: dict):
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{API}{path}", json=data, timeout=10)
        return r.json(), r.status_code

@app.get("/", response_class=HTMLResponse)
async def index():
    return RedirectResponse(url="/simulate", status_code=302)

# ── Simluation & Terminal Feed ───────────────────────
@app.get("/simulate", response_class=HTMLResponse)
async def simulate_page(request: Request):
    return templates.TemplateResponse("simulate.html", {
        "request": request,
        "page": "simulate",
    })

@app.post("/simulate/start")
async def simulate_start(request: Request, count: int = Form(...)):
    await api_post("/api/simulate", {"count": count})
    return RedirectResponse(url="/simulate", status_code=303)

# ── Analysis & System Metrics ────────────────────────
@app.get("/analysis", response_class=HTMLResponse)
async def analysis_page(request: Request):
    return templates.TemplateResponse("analysis.html", {
        "request": request,
        "page": "analysis",
    })

@app.get("/api/system_metrics")
async def system_metrics():
    # Return mock/actual host metrics to chart
    return {
        "cpu_percent": psutil.cpu_percent(interval=None),
        "memory_percent": psutil.virtual_memory().percent,
        "active_connections": len(psutil.net_connections(kind='inet')),
    }
