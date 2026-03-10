import json
import os
import time
import fcntl
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
STATUS_FILE = BASE_DIR / "logs" / "current_status.json"

def update_status(module, task, status, progress=None, details=None):
    """Actualiza el estado global para el dashboard web con bloqueo de archivo."""
    os.makedirs(STATUS_FILE.parent, exist_ok=True)
    
    pid = os.getpid()
    key = f"{module}_{pid}"
    
    # Abrir archivo con bloqueo para evitar colisiones entre procesos
    with open(STATUS_FILE, "a+", encoding="utf-8") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.seek(0)
            content = f.read()
            current_data = json.loads(content) if content else {}
        except:
            current_data = {}

        current_data[key] = {
            "module": module,
            "pid": pid,
            "task": task,
            "status": status,
            "progress": progress,
            "details": details,
            "last_update": time.time()
        }
        
        f.seek(0)
        f.truncate()
        json.dump(current_data, f, indent=4, ensure_ascii=False)
        fcntl.flock(f, fcntl.LOCK_UN)

def clear_stale_statuses(max_age=600):
    """Elimina estados que no se han actualizado en X segundos con bloqueo."""
    if not STATUS_FILE.exists():
        return
    
    with open(STATUS_FILE, "a+", encoding="utf-8") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.seek(0)
            content = f.read()
            data = json.loads(content) if content else {}
        except:
            fcntl.flock(f, fcntl.LOCK_UN)
            return

        now = time.time()
        new_data = {m: d for m, d in data.items() if (now - d.get("last_update", 0)) < max_age}
        
        if len(new_data) != len(data):
            f.seek(0)
            f.truncate()
            json.dump(new_data, f, indent=4, ensure_ascii=False)
        
        fcntl.flock(f, fcntl.LOCK_UN)

def get_status():
    """Retorna el estado actual completo."""
    if STATUS_FILE.exists():
        try:
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}
