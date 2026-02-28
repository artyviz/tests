import os
import asyncio

import psutil
import httpx
import websockets
from fastapi import FastAPI, Request, Form, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, RedirectResponse, Response
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

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)

@app.get("/", response_class=HTMLResponse)
async def index():
    return RedirectResponse(url="/simulate", status_code=302)

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

@app.get("/analysis", response_class=HTMLResponse)
async def analysis_page(request: Request):
    return templates.TemplateResponse("analysis.html", {
        "request": request,
        "page": "analysis",
    })

@app.get("/api/system_metrics")
async def system_metrics():
    return {
        "cpu_percent": psutil.cpu_percent(interval=None),
        "memory_percent": psutil.virtual_memory().percent,
        "active_connections": len(psutil.net_connections(kind='inet')),
    }

@app.api_route("/proxy/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_api(request: Request, path: str):
    url = f"{API}/api/{path}"
    params = dict(request.query_params)
    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in ("host", "content-length", "transfer-encoding")
    }

    async with httpx.AsyncClient() as client:
        if request.method == "GET":
            resp = await client.get(url, params=params, headers=headers, timeout=15)
        else:
            body = await request.body()
            resp = await client.request(
                request.method, url, content=body, params=params,
                headers=headers, timeout=15,
            )

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type=resp.headers.get("content-type", "application/json"),
    )

@app.websocket("/ws/live")
async def websocket_proxy(ws: WebSocket):
    await ws.accept()
    rust_ws_url = API.replace("http://", "ws://").replace("https://", "wss://") + "/api/ws"

    try:
        async with websockets.connect(rust_ws_url) as upstream:
            async def forward():
                try:
                    async for msg in upstream:
                        await ws.send_text(msg)
                except Exception:
                    pass

            task = asyncio.create_task(forward())
            try:
                while True:
                    await ws.receive_text()
            except WebSocketDisconnect:
                pass
            finally:
                task.cancel()
    except Exception:
        try:
            await ws.close()
        except Exception:
            pass
