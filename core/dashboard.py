import os
import time
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import json

from .status_manager import get_status

app = FastAPI(title="Singularity Core Dashboard")

BASE_DIR = Path(__file__).parent.parent
templates_dir = BASE_DIR / "core" / "templates"
os.makedirs(templates_dir, exist_ok=True)

templates = Jinja2Templates(directory=str(templates_dir))

# Crear el template básico si no existe
TEMPLATE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Singularity Core Dashboard</title>
    <meta http-equiv="refresh" content="5">
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #121212; color: #e0e0e0; padding: 20px; }
        .card { background: #1e1e1e; border-radius: 8px; padding: 15px; margin-bottom: 20px; border-left: 5px solid #00bcd4; }
        .module-name { font-size: 1.2em; font-weight: bold; color: #00bcd4; margin-bottom: 10px; }
        .status-ok { color: #4caf50; }
        .status-warn { color: #ff9800; }
        .status-error { color: #f44336; }
        .progress-container { width: 100%; background-color: #333; border-radius: 5px; margin: 10px 0; }
        .progress-bar { height: 10px; background-color: #00bcd4; border-radius: 5px; transition: width 0.3s; }
        .details { font-size: 0.9em; color: #aaa; margin-top: 10px; }
        h1 { color: #fff; text-align: center; border-bottom: 1px solid #333; padding-bottom: 10px; }
    </style>
</head>
<body>
    <h1>⚡ SINGULARITY CORE — DASHBOARD ⚡</h1>
    <div id="modules">
        {% for module, data in status.items() %}
        <div class="card">
            <div class="module-name">{{ module | upper }}</div>
            <div><strong>Tarea:</strong> {{ data.task }}</div>
            <div><strong>Estado:</strong> {{ data.status }}</div>
            {% if data.progress is not none %}
            <div class="progress-container">
                <div class="progress-bar" style="width: {{ data.progress }}%;"></div>
            </div>
            <div>{{ data.progress }}%</div>
            {% endif %}
            {% if data.details %}
            <div class="details">{{ data.details }}</div>
            {% endif %}
            <div class="details" style="font-size: 0.7em; margin-top: 5px;">
                Última actualización: {{ (now - data.last_update) | int }}s ago
            </div>
        </div>
        {% endfor %}
    </div>
</body>
</html>
"""

index_path = templates_dir / "index.html"
if not index_path.exists():
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(TEMPLATE_HTML)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    status_data = get_status()
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "status": status_data,
        "now": time.time()
    })

@app.get("/api/status")
async def api_status():
    return get_status()

def run_dashboard():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002, log_level="warning")
