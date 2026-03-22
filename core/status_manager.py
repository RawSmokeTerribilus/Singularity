import json
import os
import shutil
import subprocess
import tempfile
import time
import fcntl
import random
from singularity_config import GOD_PHRASES
from rich import print as rprint
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
STATUS_FILE = BASE_DIR / "logs" / "current_status.json"


def _get_process_metrics(pid):
    try:
        result = subprocess.run(
            ["ps", "-p", str(pid), "-o", "%cpu,rss", "--no-headers"],
            capture_output=True, text=True, timeout=2
        )
        parts = result.stdout.strip().split()
        if len(parts) < 2:
            return None
        return {"cpu": f"{parts[0]}%", "ram": f"{round(int(parts[1]) / 1024, 1)} MB"}
    except Exception:
        return None


def clear_all_statuses():
    os.makedirs(STATUS_FILE.parent, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=STATUS_FILE.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write("{}")
        shutil.move(tmp_path, STATUS_FILE)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def update_status(module, task, status, progress=None, details=None):
    """Actualiza el estado global para el dashboard web con bloqueo de archivo."""
    os.makedirs(STATUS_FILE.parent, exist_ok=True)

    pid = os.getpid()
    key = f"{module}_{pid}"

    metrics = _get_process_metrics(pid)
    now = time.time()

    # --- INYECTOR DE TROLEO (Soberanía Operativa) ---
    # Si la tarea no es "ONLINE" o "SCANNING" (para no saturar en bucles rápidos)
    # tiramos un dado. Si sale un 2% (0.02), escupe la perla.
    if status in ["PROCESSING", "WORKING"] and random.random() < 0.02:
        rprint(f"[dim italic magenta]🤖 {random.choice(GOD_PHRASES)}[/dim italic magenta]")
    # ------------------------------------------------

    with open(STATUS_FILE, "a+", encoding="utf-8") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.seek(0)
            content = f.read()
            current_data = json.loads(content) if content else {}
        except Exception:
            current_data = {}

        existing = current_data.get(key, {})
        start_time = existing.get("start_time", now)

        entry = {
            "module": module,
            "pid": pid,
            "task": task,
            "status": status,
            "progress": progress,
            "details": details,
            "last_update": now,
            "start_time": start_time,
            "metrics": metrics,
        }

        if status in ("FINISHED", "COMPLETED", "ERROR"):
            entry["duration"] = now - start_time

        current_data[key] = entry

        f.seek(0)
        f.truncate()
        json.dump(current_data, f, indent=4, ensure_ascii=False)
        fcntl.flock(f, fcntl.LOCK_UN)


def clear_stale_statuses(max_age=600):
    """Cambia estados que no se han actualizado en X segundos a 'OFFLINE' sin eliminarlos."""
    if not STATUS_FILE.exists():
        return

    with open(STATUS_FILE, "a+", encoding="utf-8") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.seek(0)
            content = f.read()
            data = json.loads(content) if content else {}
        except Exception:
            fcntl.flock(f, fcntl.LOCK_UN)
            return

        now = time.time()
        modified = False
        to_delete = []

        for key, d in data.items():
            pid = d.get("pid")
            is_alive = False
            if pid:
                try:
                    os.kill(pid, 0)
                    is_alive = True
                except OSError:
                    is_alive = False

            if not is_alive:
                if (now - d.get("last_update", 0)) > (max_age * 2):
                    to_delete.append(key)
                elif d.get("status") != "OFFLINE" and d.get("status") != "FINISHED":
                    d["status"] = "OFFLINE"
                    modified = True
            elif (now - d.get("last_update", 0)) >= max_age:
                if d.get("status") != "OFFLINE" and d.get("status") != "FINISHED":
                    d["status"] = "OFFLINE"
                    modified = True

        for key in to_delete:
            del data[key]
            modified = True

        if modified:
            f.seek(0)
            f.truncate()
            json.dump(data, f, indent=4, ensure_ascii=False)

        fcntl.flock(f, fcntl.LOCK_UN)


def get_status():
    """Retorna el estado actual completo."""
    if STATUS_FILE.exists():
        try:
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}
