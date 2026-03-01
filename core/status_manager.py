import json
import os
import time
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
STATUS_FILE = BASE_DIR / "logs" / "current_status.json"

def update_status(module, task, status, progress=None, details=None):
    """Actualiza el estado global para el dashboard web."""
    os.makedirs(STATUS_FILE.parent, exist_ok=True)
    
    current_data = {}
    if STATUS_FILE.exists():
        try:
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                current_data = json.load(f)
        except:
            current_data = {}

    current_data[module] = {
        "task": task,
        "status": status,
        "progress": progress,
        "details": details,
        "last_update": time.time()
    }
    
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(current_data, f, indent=4, ensure_ascii=False)

def get_status():
    """Retorna el estado actual completo."""
    if STATUS_FILE.exists():
        try:
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}
