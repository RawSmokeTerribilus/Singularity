import os
import time
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import json

from .status_manager import get_status, clear_stale_statuses

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
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0a0a0a; color: #e0e0e0; padding: 20px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .card { background: #1a1a1a; border-radius: 12px; padding: 20px; border-top: 4px solid #444; box-shadow: 0 4px 15px rgba(0,0,0,0.5); transition: transform 0.2s; }
        .card:hover { transform: translateY(-5px); }
        .module-name { font-size: 1.1em; font-weight: 800; margin-bottom: 15px; display: flex; align-items: center; justify-content: space-between; }
        
        /* Module Colors */
        .card-core { border-top-color: #00bcd4; }
        .card-mkverything { border-top-color: #4caf50; }
        .card-rawloadrr { border-top-color: #e91e63; }
        .card-unit3d { border-top-color: #ffc107; }
        
        .label { color: #888; font-size: 0.85em; text-transform: uppercase; letter-spacing: 1px; margin-top: 10px; }
        .value { color: #fff; font-weight: 500; margin-bottom: 8px; }
        
        .progress-container { width: 100%; background-color: #333; border-radius: 10px; margin: 10px 0; height: 12px; overflow: hidden; }
        .progress-bar { height: 100%; background: linear-gradient(90deg, #00bcd4, #00acc1); border-radius: 10px; transition: width 0.5s ease-in-out; }
        
        .details { font-size: 0.85em; color: #999; background: #222; padding: 8px; border-radius: 6px; margin-top: 15px; border-left: 3px solid #444; font-family: monospace; word-break: break-all; }
        .last-update { font-size: 0.7em; color: #666; text-align: right; margin-top: 15px; }
        
        h1 { color: #fff; text-align: center; font-weight: 900; letter-spacing: 4px; margin-bottom: 40px; text-shadow: 0 0 10px rgba(0,188,212,0.3); }
        .status-badge { font-size: 0.7em; padding: 3px 8px; border-radius: 4px; font-weight: bold; background: #333; text-transform: uppercase; }
        .status-online { color: #4caf50; border: 1px solid #4caf50; }
        .status-processing { color: #00bcd4; border: 1px solid #00bcd4; }
        .status-error { color: #f44336; border: 1px solid #f44336; }
        .status-completed { color: #4caf50; border: 1px solid #4caf50; }
    </style>
</head>
<body>
    <h1>⚡ SINGULARITY CORE ⚡</h1>
    <div class="grid">
        {% for key, data in status.items() %}
        <div class="card card-{{ (data.module if data.module else key) | lower }}">
            <div class="module-name">
                <span>{{ (data.module if data.module else key) | upper }} {% if data.pid %}<span style="font-size: 0.6em; color: #888;">(PID: {{ data.pid }})</span>{% endif %}</span>
                <span class="status-badge status-{{ data.status | lower }}">{{ data.status }}</span>
            </div>
            
            <div class="label">Tarea</div>
            <div class="value">{{ data.task }}</div>

            {% if data.progress is not none %}
            <div class="label">Progreso</div>
            <div class="progress-container">
                <div class="progress-bar" style="width: {{ data.progress }}%;"></div>
            </div>
            <div style="font-weight: bold; color: #00bcd4; font-size: 0.9em;">{{ data.progress }}%</div>
            {% endif %}

            {% if data.details %}
            <div class="details">{{ data.details }}</div>
            {% endif %}

            <div class="last-update">
                Actualizado hace {{ (now - data.last_update) | int }}s
            </div>
        </div>
        {% endfor %}
    </div>
</body>
</html>
"""

index_path = templates_dir / "index.html"
with open(index_path, "w", encoding="utf-8") as f:
    f.write(TEMPLATE_HTML)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    clear_stale_statuses() # Limpiar procesos inactivos
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

if __name__ == "__main__":
    run_dashboard()
