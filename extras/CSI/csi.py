import os
import sys
from typing import Optional
import re
import time
import random
import shutil
import subprocess
import logging
import importlib.util
import json
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv, set_key
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.align import Align
import requests
from bs4 import BeautifulSoup, element as bs4_element

try:
    import qbittorrentapi
except ImportError:
    qbittorrentapi = None

# CSI Integration
CSI_DIR  = Path(__file__).resolve().parent
BASE_DIR = CSI_DIR.parent.parent
sys.path.append(str(BASE_DIR))

try:
    from core.status_manager import update_status
except ImportError:
    def update_status(*args, **kwargs): pass

# ─── PATHS ────────────────────────────────────────────────────────────────────
ENV_PATH = BASE_DIR / ".env"
BACKUP_LOG  = CSI_DIR / "backups.log"

# CSI v1.6.5: Environment-Aware Paths & Persistent Reporting Restructuring
DOCKER_REPORTS_PATH = "/app/work_data/reports/csi_reports"
HOST_REPORTS_DIR    = "./work_data/reports/csi_reports"

def get_reports_path():
    """Detect between Docker and Host report paths."""
    if os.path.exists(HOST_REPORTS_DIR):
        return Path(HOST_REPORTS_DIR)
    return Path(DOCKER_REPORTS_PATH)

REPORTS_DIR = get_reports_path()
LOGS_DIR    = REPORTS_DIR / "logs" # v1.6.5: Moved to mapped volume for host access

# ─── LIVE REPORTING ───────────────────────────────────────────────────────────
class LiveReport:
    """CSI v1.6.5: Handle real-time report generation to mapped volumes."""
    def __init__(self, subcat: str, config: dict):
        self.subcat = subcat
        self.config = config
        self.files  = {}
        self.seen   = {}
        self.paths  = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def add(self, category: str, codec: str, path: str):
        c_up = category.upper()
        o_up = codec.upper()
        key = (c_up, o_up)
        
        if key not in self.files:
            p = get_report_path(c_up, o_up, self.subcat)
            self.files[key] = open(p, "w", encoding="utf-8")
            self.seen[key]  = set()
            self.paths.append(p)
            
            # Log the host path immediately so the user can see it's live
            relative = p.relative_to(REPORTS_DIR)
            dbg(f"[LIVE] Report initialized: {HOST_REPORTS_DIR}/{relative}")

        if path not in self.seen[key]:
            self.seen[key].add(path)
            f = self.files[key]
            f.write(path + "\n")
            f.flush()

    def close(self):
        for f in self.files.values():
            if not f.closed:
                f.close()
        self.files.clear()
        return self.paths

DOCKER_TMP_PATH = "/app/RawLoadrr/tmp"
HOST_TMP_PATH   = "./work_data/tmp"

def get_tmp_path():
    """Auto-detect between Docker and Host paths."""
    if os.path.exists(HOST_TMP_PATH):
        return Path(HOST_TMP_PATH)
    return Path(DOCKER_TMP_PATH)

TMP_ROOT = get_tmp_path()

# CSI v2.0: Ruta de persistencia del TrackerIndex entre sesiones
# Almacenado en REPORTS_DIR (ya mapeado a volumen en Docker, accesible desde host)
TRACKER_INDEX_PATH = REPORTS_DIR / "tracker_index.json"

# ─── LOGGING & INIT ──────────────────────────────────────────────────────────
console = Console()
DEBUG_MODE = False

# --- TROLLING SUBSYSTEM INJECTION ---
try:
    from singularity_config import GOD_PHRASES
except ImportError:
    GOD_PHRASES = []

if GOD_PHRASES:
    _original_console_print = console.print

    def troll_print(*args, **kwargs):
        # REGLA DE ORO: El log técnico SIEMPRE se imprime primero, íntegro e intocable.
        # El troleo es un addendum con probabilidad del 7%, NUNCA un sustituto.
        # Ningún path, ID, estado de match o dato crítico puede ser ocultado por el troleo.
        _original_console_print(*args, **kwargs)
        # Solo DESPUÉS del log real, y solo a veces, se infiltra una frase de amenidad.
        if random.random() < 0.07:  # 7% de probabilidad — addendum, jamás reemplazo
            phrase = random.choice(GOD_PHRASES)
            _original_console_print(f"[dim italic magenta]« {phrase} »[/dim italic magenta]")

    console.print = troll_print  # type: ignore[method-assign]
# ------------------------------------

_env_backup_done = False
_initialized = False
_fh = None

logger = logging.getLogger("CSI")
logger.setLevel(logging.DEBUG)

def _ensure_initialized():
    """Lazy initialization of directories and logging to avoid import side-effects."""
    global _initialized, _fh
    if _initialized:
        return
    
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # v1.6.5 Clean up: Standardized folders only
    for _case in ("local_cases", "user_cases", "global_cases"):
        for _sub in ("movies", "tv_shows"):
            (REPORTS_DIR / _case / _sub).mkdir(parents=True, exist_ok=True)

    # Logging setup
    _log_file = LOGS_DIR / f"csi_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    _fh = logging.FileHandler(_log_file, encoding="utf-8")
    _fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(_fh)
    
    _initialized = True

def dbg(msg: str):
    logger.debug(msg)
    if DEBUG_MODE:
        console.print(f"[dim cyan]DBG: {msg}[/dim cyan]")

def toggle_debug(force_state=None):
    global DEBUG_MODE, _fh
    if force_state is not None:
        DEBUG_MODE = force_state
    else:
        DEBUG_MODE = not DEBUG_MODE
    
    # Refresh handlers
    logger.handlers = [h for h in logger.handlers if not isinstance(h, logging.StreamHandler)]
    if _fh:
        logger.addHandler(_fh) # Always keep file handler if initialized
    
    if DEBUG_MODE:
        _sh = logging.StreamHandler(sys.stdout)
        _sh.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        logger.addHandler(_sh)
        if force_state is None:
            console.print("[bold green]Debug Mode ON[/bold green]")
    else:
        if force_state is None:
            console.print("[bold yellow]Debug Mode OFF[/bold yellow]")

# ─── ASCII ART ────────────────────────────────────────────────────────────────
DETECTIVE_ART = (
    "[bold cyan]"
    "╔============================================╗\n"
    "||                                          ||\n"
    "||                                          ||\n"
    "||       ██████╗    ███████╗    ██╗         ||\n"
    "||      ██╔════╝    ██╔════╝    ██║         ||\n"
    "||      ██║         ███████╗    ██║         ||\n"
    "||      ██║         ╚════██║    ██║         ||\n"
    "||      ╚██████╗    ███████║    ██║         ||\n"
    "||       ╚═════╝    ╚══════╝    ╚═╝         ||\n"
    "||                                          ||\n"
    "||   ████████╗   ████████╗█████████████╗    ||\n"
    "||  ██╔════╚██╗ ██╔██╔══████╔════██╔══██╗   ||\n"
    "||  ██║     ╚████╔╝██████╔█████╗ ██████╔╝   ||\n"
    "||  ██║      ╚██╔╝ ██╔══████╔══╝ ██╔══██╗   ||\n"
    "||  ╚██████╗  ██║  ██████╔█████████║  ██║   ||\n"
    "||   ╚═════╝  ╚═╝  ╚═════╝╚══════╚═╝  ╚═╝   ||\n"
    "||                                          ||\n"
    "||                                          ||\n"
    "╚============================================╝\n"
    "[/bold cyan]"
)

# ─── STATE MACHINE — MÁQUINA DE ESTADOS CSI v2.0 ─────────────────────────────
# Cinco estados posibles por cada ítem de la biblioteca.
# La máquina de estados es la fuente de verdad del diagnóstico.
# PROHIBIDO usar True/False para representar el resultado de una triangulación.
#
# Jerarquía de Autoridades (orden estricto):
#   1. Tracker API / Scraper  → fuente de verdad principal
#   2. qBittorrent (Client)   → confirma si se está seeding
#   3. Disco local            → confirma existencia física
#   4. Cache/tmp/JSON         → historial suplementario, NUNCA fuente única

ESTADO_OK             = "ESTADO_OK"             # Verde   — En Tracker + en Cliente
ESTADO_DUPE_POTENCIAL = "ESTADO_DUPE_POTENCIAL"  # Amarillo— Mismo TMDB, diferente ICU
ESTADO_FALTA_CLIENTE  = "ESTADO_FALTA_CLIENTE"   # Naranja — En Tracker, sin seedear
ESTADO_NO_SUBIDO      = "ESTADO_NO_SUBIDO"       # Rojo    — No encontrado en Tracker
ESTADO_INCIDENCIA     = "ESTADO_INCIDENCIA"      # Gris    — Error de sonda / fallo conexión

# Colores Rich asociados a cada estado
STATE_COLORS = {
    ESTADO_OK:             "green",
    ESTADO_DUPE_POTENCIAL: "yellow",
    ESTADO_FALTA_CLIENTE:  "dark_orange",
    ESTADO_NO_SUBIDO:      "red",
    ESTADO_INCIDENCIA:     "dim white",
}

# Etiquetas descriptivas para output al usuario
STATE_LABELS = {
    ESTADO_OK:             "✓  OK              — Subido y seedeando",
    ESTADO_DUPE_POTENCIAL: "⚠  DUPE POTENCIAL  — Misma película, diferente versión",
    ESTADO_FALTA_CLIENTE:  "●  FALTA CLIENTE   — En tracker, no en qBittorrent",
    ESTADO_NO_SUBIDO:      "✗  NO SUBIDO       — Candidato a upload",
    ESTADO_INCIDENCIA:     "?  INCIDENCIA      — Error de sonda, no se pudo verificar",
}

# ─── SECURITY & RATE LIMITER ──────────────────────────────────────────────────
USER_AGENTS = [
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0",
]

class RateLimiter:
    def __init__(self, calls_per_min: int = 28):
        self.interval = 60.0 / calls_per_min
        self.last_call = 0.0

    def wait(self):
        elapsed = time.time() - self.last_call
        if elapsed < self.interval:
            sleep_for = self.interval - elapsed + random.uniform(0.1, 0.6)
            dbg(f"Rate limit: sleeping {sleep_for:.2f}s")
            time.sleep(sleep_for)
        self.last_call = time.time()

api_limiter = RateLimiter(28)

def _headers(config: Optional[dict] = None) -> dict:
    ua = "undici"
    if config and config.get("CUSTOM_USER_AGENT"):
        ua = config["CUSTOM_USER_AGENT"]
    
    return {
        "User-Agent":      ua,
        "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3",
        "DNT":             "1",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
    }

def _session(config: dict) -> requests.Session:
    s = requests.Session()
    s.headers.update(_headers(config))
    
    # Add tracker cookie if available
    c_name = config.get("TRACKER_COOKIE_NAME")
    c_val  = config.get("TRACKER_COOKIE") or config.get("TRACKER_COOKIE_VALUE")
    
    if c_name and c_val:
        s.cookies.set(c_name, c_val)
    elif c_val:
        # Fallback if name is not explicitly set, try common names
        s.cookies.set("nuclear_order_bit_syndicate_session", c_val)
        
    if config.get("USE_TOR"):
        s.proxies = {
            "http":  "socks5h://127.0.0.1:9050",
            "https": "socks5h://127.0.0.1:9050",
        }
    return s

# ─── RAWLOADRR CONFIG READER ──────────────────────────────────────────────────
def _load_rl_config() -> dict:
    path = BASE_DIR / "RawLoadrr" / "data" / "config.py"
    try:
        spec = importlib.util.spec_from_file_location("rl_config", path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load spec from {path}")
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.config
    except Exception as e:
        dbg(f"Could not load RawLoadrr config: {e}")
        return {}

def _update_python_var(file_path: Path, var_name: str, new_value: str):
    """Actualiza una variable 'VAR = "VAL"' en un archivo Python preservando estructura."""
    if not file_path.exists(): return
    try:
        content = file_path.read_text(encoding="utf-8")
        # Regex que busca VAR = "..." o VAR = '...' al inicio de línea o tras espacio
        pattern = r'^(\s*' + re.escape(var_name) + r'\s*=\s*)(["\'])(?:(?=(\\?))\3.)*?\2'
        if re.search(pattern, content, re.MULTILINE):
            # Reemplazar manteniendo la indentación y la variable, cambiando solo el valor entre comillas
            # Se usa re.sub con una función o string formateado con cuidado
            new_content = re.sub(
                pattern,
                lambda m: f'{m.group(1)}{m.group(2)}{new_value}{m.group(2)}',
                content,
                flags=re.MULTILINE
            )
            if new_content != content:
                file_path.write_text(new_content, encoding="utf-8")
                dbg(f"Updated {var_name} in {file_path.name}")
    except Exception as e:
        dbg(f"Error updating {var_name} in {file_path}: {e}")

def _propagate_config(updates: dict):
    """Distribuye la configuración a RawLoadrr, Mass-Edition y Singularity."""
    # Rutas probables
    rl_conf = BASE_DIR / "RawLoadrr" / "data" / "config.py"
    mass_conf = BASE_DIR / "config" / "mass_config.py"
    sing_conf = BASE_DIR / "config" / "singularity_config.py"
    
    # 1. RawLoadrr Config (Dict structure)
    if rl_conf.exists() and "TMDB_API_KEY" in updates:
        try:
            c = rl_conf.read_text(encoding="utf-8")
            # Actualizar tmdb_api en bloque DEFAULT
            c = re.sub(r'("tmdb_api"\s*:\s*")([^"]*)(")', r'\1' + updates["TMDB_API_KEY"] + r'\3', c)
            rl_conf.write_text(c, encoding="utf-8")
            dbg("Propagated TMDB to RawLoadrr config")
        except Exception as e:
            dbg(f"Failed to update RawLoadrr TMDB: {e}")

    if rl_conf.exists() and "ANNOUNCE_URL" in updates and "TRACKER_DEFAULT" in updates:
        # Intento de actualizar announce_url para el tracker específico (búsqueda simple)
        # Esto es heurístico, asume estructura estándar de RawLoadrr
        t_name = updates["TRACKER_DEFAULT"]
        announce = updates["ANNOUNCE_URL"]
        try:
            c = rl_conf.read_text(encoding="utf-8")
            # Busca bloque del tracker y su announce_url
            # Patrón: "TRACKER": { ... "announce_url": "OLD", ... }
            # Usamos un patrón simplificado que busca la clave del tracker y luego el primer announce_url que le sigue
            pat = r'("' + re.escape(t_name) + r'"\s*:\s*\{[^}]*?"announce_url"\s*:\s*")([^"]*)(")'
            if re.search(pat, c, re.DOTALL):
                c = re.sub(pat, r'\1' + announce + r'\3', c, flags=re.DOTALL)
                rl_conf.write_text(c, encoding="utf-8")
                dbg(f"Propagated Announce URL for {t_name} to RawLoadrr")
        except Exception as e:
            dbg(f"Failed to update RawLoadrr Announce: {e}")

    # 2. Mass Config (Variables globales)
    if mass_conf.exists():
        if "TRACKER_URL" in updates: _update_python_var(mass_conf, "BASE_URL", updates["TRACKER_URL"])
        if "TRACKER_USERNAME" in updates: _update_python_var(mass_conf, "USERNAME", updates["TRACKER_USERNAME"])
        if "TRACKER_COOKIE_VALUE" in updates: _update_python_var(mass_conf, "COOKIE_VALUE", updates["TRACKER_COOKIE_VALUE"])

    # 3. Singularity Config (Variables globales)
    if sing_conf.exists():
        if "TRACKER_URL" in updates: _update_python_var(sing_conf, "BASE_URL", updates["TRACKER_URL"])
        if "TRACKER_COOKIE_VALUE" in updates: _update_python_var(sing_conf, "COOKIE_VALUE", updates["TRACKER_COOKIE_VALUE"])
        if "SONARR_URL" in updates: _update_python_var(sing_conf, "SONARR_URL", updates["SONARR_URL"])
        if "SONARR_API_KEY" in updates: _update_python_var(sing_conf, "SONARR_API_KEY", updates["SONARR_API_KEY"])
        if "RADARR_URL" in updates: _update_python_var(sing_conf, "RADARR_URL", updates["RADARR_URL"])
        if "RADARR_API_KEY" in updates: _update_python_var(sing_conf, "RADARR_API_KEY", updates["RADARR_API_KEY"])

def _rl_tracker_info(rl_cfg: dict, tracker_name: str):
    """Return (api_key, base_url) for tracker_name from RawLoadrr config."""
    if not tracker_name:
        return None, None
    t = rl_cfg.get("TRACKERS", {}).get(tracker_name.upper(), {})
    api_key = t.get("api_key", "")
    if not api_key or api_key.endswith("_API_KEY") or api_key.endswith("_key"):
        api_key = None
    announce = t.get("announce_url", "")
    base_url = None
    if announce:
        m = re.match(r"(https?://[^/]+)", announce)
        if m:
            base_url = m.group(1)
    return api_key, base_url

# ─── CONFIG ───────────────────────────────────────────────────────────────────
def load_config() -> dict:
    load_dotenv(ENV_PATH, override=True)
    rl_cfg = _load_rl_config()

    tracker_name = os.getenv("TRACKER_DEFAULT", "").strip().upper()

    def _env(*keys):
        for k in keys:
            if k:
                v = os.getenv(k, "").strip()
                if v:
                    return v
        return None

    tracker_url = _env("TRACKER_BASE_URL", f"TRACKER_{tracker_name}_URL" if tracker_name else None)
    api_key     = _env("TRACKER_API_KEY",  f"TRACKER_{tracker_name}_API_KEY" if tracker_name else None)
    # CSI v1.6.2: Autonomous Config
    custom_ua = _env("CUSTOM_USER_AGENT") or "undici"
    # Portability: Use TMP_PATH as primary, default to Docker path
    tmp_path  = _env("TMP_PATH") or _env("TMP_ROOT") or str(TMP_ROOT)
    
    # Cookie logic
    cookie_name = _env("TRACKER_COOKIE_NAME", f"TRACKER_{tracker_name}_COOKIE_NAME" if tracker_name else None)
    cookie_val  = _env("TRACKER_COOKIE_VALUE", f"TRACKER_{tracker_name}_COOKIE_VALUE" if tracker_name else None)
    tracker_cookie = _env("TRACKER_COOKIE") # Combined format if exists

    # TMDB: .env first, RawLoadrr fallback
    tmdb_key = _env("TMDB_API_KEY")
    if not tmdb_key or tmdb_key == "tu_clave_tmdb_aqui":
        tmdb_key = rl_cfg.get("DEFAULT", {}).get("tmdb_api") or None

    # qBit: Default to localhost:8888 for Network Agnosticism
    rl_qbit  = rl_cfg.get("TORRENT_CLIENTS", {}).get("qbit", {})
    qbit_url  = _env("QBIT_URL") or f"http://{rl_qbit.get('qbit_url','localhost')}:{rl_qbit.get('qbit_port','8888')}"
    
    # CSI v1.6.4: Strict No-host.docker.internal policy
    if "host.docker.internal" in qbit_url:
        qbit_url = qbit_url.replace("host.docker.internal", "localhost")
        
    qbit_user = _env("QBIT_USER") or rl_qbit.get("qbit_user")
    qbit_pass = _env("QBIT_PASS") or rl_qbit.get("qbit_pass")

    return {
        "TRACKER_URL":          tracker_url,
        "TRACKER_API_KEY":      api_key or "",
        "TRACKER_COOKIE_NAME":  cookie_name,
        "TRACKER_COOKIE_VALUE": cookie_val,
        "TRACKER_COOKIE":       tracker_cookie,
        "TRACKER_USERNAME":     _env("TRACKER_USERNAME") or "",
        "TRACKER_DEFAULT":      tracker_name,
        "LIBRARY_PATH":         _env("CSI_LIBRARY_PATH"),
        "SONARR_URL":           _env("SONARR_URL"),
        "SONARR_API_KEY":       _env("SONARR_API_KEY"),
        "RADARR_URL":           _env("RADARR_URL"),
        "RADARR_API_KEY":       _env("RADARR_API_KEY"),
        "QBIT_URL":             qbit_url,
        "QBIT_USER":            qbit_user,
        "QBIT_PASS":            qbit_pass,
        "USE_TOR":              (_env("CSI_USE_TOR") or "").lower() == "true",
        "TMDB_API_KEY":         tmdb_key,
        "RAWLOADRR_CFG":        rl_cfg,
        "CUSTOM_USER_AGENT":    custom_ua,
        "TMP_PATH":             tmp_path,
        "DEBUG_MODE":           (_env("CSI_DEBUG") or "").lower() == "true",
    }

def _save_config_inplace(env_path: Path, key: str, value: str):
    """
    Safely updates a key in an .env file by reading and rewriting it in-place using r+ mode.
    This bypasses Docker inode locks by avoiding file replacement operations.
    """
    env_path.touch(exist_ok=True)

    # Quote value if it contains spaces or special characters, and isn't already quoted
    if any(c in value for c in (' ', '#', "'", '"')) and not (value.startswith(('"', "'")) and value.endswith(('"', "'"))):
        value = f'"{value}"'

    key_pattern = re.compile(r"^\s*(?:export\s+)?(" + re.escape(key) + r")\s*=")

    with open(env_path, "r+", encoding="utf-8") as f:
        lines = f.readlines()
        key_found = False
        for i, line in enumerate(lines):
            if key_pattern.match(line):
                comment = ""
                if " #" in line:
                    comment_part = line.split(" #", 1)[1]
                    comment = f" #{comment_part.strip()}"
                lines[i] = f"{key}={value}{comment}\n"
                key_found = True
                break

        if not key_found:
            if lines and not lines[-1].endswith('\n'):
                lines.append('\n')
            lines.append(f"{key}={value}\n")

        f.seek(0)
        f.writelines(lines)
        f.truncate()

def save_config(key: str, value: str):
    """
    Saves a key-value pair to the .env file.
    Uses a direct in-place write approach to be resilient to Docker file-system locks.
    """
    global _env_backup_done
    if not _env_backup_done and ENV_PATH.exists():
        bkp = ENV_PATH.with_suffix(".env.bkp")
        shutil.copy2(ENV_PATH, bkp)
        with open(BACKUP_LOG, "a") as f:
            f.write(f"[{datetime.now()}] {ENV_PATH} -> {bkp}\n")
        _env_backup_done = True

    dbg(f"Saving config: {key}={value}")
    _save_config_inplace(ENV_PATH, key, value)

# ─── SHARED HELPERS ───────────────────────────────────────────────────────────
def _norm_imdb(v) -> str:
    """Normalise an IMDB ID to its bare numeric form, e.g. 'tt0042564' → '42564'."""
    return str(v or "").replace("tt", "").lstrip("0") if v else ""

# ─── VIDEO CODEC & METADATA ──────────────────────────────────────────────────
HEVC_CODECS   = {"hevc", "h.265", "h265", "x265"}
LEGACY_CODECS = {"avc", "h.264", "h264", "x264", "mpeg-4", "mpeg4", "xvid", "divx", "mpeg video"}

def get_video_info(file_path: Path) -> dict:
    """Extracts Codec, Size, and Resolution using MediaInfo."""
    try:
        # P2: Combine mediainfo calls to reduce subprocess forks
        r = subprocess.run(
            ["mediainfo", "--Inform=Video;%Format%|%Width%x%Height%", str(file_path)],
            capture_output=True, text=True, timeout=10,
        )
        parts = r.stdout.strip().split("|")
        codec = parts[0].lower() if parts else "unknown"
        res   = parts[1] if len(parts) > 1 else "unknown"

        # Size in GB
        size_bytes = file_path.stat().st_size
        size_gb = f"{size_bytes / (1024**3):.2f}GB"

        return {
            "codec": codec,
            "res": res,
            "size": size_gb
        }
    except Exception:
        return {"codec": "unknown", "res": "unknown", "size": "unknown"}

def get_video_codec(file_path) -> str:
    info = get_video_info(Path(file_path))
    return info["codec"]

# ─── ICU — IDENTIFICADOR COMPUESTO ÚNICO (CSI v2.0) ──────────────────────────
# El ICU es la unidad atómica de identidad de un torrent en CSI v2.0.
# Sustituye la comparación simple por TMDB_ID por un fingerprint multidimensional.
# Formato: "TMDB_ID|RESOLUTION|CODEC|GROUP"  (todo en mayúsculas, separador pipe)
# Ejemplo: "12345|1080P|REMUX|GROUPNAME"
#
# La comparación exacta de ICU permite distinguir:
#   - Misma película, diferente resolución      (DUPE_POTENCIAL)
#   - Misma película, diferente codec/grupo     (DUPE_POTENCIAL)
#   - Misma película, misma versión exacta      (ESTADO_OK)

# Patrones de resolución reconocidos (orden: de mayor a menor especificidad)
_RES_PATTERNS = [
    (re.compile(r"\b2160p?\b", re.I), "2160P"),
    (re.compile(r"\b4k\b",     re.I), "2160P"),
    (re.compile(r"\b1080p?\b", re.I), "1080P"),
    (re.compile(r"\b720p?\b",  re.I), "720P"),
    (re.compile(r"\b480p?\b",  re.I), "480P"),
    (re.compile(r"\b576p?\b",  re.I), "576P"),
]

# Patrones de fuente/codec reconocidos
_CODEC_PATTERNS = [
    (re.compile(r"\bREMUX\b",             re.I), "REMUX"),
    (re.compile(r"\bBluRay\b|\bBDRip\b",  re.I), "BLURAY"),
    (re.compile(r"\bWEB[-.]?DL\b",        re.I), "WEB-DL"),
    (re.compile(r"\bWEBRip\b|\bWEB\b",    re.I), "WEBRIP"),
    (re.compile(r"\bHDTV\b",              re.I), "HDTV"),
    (re.compile(r"\bx265\b|\bHEVC\b|\bH\.265\b", re.I), "x265"),
    (re.compile(r"\bx264\b|\bAVC\b|\bH\.264\b",  re.I), "x264"),
    (re.compile(r"\bXviD\b|\bDivX\b",    re.I), "XVID"),
]


def normalize_folder_name(name: str) -> dict:
    """
    CSI v2.0: Normaliza nombres de carpeta/archivo a componentes semánticos.
    Maneja tanto formato con puntos (Pelicula.2010.1080p.REMUX-GRP)
    como formato con espacios/paréntesis (Pelicula (2010)).

    Retorna dict con:
        base_name   — Título limpio sin año/técnica
        year        — Año de producción o ""
        resolution  — Resolución normalizada ("1080P", "720P", ...) o ""
        codec       — Fuente/codec normalizado ("REMUX", "x265", ...) o ""
        group       — Grupo de release (token tras último "-") o ""
    """
    if not name:
        return {"base_name": "", "year": "", "resolution": "", "codec": "", "group": ""}

    # Normalizar separadores: reemplazar puntos y guiones bajos por espacios
    # pero preservar guiones finales de grupo (Pelicula.2010.1080p.REMUX-GRP)
    working = name.strip()

    # Extraer grupo de release: último token separado por "-" si parece release group
    group = ""
    group_match = re.search(r"-([A-Za-z0-9]{2,12})$", working)
    if group_match:
        candidate = group_match.group(1)
        # Filtrar falsos positivos: no extraer años ni resoluciones como grupo
        if not re.match(r"^\d{4}$", candidate) and not re.match(r"^\d{3,4}[pP]$", candidate):
            group = candidate.upper()
            working = working[:group_match.start()]

    # Normalizar puntos y guiones bajos como separadores a espacios
    working = re.sub(r"[._]", " ", working)
    # Eliminar corchetes y su contenido (ej: [BluRay] → gestionar aparte)
    working = re.sub(r"\[([^\]]+)\]", r" \1 ", working)

    # Extraer resolución
    resolution = ""
    for pattern, value in _RES_PATTERNS:
        if pattern.search(working):
            resolution = value
            break

    # Extraer codec/fuente
    codec = ""
    for pattern, value in _CODEC_PATTERNS:
        if pattern.search(working):
            codec = value
            break

    # Extraer año: "(YYYY)" o "YYYY" como token solitario (1900-2099)
    year = ""
    year_match = re.search(r"\((\d{4})\)|(?<!\d)(\d{4})(?!\d)", working)
    if year_match:
        year = year_match.group(1) or year_match.group(2)
        if not (1900 <= int(year) <= 2099):
            year = ""

    # Construir base_name: eliminar año, resolución, codec y técnicos del nombre
    base = working
    # Eliminar año con paréntesis
    base = re.sub(r"\(\d{4}\)", "", base)
    # Eliminar año suelto como token
    if year:
        base = re.sub(r"(?<!\d)" + re.escape(year) + r"(?!\d)", "", base)
    # Eliminar tokens técnicos (resolución, codec, fuentes comunes)
    _TECH_TOKENS = re.compile(
        r"\b(2160p?|4k|1080p?|720p?|480p?|576p?|"
        r"REMUX|BluRay|BDRip|WEB[-.]?DL|WEBRip|WEB|HDTV|"
        r"x265|x264|HEVC|AVC|H\.265|H\.264|XviD|DivX|"
        r"AAC|DTS|AC3|FLAC|TrueHD|Atmos|EAC3|"
        r"HDR|HDR10|DV|DoVi|SDR|"
        r"MKV|MP4|AVI|REMUX|PROPER|REPACK)\b",
        re.I
    )
    base = _TECH_TOKENS.sub("", base)
    # Limpiar espacios sobrantes
    base = re.sub(r"\s+", " ", base).strip(" -.,")

    dbg(f"[ICU] normalize_folder_name('{name}') → base='{base}' year='{year}' "
        f"res='{resolution}' codec='{codec}' group='{group}'")

    return {
        "base_name":  base,
        "year":       year,
        "resolution": resolution,
        "codec":      codec,
        "group":      group,
    }


def build_icu(tmdb_id, resolution: str, codec: str, group: str) -> str:
    """
    CSI v2.0: Construye el Identificador Compuesto Único (ICU).
    Formato: "TMDB_ID|RESOLUTION|CODEC|GROUP"
    Normaliza valores vacíos a "UNKNOWN" para garantizar ICUs válidos.

    Ejemplo: build_icu("12345", "1080p", "REMUX", "GRouP") → "12345|1080P|REMUX|GROUP"
    """
    tid  = str(tmdb_id).strip() if tmdb_id else "0"
    res  = resolution.upper().strip() if resolution else "UNKNOWN"
    cod  = codec.upper().strip()      if codec      else "UNKNOWN"
    grp  = group.upper().strip()      if group      else "UNKNOWN"
    return f"{tid}|{res}|{cod}|{grp}"


def parse_icu_from_tracker_name(name: str, tmdb_id) -> str:
    """
    CSI v2.0: Extrae un ICU del nombre de un torrent obtenido del tracker/scraper.
    Usa normalize_folder_name() para parsear los componentes y luego build_icu().
    """
    components = normalize_folder_name(name)
    return build_icu(
        tmdb_id,
        components.get("resolution", ""),
        components.get("codec", ""),
        components.get("group", ""),
    )


def _size_entropy_tiebreak(local_size_bytes: int, tracker_size_bytes: int,
                           tolerance: float = 0.05) -> bool:
    """
    CSI v2.0: Factor de desempate por tamaño de archivo.
    Si dos torrents del mismo TMDB_ID tienen ICUs distintos pero tamaños similares,
    probablemente son la misma versión con metadatos mal parseados.
    Tolerancia: ±5% del tamaño (configurable).
    Retorna True si los tamaños están dentro de la tolerancia → probable mismo contenido.
    """
    if not local_size_bytes or not tracker_size_bytes:
        return False
    ratio = abs(local_size_bytes - tracker_size_bytes) / max(local_size_bytes, tracker_size_bytes)
    within = ratio <= tolerance
    dbg(f"[ICU] Size entropy tiebreak: local={local_size_bytes} tracker={tracker_size_bytes} "
        f"ratio={ratio:.3f} tolerance={tolerance:.2f} → {'MATCH' if within else 'DIFF'}")
    return within

# ─── METADATA MANAGER ─────────────────────────────────────────────────────────
class MetadataManager:
    """
    Loads Sonarr and Radarr catalogs and provides folder-based lookups.
    Uses the `path` field from Sonarr/Radarr so folder names match exactly,
    avoiding fuzzy title comparisons.
    Also extracts Sonarr IDs embedded in folder names (TVdbID pattern).
    """

    def __init__(self, config: dict):
        self.cfg = config
        self._sonarr_by_path  = {}  # lower folder name → series dict
        self._sonarr_by_tvdb  = {}  # tvdb id str → series dict
        self._radarr_by_path  = {}  # lower folder name → movie dict

    def load_sonarr(self):
        if not (self.cfg["SONARR_URL"] and self.cfg["SONARR_API_KEY"]):
            dbg("Sonarr not configured — skipping")
            return
        try:
            api_limiter.wait()
            r = requests.get(
                f"{self.cfg['SONARR_URL']}/api/v3/series",
                headers={"X-Api-Key": self.cfg["SONARR_API_KEY"], "User-Agent": "undici"},
                timeout=15,
            )
            for s in r.json():
                if s.get("path"):
                    self._sonarr_by_path[Path(s["path"]).name.lower()] = s
                tvdb = str(s.get("tvdbId") or "")
                if tvdb:
                    self._sonarr_by_tvdb[tvdb] = s
            dbg(f"Sonarr: {len(self._sonarr_by_path)} series loaded")
        except Exception as e:
            dbg(f"Sonarr load error: {e}")

    def load_radarr(self):
        if not (self.cfg["RADARR_URL"] and self.cfg["RADARR_API_KEY"]):
            dbg("Radarr not configured — skipping")
            return
        try:
            api_limiter.wait()
            r = requests.get(
                f"{self.cfg['RADARR_URL']}/api/v3/movie",
                headers={"X-Api-Key": self.cfg["RADARR_API_KEY"], "User-Agent": "undici"},
                timeout=15,
            )
            for m in r.json():
                if m.get("path"):
                    self._radarr_by_path[Path(m["path"]).name.lower()] = m
            dbg(f"Radarr: {len(self._radarr_by_path)} movies loaded")
        except Exception as e:
            dbg(f"Radarr load error: {e}")

    def get_series(self, folder_name: str) -> Optional[dict]:
        """
        Locate Sonarr series for a show folder.
        Priority: exact path match → TVdbID extracted from folder name.
        """
        s = self._sonarr_by_path.get(folder_name.lower())
        if s:
            return s
        # Pattern: "Show Name YEAR-TVdbID-NNNNNN-..." (explicit)
        m = re.search(r"TVdbID[- _](\d+)", folder_name, re.I)
        if not m:
            # Pattern: "Show Name YEAR-NNNNNN" (implicit 5-7 digit ID after year)
            m = re.search(r"\d{4}-(\d{5,7})(?:\b|$|-)", folder_name)
        if m:
            s = self._sonarr_by_tvdb.get(m.group(1))
            if s:
                dbg(f"Sonarr match via TVdbID {m.group(1)} for '{folder_name}'")
                return s
        dbg(f"Sonarr: no match for folder '{folder_name}'")
        return None

    def get_movie(self, folder_name: str) -> Optional[dict]:
        return self._radarr_by_path.get(folder_name.lower())

    def get_aired_episodes(self, sonarr_series_id: int, season_num: int) -> Optional[int]:
        """Count aired episodes (airDateUtc < now UTC) for a Sonarr season."""
        try:
            api_limiter.wait()
            r = requests.get(
                f"{self.cfg['SONARR_URL']}/api/v3/episode",
                params={"seriesId": sonarr_series_id, "seasonNumber": season_num},
                headers={"X-Api-Key": self.cfg["SONARR_API_KEY"], "User-Agent": "undici"},
                timeout=15,
            )
            now = datetime.now(timezone.utc)
            count = sum(
                1 for ep in r.json()
                if ep.get("airDateUtc") and
                datetime.fromisoformat(ep["airDateUtc"].replace("Z", "+00:00")) < now
            )
            dbg(f"Sonarr aired episodes series={sonarr_series_id} S{season_num}: {count}")
            return count
        except Exception as e:
            dbg(f"Sonarr episodes error: {e}")
            return None

# ─── TRACKER INDEX ────────────────────────────────────────────────────────────
class TrackerIndex:
    """
    CSI v2.0: Índice en memoria del estado del tracker.
    Construido desde la API UNIT3D y/o el scraper HTTP.
    Persistido en tracker_index.json entre sesiones (eliminando la amnesia).

    Jerarquía de fuentes (orden de construcción):
        A. Scraper HTTP (cookie session)  → fuente principal de uploads del usuario
        B. Local TMP JSONs               → historial suplementario (no crítico)
        C. qBittorrent Client            → seeding paths para cruce de estado

    Métodos de consulta:
        has_movie_state()     → retorna estado CSI (ESTADO_OK, DUPE, etc.)
        has_tv_season_state() → retorna estado CSI para temporadas
        has_movie()           → wrapper bool legacy (compatibilidad)
        has_tv_season()       → wrapper bool legacy (compatibilidad)
    """

    def __init__(self):
        self.movie_tmdb    = set()   # str tmdb IDs de películas en tracker
        self.movie_imdb    = set()   # str imdb IDs (numeric, sin 'tt')
        self.tv_seasons    = set()   # (tmdb_str, season_str) — temporadas en tracker
        self.tv_tvdb       = set()   # (tvdb_str, season_str) — TV por TVDB
        self.seeding_names = set()      # paths absolutos (lower) desde qBit — compat v1.x
        self.seeding_paths = set()      # paths absolutos (lower) desde qBit — v2.0
        self.client_path_map: dict = {} # CSI v3.0: abs_path_lower → {hash, size}

        # CSI v2.0: ICU Index — fingerprint exacto por versión de torrent
        # Clave: ICU string ("TMDB|RES|CODEC|GROUP") → metadata del torrent
        self.icu_index: dict = {}    # ICU_str → {"torrent_id", "name", "size_bytes"}

        # CSI v2.0: URL del tracker registrada al construir el índice
        # Usada para invalidar el JSON cacheado si cambia el tracker
        self.tracker_url: str = ""

        # CSI v2.0: Flag de sonda — True si el último intento de consulta falló
        # Impide marcar ítems como ESTADO_NO_SUBIDO cuando no hay certeza
        self._probe_failed: bool = False

    def _ingest(self, torrent: dict):
        """
        CSI v2.0: Ingiere un torrent del tracker en el índice en memoria.
        Además de los IDs básicos, construye el ICU (Identificador Compuesto Único)
        para comparación precisa por resolución/codec/grupo.
        """
        attrs = torrent.get("attributes", {})
        # Robust ID extraction from both attributes and top-level
        tmdb = str(attrs.get("tmdb_id") or torrent.get("tmdb_id") or attrs.get("tmdb") or "").strip()
        imdb = _norm_imdb(attrs.get("imdb_id") or torrent.get("imdb_id") or attrs.get("imdb") or "")
        tvdb = str(attrs.get("tvdb_id") or torrent.get("tvdb_id") or attrs.get("tvdb") or "").strip()

        name      = attrs.get("name") or torrent.get("name") or ""
        cat_id    = str(attrs.get("category_id") or torrent.get("category_id") or "")
        season    = attrs.get("season_number") or torrent.get("season_number")
        tid       = str(attrs.get("torrent_id") or torrent.get("torrent_id") or "")
        size_raw  = attrs.get("size") or torrent.get("size") or 0
        try:
            size_bytes = int(size_raw)
        except (ValueError, TypeError):
            size_bytes = 0

        # MASTER RULE: data-category-id="1" for TV, 0 for Movies.
        # MANDATORY FALLBACK: Pattern matching in name
        is_tv = False
        if cat_id == "1":
            is_tv = True
        elif cat_id == "0":
            is_tv = False
        else:
            # P1/P3: Only fallback when category is unknown and tighten regex
            if re.search(r"[ .]S\d{2}\b|Season\s+\d+|\bE\d{2,}\b", name, re.I):
                is_tv = True

        if is_tv:
            # If it's TV, we need a season number. If missing, try to extract from name.
            if season is None:
                m = re.search(r"[ .]S(\d+)", name, re.I)
                if m: season = int(m.group(1))
                else: season = 1 # Default to S01 if totally unknown but matched as TV

            try:
                s = str(int(season))
                if tmdb: self.tv_seasons.add((tmdb, s))
                if tvdb: self.tv_tvdb.add((tvdb, s))
            except (ValueError, TypeError):
                pass
        else:
            if tmdb: self.movie_tmdb.add(tmdb)
            if imdb: self.movie_imdb.add(imdb)

        # CSI v2.0: Construir ICU del torrent ingresado y almacenar en icu_index
        # Esto permite comparación exacta de versión (resolución/codec/grupo)
        if tmdb or tvdb:
            components = normalize_folder_name(name)
            icu = build_icu(
                tmdb or tvdb,
                components.get("resolution", ""),
                components.get("codec",      ""),
                components.get("group",      ""),
            )
            if icu not in self.icu_index:
                self.icu_index[icu] = {
                    "torrent_id": tid,
                    "name":       name,
                    "size_bytes": size_bytes,
                    "tmdb_id":    tmdb,
                    "tvdb_id":    tvdb,
                    "is_tv":      is_tv,
                }
                dbg(f"[ICU] Ingested: {icu} ← '{name}'")

    def build_user(self, config: dict) -> bool:
        """
        CSI v2.0: Motor de Triangulación (sin API para uploads del usuario).
        Fuentes: Scraper (A), Local TMP JSONs (B), qBittorrent (C).
        La ausencia de TMP o JSON NO es un fallo bloqueante.
        """
        if not config["TRACKER_URL"]:
            console.print("[red]TRACKER_URL not set.[/red]")
            return False

        # CSI v2.0: Registrar el tracker_url para invalidación futura del JSON
        self.tracker_url = config["TRACKER_URL"].rstrip("/")

        user = config.get("TRACKER_USERNAME")
        total = 0

        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as prog:
            t_id = prog.add_task(f"Triangulating index for {user}...", total=None)

            # ── Source A: Cookie Scraper ──────────────────────────────────────
            prog.update(t_id, description="[Scraper] Parsing tracker pages...")
            total += self._source_scraper(config, prog, t_id)

            # ── Source B: Local Metadata ──────────────────────────────────────
            prog.update(t_id, description="[Tmp] Scanning local metadata...")
            total += self._source_local_tmp(config)

            # ── Source C: qBittorrent ─────────────────────────────────────────
            prog.update(t_id, description="[qBit] Checking seeding status...")
            total += self._source_qbit(config)

        console.print(
            f"[green]Triangulation Complete! {total} items matched · "
            f"Movies: {len(self.movie_tmdb) + len(self.movie_imdb)} | "
            f"TV Seasons: {len(self.tv_seasons)}[/green]"
        )
        return True

    def _source_scraper(self, config: dict, progress, task_id) -> int:
        """Source A: Scraping UNIT3D torrent list via cookies."""
        user = config.get("TRACKER_USERNAME")
        base = config["TRACKER_URL"].rstrip("/")
        page = 0
        matches = 0
        sess = _session(config)
        consecutive_errors = 0
        MAX_CONSECUTIVE_ERRORS = 3

        while True:
            page += 1
            if page > 500: # Safety guard
                dbg("Scraper: safety limit reached (500 pages)")
                break
                
            url = f"{base}/torrents?uploader={user}&page={page}"
            try:
                api_limiter.wait()
                r = sess.get(url, timeout=20)
                if r.status_code != 200:
                    dbg(f"Scraper page {page}: HTTP {r.status_code}")
                    consecutive_errors += 1
                    if consecutive_errors >= MAX_CONSECUTIVE_ERRORS: break
                    continue
                
                consecutive_errors = 0
                soup = BeautifulSoup(r.text, "html.parser")
                rows = soup.select("tr.torrent-search--list__row")
                if not rows:
                    dbg(f"Scraper: No rows found on page {page}")
                    break
                
                for row in rows:
                    if not isinstance(row, bs4_element.Tag):
                        continue
                    # CSI v1.6.4: Strict Parse (Matched Unknown Fix)
                    tmdb = row.get("data-tmdb-id") or ""
                    imdb = row.get("data-imdb-id") or ""
                    tvdb = row.get("data-tvdb-id") or ""
                    tid  = row.get("data-torrent-id") or ""
                    cat_id = row.get("data-category-id") or ""

                    name_tag = row.select_one("a.torrent-search--list__name")
                    name_text = (
                        name_tag.get_text(strip=True)
                        if isinstance(name_tag, bs4_element.Tag) else "Unknown"
                    )

                    # Fallback for IDs if attributes are empty or placeholder
                    if not tmdb or tmdb == "0":
                        tmdb_link = row.find("a", href=re.compile(r"themoviedb.org/(movie|tv)/(\d+)"))
                        if isinstance(tmdb_link, bs4_element.Tag):
                            m = re.search(r"/(movie|tv)/(\d+)", str(tmdb_link.get("href", "") or ""))
                            if m: tmdb = m.group(2)

                    if not imdb or imdb == "0":
                        imdb_link = row.find("a", href=re.compile(r"imdb.com/title/tt(\d+)"))
                        if isinstance(imdb_link, bs4_element.Tag):
                            m = re.search(r"title/tt(\d+)", str(imdb_link.get("href", "") or ""))
                            if m: imdb = m.group(1)
                    
                    if not any([tmdb, imdb, tvdb]):
                        dbg(f"[DEBUG] Row skipped (No IDs): {name_text}")
                        continue

                    # For now, let's use the standard ingest but with a dict
                    fake_torrent = {
                        "attributes": {
                            "tmdb_id": tmdb,
                            "imdb_id": imdb,
                            "tvdb_id": tvdb,
                            "torrent_id": tid,
                            "category_id": cat_id,
                            "name": name_text
                        }
                    }
                    
                    self._ingest(fake_torrent)
                    matches += 1
                    dbg(f"[DEBUG] [TRIANGULATION] Matched {name_text} via Scraper")

                # Check for next page
                if not soup.select_one("a.pagination__next"):
                    break
                    
            except Exception as e:
                dbg(f"Scraper error page {page}: {e}")
                consecutive_errors += 1
                if consecutive_errors >= MAX_CONSECUTIVE_ERRORS: break
                
        return matches

    def _source_local_tmp(self, config: dict) -> int:
        """
        Source B: Local JSON scanning in TMP_PATH.
        CSI v2.0: Esta fuente es SUPLEMENTARIA, no crítica.
        Si la carpeta tmp no existe, se continúa sin fallar — el índice
        se construye desde las fuentes primarias (Scraper/API/qBit).
        PROHIBIDO retornar 0 como señal de fallo bloqueante.
        """
        tmp_path = Path(config.get("TMP_PATH", TMP_ROOT))
        if not tmp_path.exists():
            dbg(f"[DEBUG] TMP_PATH no encontrado: {tmp_path} — fuente local omitida (no crítica)")
            # CSI v2.0: No retornamos 0 como señal de fallo.
            # La ausencia de tmp NO implica que el contenido no esté en el tracker.
            # Continuamos: las fuentes A (Scraper) y C (qBit) tienen prioridad.
            return 0  # 0 matches locales, pero el flujo continúa normalmente
        
        matches = 0
        found_any_json = False
        try:
            # Recon of TMP folder: look for .json files
            for item in tmp_path.iterdir():
                json_files = []
                if item.is_dir():
                    json_files = list(item.glob("*.json"))
                elif item.suffix == ".json":
                    json_files = [item]
                
                if json_files:
                    found_any_json = True

                for jf in json_files:
                    try:
                        with open(jf, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            # UNIT3D Upload JSONs usually have these
                            tmdb = data.get("tmdb_id") or data.get("tmdb")
                            imdb = data.get("imdb_id") or data.get("imdb")
                            tvdb = data.get("tvdb_id") or data.get("tvdb")
                            season = data.get("season_number")
                            cat_id = data.get("category_id") or data.get("category")
                            name = data.get("name") or jf.stem
                            
                            if tmdb or imdb or tvdb:
                                fake_t = {
                                    "attributes": {
                                        "tmdb_id": tmdb,
                                        "imdb_id": imdb,
                                        "tvdb_id": tvdb,
                                        "season_number": season,
                                        "category_id": cat_id,
                                        "name": name
                                    }
                                }
                                self._ingest(fake_t)
                                matches += 1
                                dbg(f"[DEBUG] [TRIANGULATION] Matched {name} via Tmp")
                    except Exception:
                        continue
            
            if not found_any_json:
                dbg(f"[DEBUG] Local storage empty at {tmp_path}. No .json files found.")

        except Exception as e:
            dbg(f"Local TMP source error: {e}")
            
        return matches

    def _source_qbit(self, config: dict) -> int:
        """Source C: qBittorrent seeding items (Paths)."""
        path_map = get_client_torrents(config)
        if path_map is None:
            dbg("[SOURCE_C] qBittorrent no disponible — sonda fallida, activando _probe_failed")
            self._probe_failed = True
            return 0

        self.client_path_map = path_map
        matches = 0
        for p in path_map:
            self.seeding_names.add(p)
            self.seeding_paths.add(p)
            matches += 1
            dbg(f"[DEBUG] [TRIANGULATION] Matched {p} via qBit")
        return matches
            
    def has_movie(self, tmdb_id=None, imdb_id=None, name=None) -> bool:
        """Legacy bool wrapper — compatibilidad con código v1.x."""
        if tmdb_id and str(tmdb_id) in self.movie_tmdb:
            return True
        if imdb_id:
            clean = _norm_imdb(imdb_id)
            if clean and clean in self.movie_imdb:
                return True
        if name and name.lower() in self.seeding_names:
            return True
        return False

    def has_tv_season(self, tmdb_id=None, tvdb_id=None, season_num=None, name=None) -> bool:
        """Legacy bool wrapper — compatibilidad con código v1.x."""
        if season_num is not None:
            s = str(int(season_num))
            if tmdb_id and (str(tmdb_id), s) in self.tv_seasons:
                return True
            if tvdb_id and (str(tvdb_id), s) in self.tv_tvdb:
                return True
        if name and name.lower() in self.seeding_names:
            return True
        return False

    # ──────────────────────────────────────────────────────────────────────────
    # CSI v2.0: Métodos de Máquina de Estados
    # Retornan uno de los 5 estados definidos en STATE_MACHINE section.
    # Estos métodos son la evolución de has_movie() / has_tv_season().
    # ──────────────────────────────────────────────────────────────────────────

    def has_movie_state(self, tmdb_id=None, imdb_id=None, name=None,
                        local_icu: Optional[str] = None, client_paths: Optional[set] = None,
                        local_size_bytes: int = 0) -> str:
        """
        CSI v2.0: Determina el estado de una película en la triangulación.
        Prioridad de autoridades: ICU exacto > TMDB_ID > IMDB_ID > seeding_names
        Integra la comprobación del cliente (client_paths) para distinguir
        ESTADO_OK de ESTADO_FALTA_CLIENTE.

        Args:
            tmdb_id:          TMDB ID de la película (Radarr/TMDB)
            imdb_id:          IMDB ID de la película
            name:             Nombre de carpeta local (para fallback por nombre)
            local_icu:        ICU construido desde el contenido local
            client_paths:     Set de paths absolutos (lower) desde qBittorrent
            local_size_bytes: Tamaño del archivo local en bytes (para entropía)

        Returns:
            str: Uno de los 5 estados ESTADO_* definidos en la máquina de estados.
        """
        client_paths = client_paths or set()
        tmdb_str = str(tmdb_id).strip() if tmdb_id else ""

        # ── Nivel 1: Comparación exacta por ICU ──────────────────────────────
        # Si tenemos el ICU local, buscamos una coincidencia exacta en el índice.
        if local_icu and local_icu in self.icu_index:
            tracker_entry = self.icu_index[local_icu]
            dbg(f"[STATE] ICU exact match: {local_icu} → torrent_id={tracker_entry.get('torrent_id')}")
            # Confirmar si también está en el cliente (seeding).
            # Usar nombre local primero; si no hay nombre local, usar el nombre del tracker.
            check_name = name or tracker_entry.get("name", "")
            in_client = self._check_client_path(check_name, client_paths)
            if in_client:
                return ESTADO_OK
            else:
                return ESTADO_FALTA_CLIENTE

        # ── Nivel 2: TMDB_ID presente en tracker pero ICU diferente ──────────
        # Misma película, versión distinta → potencial duplicado
        if tmdb_str and tmdb_str in self.movie_tmdb:
            # Buscar en icu_index si hay entradas con ese TMDB pero ICU diferente
            matching_icus = [k for k in self.icu_index if k.startswith(f"{tmdb_str}|")]
            if matching_icus and local_icu:
                # ICU diferente confirmado → aplicar entropía de tamaño como desempate
                for existing_icu in matching_icus:
                    tracker_size = self.icu_index[existing_icu].get("size_bytes", 0)
                    if tracker_size and local_size_bytes:
                        if _size_entropy_tiebreak(local_size_bytes, tracker_size):
                            # Tamaños muy similares → probablemente la misma versión
                            dbg(f"[STATE] Size entropy tiebreak → FALTA_CLIENTE "
                                f"(local={local_size_bytes}, tracker={tracker_size})")
                            in_client = self._check_client_path(name or "", client_paths)
                            return ESTADO_OK if in_client else ESTADO_FALTA_CLIENTE
                # Sin match por tamaño → dupe potencial confirmado
                dbg(f"[STATE] DUPE POTENCIAL: tmdb={tmdb_str} local_icu={local_icu} "
                    f"existing_icus={matching_icus}")
                return ESTADO_DUPE_POTENCIAL
            elif matching_icus and not local_icu:
                # No tenemos ICU local para comparar → conservador, reportar como dupe potencial
                return ESTADO_DUPE_POTENCIAL
            else:
                # TMDB en tracker pero sin ICU en índice (entrada de v1.x sin ICU)
                in_client = self._check_client_path(name or "", client_paths)
                return ESTADO_OK if in_client else ESTADO_FALTA_CLIENTE

        # ── Nivel 3: IMDB_ID ─────────────────────────────────────────────────
        if imdb_id:
            clean = _norm_imdb(imdb_id)
            if clean and clean in self.movie_imdb:
                dbg(f"[STATE] IMDB match: {clean} → checking client")
                in_client = self._check_client_path(name or "", client_paths)
                return ESTADO_OK if in_client else ESTADO_FALTA_CLIENTE

        # ── Nivel 4: Nombre en seeding_names (qBit path match legacy) ────────
        if name and name.lower() in self.seeding_names:
            return ESTADO_OK  # Si está seeding, asumimos subido

        # ── Sin coincidencia → No subido ─────────────────────────────────────
        return ESTADO_NO_SUBIDO

    def has_tv_season_state(self, tmdb_id=None, tvdb_id=None, season_num=None,
                            name=None, local_icu: str | None = None,
                            client_paths: set | None = None,
                            local_size_bytes: int = 0) -> str:
        """
        CSI v2.0: Determina el estado de una temporada de TV en la triangulación.
        Análogo a has_movie_state() pero para contenido de TV.

        Args:
            tmdb_id:          TMDB ID de la serie (Sonarr/TMDB)
            tvdb_id:          TVDB ID de la serie (Sonarr/TheTVDB)
            season_num:       Número de temporada (int)
            name:             Nombre de la carpeta del show (para fallback)
            local_icu:        ICU construido desde el contenido local
            client_paths:     Set de paths absolutos (lower) desde qBittorrent
            local_size_bytes: Tamaño total en bytes de la temporada local

        Returns:
            str: Uno de los 5 estados ESTADO_* definidos en la máquina de estados.
        """
        client_paths = client_paths or set()
        tmdb_str = str(tmdb_id).strip() if tmdb_id else ""
        tvdb_str = str(tvdb_id).strip() if tvdb_id else ""

        # ── Nivel 1: ICU exacto ───────────────────────────────────────────────
        if local_icu and local_icu in self.icu_index:
            tracker_entry = self.icu_index[local_icu]
            dbg(f"[STATE] TV ICU exact match: {local_icu} → torrent_id={tracker_entry.get('torrent_id')}")
            # Usar nombre local primero; si no hay, usar nombre del tracker como fallback
            check_name = name or tracker_entry.get("name", "")
            in_client = self._check_client_path(check_name, client_paths)
            return ESTADO_OK if in_client else ESTADO_FALTA_CLIENTE

        # ── Nivel 2: TMDB/TVDB con número de temporada ───────────────────────
        if season_num is not None:
            s = str(int(season_num))
            found_in_tracker = False
            if tmdb_str and (tmdb_str, s) in self.tv_seasons:
                found_in_tracker = True
            if tvdb_str and (tvdb_str, s) in self.tv_tvdb:
                found_in_tracker = True

            if found_in_tracker:
                # Comprobar si hay ICU similar (dupe potencial de TV)
                if local_icu:
                    ref_id = tmdb_str or tvdb_str
                    matching_icus = [k for k in self.icu_index if k.startswith(f"{ref_id}|")]
                    if matching_icus:
                        # Hay versiones en tracker pero ninguna coincide con el ICU local
                        in_client = self._check_client_path(name or "", client_paths)
                        return ESTADO_OK if in_client else ESTADO_FALTA_CLIENTE
                in_client = self._check_client_path(name or "", client_paths)
                return ESTADO_OK if in_client else ESTADO_FALTA_CLIENTE

        # ── Nivel 3: Nombre en seeding_names ─────────────────────────────────
        if name and name.lower() in self.seeding_names:
            return ESTADO_OK

        return ESTADO_NO_SUBIDO

    def _check_client_path(self, name: str, client_paths: set) -> bool:
        """
        CSI v2.0: Comprueba si un ítem está presente en qBittorrent
        verificando si algún path del cliente contiene el nombre del ítem.
        Comparación case-insensitive.
        """
        if not name or not client_paths:
            return False
        name_lower = name.lower()
        for cp in client_paths:
            if name_lower in cp:
                return True
        # También comprobar contra seeding_names (v1.x compat)
        if name_lower in self.seeding_names:
            return True
        return False

    # ──────────────────────────────────────────────────────────────────────────
    # CSI v2.0: Persistencia del índice (elimina la amnesia entre sesiones)
    # ──────────────────────────────────────────────────────────────────────────

    def save_to_json(self, path: Path):
        """
        CSI v2.0: Serializa el estado actual del TrackerIndex a un archivo JSON.
        Llamar después de cada escaneo o investigación para persistir el índice.
        Garantiza que la próxima sesión no tenga que reconstruir desde cero.
        """
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "version":      "2.0",
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "tracker_url":  self.tracker_url,
                # Conjuntos → listas para serialización JSON
                "movie_tmdb":   sorted(list(self.movie_tmdb)),
                "movie_imdb":   sorted(list(self.movie_imdb)),
                "tv_seasons":   sorted([list(t) for t in self.tv_seasons]),
                "tv_tvdb":      sorted([list(t) for t in self.tv_tvdb]),
                "seeding_names": sorted(list(self.seeding_names)),
                # Dicts ya son serializables directamente
                "icu_index":    self.icu_index,
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            dbg(f"[INDEX] TrackerIndex guardado: {path} "
                f"({len(self.movie_tmdb)} movies, {len(self.tv_seasons)} seasons, "
                f"{len(self.icu_index)} ICUs)")
            console.print(
                f"[dim green]▸ Índice persistido:[/dim green] [dim]{path}[/dim] "
                f"[dim]({len(self.icu_index)} ICUs)[/dim]"
            )
        except Exception as e:
            dbg(f"[INDEX] Error al guardar TrackerIndex: {e}")
            console.print(f"[yellow]Advertencia: No se pudo guardar el índice: {e}[/yellow]")

    def load_from_json(self, path: Path, tracker_url: str = "") -> bool:
        """
        CSI v2.0: Carga el TrackerIndex desde un JSON persistido previamente.
        Verifica que el tracker_url coincida para evitar usar un índice obsoleto
        de un tracker diferente.

        Returns:
            True  si el índice fue cargado exitosamente y es válido
            False si el archivo no existe, está corrupto o la URL no coincide
        """
        if not path.exists():
            dbg(f"[INDEX] No existe {path} — se construirá el índice desde cero")
            return False

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Validar versión
            version = data.get("version", "1.0")
            if version not in ("2.0",):
                dbg(f"[INDEX] Versión de JSON incompatible ({version}) — reconstruyendo")
                return False

            # Validar URL del tracker (invalidación automática si cambia el tracker)
            saved_url = data.get("tracker_url", "")
            if tracker_url and saved_url and saved_url.rstrip("/") != tracker_url.rstrip("/"):
                console.print(
                    f"[yellow]▸ Índice cacheado corresponde a tracker diferente.[/yellow]\n"
                    f"  Guardado: [dim]{saved_url}[/dim]\n"
                    f"  Actual:   [dim]{tracker_url}[/dim]\n"
                    f"  [dim]Reconstruyendo desde cero...[/dim]"
                )
                dbg(f"[INDEX] URL mismatch: saved='{saved_url}' current='{tracker_url}' → rebuild")
                return False

            # Cargar datos en los conjuntos en memoria
            self.movie_tmdb    = set(data.get("movie_tmdb", []))
            self.movie_imdb    = set(data.get("movie_imdb", []))
            self.tv_seasons    = set(tuple(t) for t in data.get("tv_seasons", []))
            self.tv_tvdb       = set(tuple(t) for t in data.get("tv_tvdb",    []))
            self.seeding_names = set(data.get("seeding_names", []))
            self.seeding_paths = self.seeding_names  # alias v2.0
            self.icu_index     = data.get("icu_index", {})
            self.tracker_url   = saved_url

            last_updated = data.get("last_updated", "desconocido")
            console.print(
                Panel(
                    f"[green]Índice cargado desde caché[/green]\n"
                    f"Tracker : [cyan]{saved_url}[/cyan]\n"
                    f"Películas: [bold]{len(self.movie_tmdb)}[/bold] TMDBs | "
                    f"TV: [bold]{len(self.tv_seasons)}[/bold] temporadas | "
                    f"ICUs: [bold]{len(self.icu_index)}[/bold]\n"
                    f"[dim]Última actualización: {last_updated}[/dim]",
                    border_style="green",
                    title="[bold]CSI — TrackerIndex Persistente[/bold]",
                )
            )
            dbg(f"[INDEX] Cargado desde {path}: {len(self.movie_tmdb)} movies, "
                f"{len(self.tv_seasons)} seasons, {len(self.icu_index)} ICUs")
            return True

        except json.JSONDecodeError as e:
            dbg(f"[INDEX] JSON corrupto en {path}: {e} — reconstruyendo")
            console.print(f"[yellow]Índice cacheado corrupto ({e}) — reconstruyendo desde cero[/yellow]")
            return False
        except Exception as e:
            dbg(f"[INDEX] Error al cargar {path}: {e}")
            return False

# ─── GLOBAL SEARCH (per-item API call) ───────────────────────────────────────
# CSI v2.0: Sistema de consultas híbridas con fallback y máquina de estados.
#
# Flujo de consulta:
#   1. API UNIT3D (api_token)  → fuente primaria
#   2. Scraper HTTP (cookie)   → fallback si API falla o no hay API key
#   3. ESTADO_INCIDENCIA       → si ambas fuentes fallan
#
# REGLA CRÍTICA: NUNCA retornar ESTADO_NO_SUBIDO si la consulta falló.
# Solo ESTADO_INCIDENCIA cuando no hay certeza de la respuesta del tracker.

def _compare_icu_results(results: list, local_icu: str | None, tmdb_id,
                         client_paths: set, local_size_bytes: int = 0) -> str:
    """
    CSI v2.0: Analiza la lista de torrents devuelta por el tracker
    y determina el estado CSI del ítem local comparando ICUs.

    Args:
        results:          Lista de dicts de torrents (formato UNIT3D API)
        local_icu:        ICU construido desde el contenido local
        tmdb_id:          TMDB ID del ítem (para logging)
        client_paths:     Paths del cliente qBit (para ESTADO_OK vs FALTA_CLIENTE)
        local_size_bytes: Tamaño local para entropía de desempate

    Returns:
        str: Estado CSI determinado
    """
    if not results:
        return ESTADO_NO_SUBIDO

    # Si tenemos ICU local, intentar coincidencia exacta primero
    if local_icu:
        for t in results:
            attrs = t.get("attributes", {})
            t_name  = attrs.get("name") or t.get("name") or ""
            t_tmdb  = str(attrs.get("tmdb_id") or t.get("tmdb_id") or "").strip()
            tracker_icu = parse_icu_from_tracker_name(t_name, t_tmdb or tmdb_id)

            if tracker_icu == local_icu:
                dbg(f"[COMPARE] ICU exact match en tracker: {tracker_icu}")
                in_client = _check_path_in_client(t_name, client_paths)
                return ESTADO_OK if in_client else ESTADO_FALTA_CLIENTE

        # ICU no coincide → mismo TMDB pero versión diferente → DUPE POTENCIAL
        # Aplicar entropía de tamaño como posible desempate
        for t in results:
            attrs = t.get("attributes", {})
            t_size = 0
            try:
                t_size = int(attrs.get("size") or t.get("size") or 0)
            except (ValueError, TypeError):
                pass
            if t_size and local_size_bytes:
                if _size_entropy_tiebreak(local_size_bytes, t_size):
                    dbg(f"[COMPARE] Size entropy tiebreak → probablemente misma versión")
                    t_name = attrs.get("name") or t.get("name") or ""
                    in_client = _check_path_in_client(t_name, client_paths)
                    return ESTADO_OK if in_client else ESTADO_FALTA_CLIENTE

        dbg(f"[COMPARE] DUPE POTENCIAL: tmdb={tmdb_id}, local_icu={local_icu}")
        return ESTADO_DUPE_POTENCIAL

    # Sin ICU local, solo sabemos que existe en tracker
    # Verificar si está en el cliente por nombre
    for t in results:
        attrs = t.get("attributes", {})
        t_name = attrs.get("name") or t.get("name") or ""
        if _check_path_in_client(t_name, client_paths):
            return ESTADO_OK
    return ESTADO_FALTA_CLIENTE


def _check_path_in_client(name: str, client_paths: set) -> bool:
    """
    CSI v2.0: Comprueba si un nombre de torrent está presente en el cliente
    buscando coincidencia parcial case-insensitive en los paths de qBit.
    Función auxiliar independiente para uso en búsquedas globales.
    """
    if not name or not client_paths:
        return False
    name_lower = name.lower()
    for cp in client_paths:
        if name_lower in cp:
            return True
    return False


def _scraper_search_item(config: dict, tmdb_id=None, tvdb_id=None,
                         query: Optional[str] = None, tracker_index: "Optional[TrackerIndex]" = None,
                         client_paths: Optional[set] = None, local_icu: Optional[str] = None,
                         local_size_bytes: int = 0) -> str:
    """
    CSI v2.0: Fallback scraper para búsqueda per-ítem cuando la API falla.
    Consulta el índice en memoria del TrackerIndex (si está disponible) antes
    de intentar un scrape HTTP adicional — esto evita llamadas innecesarias.

    Retorna estado CSI o ESTADO_INCIDENCIA si no hay información suficiente.
    """
    client_paths = client_paths or set()

    # Si tenemos un índice en memoria, consultarlo primero (O(1))
    if tracker_index is not None and len(tracker_index.movie_tmdb) > 0:
        dbg(f"[SCRAPER_FALLBACK] Consultando índice en memoria para tmdb={tmdb_id}")
        if tmdb_id:
            tmdb_str = str(tmdb_id).strip()
            if tmdb_str in tracker_index.movie_tmdb:
                if local_icu and local_icu in tracker_index.icu_index:
                    in_client = _check_path_in_client(query or "", client_paths)
                    return ESTADO_OK if in_client else ESTADO_FALTA_CLIENTE
                elif tmdb_str in tracker_index.movie_tmdb:
                    return ESTADO_DUPE_POTENCIAL
            return ESTADO_NO_SUBIDO

    # Sin índice en memoria — intentar búsqueda HTTP en el tracker con cookie
    base = config.get("TRACKER_URL", "").rstrip("/")
    if not base:
        dbg("[SCRAPER_FALLBACK] No TRACKER_URL disponible para fallback scraper")
        return ESTADO_INCIDENCIA

    cookie_available = (
        config.get("TRACKER_COOKIE") or config.get("TRACKER_COOKIE_VALUE")
    )
    if not cookie_available:
        dbg("[SCRAPER_FALLBACK] Sin cookie disponible para scrape — INCIDENCIA")
        return ESTADO_INCIDENCIA

    try:
        sess = _session(config)
        search_term = query or ""
        url = f"{base}/torrents?tmdbId={tmdb_id or ''}&name={search_term}&page=1"
        dbg(f"[SCRAPER_FALLBACK] HTTP scrape: {url}")
        api_limiter.wait()
        r = sess.get(url, timeout=15)

        if r.status_code != 200:
            dbg(f"[SCRAPER_FALLBACK] HTTP {r.status_code} — INCIDENCIA")
            return ESTADO_INCIDENCIA

        soup = BeautifulSoup(r.text, "html.parser")
        rows = soup.select("tr.torrent-search--list__row")
        if not rows:
            dbg("[SCRAPER_FALLBACK] Sin resultados en scrape — NO_SUBIDO")
            return ESTADO_NO_SUBIDO

        for row in rows:
            if not isinstance(row, bs4_element.Tag):
                continue
            row_tmdb = row.get("data-tmdb-id") or ""
            row_name_tag = row.select_one("a.torrent-search--list__name")
            row_name = (
                row_name_tag.get_text(strip=True)
                if isinstance(row_name_tag, bs4_element.Tag) else ""
            )
            if (tmdb_id and str(row_tmdb) == str(tmdb_id)) or (query and query.lower() in row_name.lower()):
                in_client = _check_path_in_client(row_name, client_paths)
                if local_icu:
                    tracker_icu = parse_icu_from_tracker_name(row_name, tmdb_id)
                    if tracker_icu == local_icu:
                        return ESTADO_OK if in_client else ESTADO_FALTA_CLIENTE
                    return ESTADO_DUPE_POTENCIAL
                return ESTADO_OK if in_client else ESTADO_FALTA_CLIENTE

        return ESTADO_NO_SUBIDO

    except Exception as e:
        dbg(f"[SCRAPER_FALLBACK] Error: {e} — INCIDENCIA")
        return ESTADO_INCIDENCIA


def search_global_state(config: dict, tmdb_id=None, imdb_id=None, tvdb_id=None,
                        season_num=None, query=None, local_icu: Optional[str] = None,
                        client_paths: Optional[set] = None, local_size_bytes: int = 0,
                        tracker_index: "Optional[TrackerIndex]" = None) -> str:
    """
    CSI v2.0: Consulta per-ítem al tracker con máquina de estados y fallback híbrido.

    Flujo de ejecución:
        1. API UNIT3D (api_token)  → resultado análizado con _compare_icu_results()
        2. Scraper HTTP (cookie)   → _scraper_search_item() si API falla
        3. ESTADO_INCIDENCIA       → si ambas fuentes fallan

    REGLA CRÍTICA:
        NUNCA retornar ESTADO_NO_SUBIDO si hay un fallo de conexión.
        Solo ESTADO_INCIDENCIA cuando no hay certeza de la respuesta del tracker.

    Args:
        config:           Config del script con TRACKER_URL, API_KEY, cookies
        tmdb_id:          TMDB ID a buscar
        imdb_id:          IMDB ID a buscar
        tvdb_id:          TVDB ID a buscar (TV)
        season_num:       Número de temporada (TV)
        query:            Texto de búsqueda por nombre (fallback)
        local_icu:        ICU construido desde el contenido local
        client_paths:     Paths del cliente qBit
        local_size_bytes: Tamaño local para entropía
        tracker_index:    Índice en memoria para consultas sin API

    Returns:
        str: Estado CSI (ESTADO_OK, ESTADO_DUPE_POTENCIAL, ESTADO_FALTA_CLIENTE,
             ESTADO_NO_SUBIDO, ESTADO_INCIDENCIA)
    """
    client_paths = client_paths or set()
    base_url = config.get("TRACKER_URL", "").rstrip("/")
    api_key  = config.get("TRACKER_API_KEY", "")

    # ── Sin URL del tracker → no podemos consultar nada ──────────────────────
    if not base_url:
        dbg("[GLOBAL_STATE] No TRACKER_URL — INCIDENCIA")
        return ESTADO_INCIDENCIA

    # ── Sin API Key → fallback directo al scraper ─────────────────────────────
    if not api_key:
        dbg("[GLOBAL_STATE] Sin API key — usando scraper fallback directamente")
        return _scraper_search_item(
            config, tmdb_id=tmdb_id, tvdb_id=tvdb_id, query=query,
            tracker_index=tracker_index, client_paths=client_paths,
            local_icu=local_icu, local_size_bytes=local_size_bytes,
        )

    # ── Intentar API UNIT3D ───────────────────────────────────────────────────
    url    = f"{base_url}/api/torrents/filter"
    params = {"api_token": api_key, "perPage": 10}

    if tmdb_id:
        params["tmdbId"] = tmdb_id
    elif imdb_id:
        params["imdbId"] = str(imdb_id).replace("tt", "")
    elif tvdb_id:
        params["tvdbId"] = tvdb_id
    elif query:
        params["name"] = query
    else:
        dbg("[GLOBAL_STATE] Sin identificador para consultar — INCIDENCIA")
        return ESTADO_INCIDENCIA

    if season_num is not None:
        params["season_number"] = int(season_num)

    try:
        api_limiter.wait()
        sess = _session(config)
        r    = sess.get(url, params=params, headers=_headers(), timeout=12)

        if r.status_code != 200:
            dbg(f"[GLOBAL_STATE] API HTTP {r.status_code} — intentando scraper fallback")
            return _scraper_search_item(
                config, tmdb_id=tmdb_id, tvdb_id=tvdb_id, query=query,
                tracker_index=tracker_index, client_paths=client_paths,
                local_icu=local_icu, local_size_bytes=local_size_bytes,
            )

        data    = r.json()
        results = data.get("data", [])
        dbg(f"[GLOBAL_STATE] API OK: tmdb={tmdb_id} tvdb={tvdb_id} "
            f"season={season_num} → {len(results)} resultados")

        return _compare_icu_results(results, local_icu, tmdb_id, client_paths, local_size_bytes)

    except Exception as e:
        dbg(f"[GLOBAL_STATE] API Exception: {e} — intentando scraper fallback")
        try:
            return _scraper_search_item(
                config, tmdb_id=tmdb_id, tvdb_id=tvdb_id, query=query,
                tracker_index=tracker_index, client_paths=client_paths,
                local_icu=local_icu, local_size_bytes=local_size_bytes,
            )
        except Exception as e2:
            dbg(f"[GLOBAL_STATE] Scraper fallback también falló: {e2} → INCIDENCIA")
            return ESTADO_INCIDENCIA


def search_global(config: dict, tmdb_id=None, imdb_id=None, tvdb_id=None,
                  season_num=None, query=None) -> bool:
    """
    Legacy bool wrapper de search_global_state() — compatibilidad con v1.x.
    Retorna True si el ítem está confirmado en el tracker (ESTADO_OK o FALTA_CLIENTE o DUPE).
    Retorna False solo si la consulta fue exitosa y el ítem NO está en el tracker.
    CSI v2.0: En caso de INCIDENCIA retorna False conservadoramente (no "no subido").
    """
    state = search_global_state(config, tmdb_id=tmdb_id, imdb_id=imdb_id,
                                tvdb_id=tvdb_id, season_num=season_num, query=query)
    # Interpretar como "existe en tracker" para los estados que no son NO_SUBIDO/INCIDENCIA
    return state in (ESTADO_OK, ESTADO_FALTA_CLIENTE, ESTADO_DUPE_POTENCIAL)

# ─── LIBRARY SCANNER ──────────────────────────────────────────────────────────
def forensic_scan(config: dict, meta: MetadataManager, tracker_index: TrackerIndex,
                  do_global: bool = False, client_paths: Optional[set] = None,
                  client_path_map: Optional[dict] = None,
                  qbit_available: bool = True, report: Optional[LiveReport] = None):
    """
    CSI v2.0: Motor de escaneo forense con máquina de estados completa.
    Walk the library directory tree y clasifica cada ítem en uno de los 5 estados CSI.
    v1.6.5+: Multi-codec (HEVC/H264) reporting logic con LiveReport support.
    TV: Folders only. Movies: Files.

    Cambios v2.0:
      - Eliminado bloque 'if found_in_qbit: continue' como exit temprano.
        El cruce con qBit ahora se hace DENTRO de la determinación de estado,
        para distinguir ESTADO_OK de ESTADO_FALTA_CLIENTE correctamente.
      - Nuevos conjuntos de resultado: dupe_items, falta_cliente_items, incidencia_items.
      - Usa has_movie_state() y has_tv_season_state() en lugar de has_movie() bool.
      - En modo global, usa search_global_state() con ICU y fallback scraper.
    """
    lib_path = Path(config["LIBRARY_PATH"])
    # Conjuntos para ítems ESTADO_NO_SUBIDO (candidatos a upload) — separados por codec
    hevc_movies, h264_movies = set(), set()
    hevc_tv, h264_tv = set(), set()

    # CSI v2.0: Nuevos conjuntos para los demás estados del diagnóstico
    dupe_items        = set()  # ESTADO_DUPE_POTENCIAL — misma peli, diferente versión
    falta_cliente     = set()  # ESTADO_FALTA_CLIENTE  — en tracker, no en qBit
    incidencia_items  = set()  # ESTADO_INCIDENCIA     — error de sonda, sin certeza

    # Contadores de estados para el resumen final
    state_counts = {
        ESTADO_OK:             0,
        ESTADO_DUPE_POTENCIAL: 0,
        ESTADO_FALTA_CLIENTE:  0,
        ESTADO_NO_SUBIDO:      0,
        ESTADO_INCIDENCIA:     0,
    }

    # CSI v3.0: Normalizar client_path_map para path-first matching
    if client_path_map is None:
        client_path_map = {}
    if client_paths is None:
        client_paths = set(client_path_map.keys())

    # Precalcular un set de basenames del cliente para fallback de coincidencia
    client_basenames: set = {os.path.basename(p) for p in client_path_map}

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as prog:
        task = prog.add_task("Scanning library...", total=None)

        for root, dirs, files in os.walk(lib_path):
            dirs.sort()
            root_path = Path(root)

            # v1.6.5: Update Dashboard with current folder and real-time counts
            found_msg = f"Movies: {len(hevc_movies)+len(h264_movies)} | TV: {len(hevc_tv)+len(h264_tv)}"
            update_status("CSI", "Scanning Library", "PROCESSING",
                          details=f"[{found_msg}] Scanning: {root_path}")

            mkv_files = [f for f in files if f.lower().endswith(".mkv")]
            if not mkv_files:
                continue

            # CSI v2.0: ELIMINADO el bloque 'if found_in_qbit: continue'.
            # El cruce con qBit se hace dentro de has_movie_state() / has_tv_season_state()
            # para poder distinguir ESTADO_OK de ESTADO_FALTA_CLIENTE correctamente.
            # Items que están en qBit Y en tracker → ESTADO_OK (ya gestionados)
            # Items que están en tracker pero NO en qBit → ESTADO_FALTA_CLIENTE (reportar)

            rel_parts = root_path.relative_to(lib_path).parts
            is_tv = any(re.search(r"\bSeason\s+\d+|\bS\d{2}\b", part, re.I) for part in rel_parts[-2:])

            if is_tv:
                # ── TV Season ──────────────────────────────────────────────
                season_match = re.search(r"Season\s+(\d+)|S(\d{2})", root_path.name, re.I)
                if not season_match:
                    continue
                season_num  = int(season_match.group(1) or season_match.group(2))
                if season_num == 0:
                    continue
                show_folder = root_path.parent.name
                prog.update(task, description=f"TV: {show_folder} S{season_num:02d}")

                series  = meta.get_series(show_folder)
                s_tmdb  = str(series.get("tmdbId") or "") if series else None
                s_tvdb  = str(series.get("tvdbId") or "") if series else None

                # CSI v2.0: Construir ICU local para la temporada
                # Usamos el primer mkv como muestra de resolución/codec
                sample_info   = get_video_info(root_path / sorted(mkv_files)[0])
                local_res_raw = sample_info.get("res", "")
                local_cod_raw = sample_info.get("codec", "")
                # Normalizar resolución del mediainfo (ej: "1920x1080" → "1080P")
                local_res = _normalize_mediainfo_res(local_res_raw)
                local_cod = _normalize_mediainfo_codec(local_cod_raw)
                local_grp = normalize_folder_name(show_folder).get("group", "")
                local_icu = build_icu(s_tmdb or s_tvdb or "", local_res, local_cod, local_grp)

                # Tamaño total de la temporada
                local_size_bytes = sum(
                    (root_path / f).stat().st_size for f in mkv_files
                    if (root_path / f).exists()
                )

                # CSI v2.0: Determinación de estado con máquina de estados
                if do_global:
                    item_state = search_global_state(
                        config,
                        tmdb_id=s_tmdb or None,
                        tvdb_id=s_tvdb or None,
                        season_num=season_num,
                        query=show_folder,
                        local_icu=local_icu,
                        client_paths=client_paths,
                        local_size_bytes=local_size_bytes,
                        tracker_index=tracker_index,
                    )
                else:
                    item_state = tracker_index.has_tv_season_state(
                        tmdb_id=s_tmdb,
                        tvdb_id=s_tvdb,
                        season_num=season_num,
                        name=show_folder,
                        local_icu=local_icu,
                        client_paths=client_paths,
                        local_size_bytes=local_size_bytes,
                    )

                # CSI v3.0: PATH-FIRST override — evita falsos FALTA_CLIENTE
                if item_state == ESTADO_FALTA_CLIENTE and client_path_map:
                    current_abs = os.path.abspath(str(root_path)).lower()
                    if current_abs in client_path_map:
                        item_state = ESTADO_OK
                        dbg(f"[PATH-FIRST] TV FALTA_CLIENTE→OK (exact path): {current_abs}")
                    else:
                        current_basename = os.path.basename(current_abs)
                        if current_basename and current_basename in client_basenames:
                            item_state = ESTADO_OK
                            dbg(f"[PATH-FIRST] TV FALTA_CLIENTE→OK (basename): {current_basename}")

                # CSI v3.0: QBIT DOWN — FALTA_CLIENTE → INCIDENCIA si qBit no está disponible
                if not qbit_available and item_state == ESTADO_FALTA_CLIENTE:
                    item_state = ESTADO_INCIDENCIA
                    dbg(f"[QBIT_DOWN] TV FALTA_CLIENTE→INCIDENCIA (qBit no disponible)")

                state_counts[item_state] = state_counts.get(item_state, 0) + 1
                dbg(f"[SCAN] TV {show_folder} S{season_num:02d} → [{item_state}] ICU={local_icu}")

                # Clasificar según estado — solo ESTADO_NO_SUBIDO va al report de upload
                abs_dir = str(root_path.absolute())
                if item_state == ESTADO_OK:
                    continue  # Ya está todo en orden
                elif item_state == ESTADO_DUPE_POTENCIAL:
                    dupe_items.add(abs_dir)
                    continue  # No subir — puede ser dupe
                elif item_state == ESTADO_FALTA_CLIENTE:
                    falta_cliente.add(abs_dir)
                    continue  # En tracker pero no seeding
                elif item_state == ESTADO_INCIDENCIA:
                    incidencia_items.add(abs_dir)
                    continue  # Sin certeza — no reportar como uploadable
                # else: ESTADO_NO_SUBIDO → clasificar por codec para upload report

                # Classification by dominant codec (ESTADO_NO_SUBIDO only)
                infos      = [get_video_info(root_path / f) for f in mkv_files]
                hevc_count = sum(1 for info in infos if info["codec"] in HEVC_CODECS)
                all_hevc   = hevc_count == len(mkv_files)

                # CSI v1.6.5: TV_SHOWS -> PARENT DIRECTORY ONLY
                if all_hevc:
                    hevc_tv.add(abs_dir)
                    if report: report.add("TV", "HEVC", abs_dir)
                else:
                    h264_tv.add(abs_dir)
                    if report: report.add("TV", "H264", abs_dir)

            else:
                # ── Movie ──────────────────────────────────────────────────
                movie_folder = root_path.name
                movie_data   = meta.get_movie(movie_folder)
                m_tmdb = str(movie_data.get("tmdbId") or "") if movie_data else None
                m_imdb = str(movie_data.get("imdbId") or "") if movie_data else None
                prog.update(task, description=f"Movie: {movie_folder}")

                # CSI v2.0: Construir ICU local para la película
                # Usamos el primer mkv como muestra de resolución/codec
                first_mkv    = sorted(mkv_files)[0]
                sample_info  = get_video_info(root_path / first_mkv)
                local_res    = _normalize_mediainfo_res(sample_info.get("res", ""))
                local_cod    = _normalize_mediainfo_codec(sample_info.get("codec", ""))
                local_grp    = normalize_folder_name(movie_folder).get("group", "")
                local_icu    = build_icu(m_tmdb or "", local_res, local_cod, local_grp)

                # Tamaño del archivo de muestra (película principal)
                try:
                    local_size_bytes = (root_path / first_mkv).stat().st_size
                except Exception:
                    local_size_bytes = 0

                # CSI v2.0: Determinación de estado con máquina de estados
                if do_global:
                    item_state = search_global_state(
                        config,
                        tmdb_id=m_tmdb or None,
                        imdb_id=m_imdb or None,
                        query=movie_folder,
                        local_icu=local_icu,
                        client_paths=client_paths,
                        local_size_bytes=local_size_bytes,
                        tracker_index=tracker_index,
                    )
                else:
                    item_state = tracker_index.has_movie_state(
                        tmdb_id=m_tmdb,
                        imdb_id=m_imdb,
                        name=movie_folder,
                        local_icu=local_icu,
                        client_paths=client_paths,
                        local_size_bytes=local_size_bytes,
                    )

                # CSI v3.0: PATH-FIRST override — evita falsos FALTA_CLIENTE
                if item_state == ESTADO_FALTA_CLIENTE and client_path_map:
                    current_abs = os.path.abspath(str(root_path)).lower()
                    if current_abs in client_path_map:
                        item_state = ESTADO_OK
                        dbg(f"[PATH-FIRST] Movie FALTA_CLIENTE→OK (exact path): {current_abs}")
                    else:
                        current_basename = os.path.basename(current_abs)
                        if current_basename and current_basename in client_basenames:
                            item_state = ESTADO_OK
                            dbg(f"[PATH-FIRST] Movie FALTA_CLIENTE→OK (basename): {current_basename}")

                # CSI v3.0: QBIT DOWN — FALTA_CLIENTE → INCIDENCIA si qBit no está disponible
                if not qbit_available and item_state == ESTADO_FALTA_CLIENTE:
                    item_state = ESTADO_INCIDENCIA
                    dbg(f"[QBIT_DOWN] Movie FALTA_CLIENTE→INCIDENCIA (qBit no disponible)")

                state_counts[item_state] = state_counts.get(item_state, 0) + 1
                dbg(f"[SCAN] Movie '{movie_folder}' → [{item_state}] ICU={local_icu}")

                abs_dir = str(root_path.absolute())
                if item_state == ESTADO_OK:
                    continue
                elif item_state == ESTADO_DUPE_POTENCIAL:
                    dupe_items.add(abs_dir)
                    continue
                elif item_state == ESTADO_FALTA_CLIENTE:
                    falta_cliente.add(abs_dir)
                    continue
                elif item_state == ESTADO_INCIDENCIA:
                    incidencia_items.add(abs_dir)
                    continue
                # else: ESTADO_NO_SUBIDO → clasificar por codec

                # Not on tracker - MOVIES -> INDIVIDUAL FILES
                for mkv in sorted(mkv_files):
                    info     = get_video_info(root_path / mkv)
                    abs_path = str((root_path / mkv).absolute())
                    if info["codec"] in HEVC_CODECS:
                        hevc_movies.add(abs_path)
                        if report: report.add("MOVIE", "HEVC", abs_path)
                    else:
                        h264_movies.add(abs_path)
                        if report: report.add("MOVIE", "H264", abs_path)

    # CSI v2.0: Mostrar resumen de estados al finalizar el scan
    console.print(Panel(
        f"[bold]Resumen del Escaneo Forense CSI v2.0[/bold]\n\n"
        f"  [{STATE_COLORS[ESTADO_OK]}]{STATE_LABELS[ESTADO_OK]}[/{STATE_COLORS[ESTADO_OK]}]: "
        f"[bold]{state_counts[ESTADO_OK]}[/bold]\n"
        f"  [{STATE_COLORS[ESTADO_DUPE_POTENCIAL]}]{STATE_LABELS[ESTADO_DUPE_POTENCIAL]}"
        f"[/{STATE_COLORS[ESTADO_DUPE_POTENCIAL]}]: [bold]{state_counts[ESTADO_DUPE_POTENCIAL]}[/bold]\n"
        f"  [{STATE_COLORS[ESTADO_FALTA_CLIENTE]}]{STATE_LABELS[ESTADO_FALTA_CLIENTE]}"
        f"[/{STATE_COLORS[ESTADO_FALTA_CLIENTE]}]: [bold]{state_counts[ESTADO_FALTA_CLIENTE]}[/bold]\n"
        f"  [{STATE_COLORS[ESTADO_NO_SUBIDO]}]{STATE_LABELS[ESTADO_NO_SUBIDO]}"
        f"[/{STATE_COLORS[ESTADO_NO_SUBIDO]}]: [bold]{state_counts[ESTADO_NO_SUBIDO]}[/bold]\n"
        f"  [{STATE_COLORS[ESTADO_INCIDENCIA]}]{STATE_LABELS[ESTADO_INCIDENCIA]}"
        f"[/{STATE_COLORS[ESTADO_INCIDENCIA]}]: [bold]{state_counts[ESTADO_INCIDENCIA]}[/bold]",
        border_style="cyan",
        title="[bold cyan]Estado de la Triangulación[/bold cyan]",
    ))

    # Convert sets back to sorted lists for reporting
    return (
        sorted(list(hevc_tv)),
        sorted(list(h264_tv)),
        sorted(list(hevc_movies)),
        sorted(list(h264_movies)),
        sorted(list(dupe_items)),
        sorted(list(falta_cliente)),
        sorted(list(incidencia_items)),
    )


def _normalize_mediainfo_res(res_raw: str) -> str:
    """
    CSI v2.0: Convierte resolución de MediaInfo (ej: '1920x1080') al formato ICU (ej: '1080P').
    Necesario para cruzar información local de MediaInfo con ICU del tracker.
    """
    if not res_raw or res_raw == "unknown":
        return "UNKNOWN"
    try:
        parts = res_raw.lower().replace("x", "×").split("×")
        if len(parts) >= 2:
            height = int(parts[1])
            if height >= 2000:  return "2160P"
            if height >= 1000:  return "1080P"
            if height >= 700:   return "720P"
            if height >= 500:   return "576P"
            if height >= 400:   return "480P"
    except (ValueError, IndexError):
        pass
    # Fallback: buscar patrones directamente en el string raw
    for pattern, value in _RES_PATTERNS:
        if pattern.search(res_raw):
            return value
    return "UNKNOWN"


def _normalize_mediainfo_codec(codec_raw: str) -> str:
    """
    CSI v2.0: Normaliza el codec de MediaInfo al formato ICU.
    MediaInfo retorna 'HEVC', 'AVC', 'MPEG Video', etc.
    Los normalizamos al mismo vocabulario que usa normalize_folder_name().
    """
    if not codec_raw or codec_raw == "unknown":
        return "UNKNOWN"
    c = codec_raw.lower().strip()
    if c in {"hevc", "h.265", "h265", "x265"}:
        return "x265"
    if c in {"avc", "h.264", "h264", "x264"}:
        return "x264"
    if c in {"mpeg video", "mpeg-4", "mpeg4", "xvid", "divx"}:
        return "XVID"
    # Para codecs de fuente (REMUX, etc.) que no vienen de MediaInfo
    for pattern, value in _CODEC_PATTERNS:
        if pattern.search(codec_raw):
            return value
    return codec_raw.upper()

# ─── REPORTS ──────────────────────────────────────────────────────────────────
def get_report_path(category: str, codec: str, subcat: str) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    subdir_map = {"local": "local_cases", "user": "user_cases", "global": "global_cases"}
    base   = REPORTS_DIR / subdir_map.get(subcat, subcat)
    folder = base / ("tv_shows" if category.upper() == "TV" else "movies")
    folder.mkdir(parents=True, exist_ok=True)
    
    # CSI v1.6.5 Naming
    return folder / f"{category.upper()}_{codec.upper()}_uploadable_{ts}.txt"

def generate_reports(hevc_tv, h264_tv, hevc_m, h264_m, subcat: str, config: dict,
                     dupe_items: Optional[list] = None, falta_cliente_items: Optional[list] = None,
                     incidencia_items: Optional[list] = None):
    """
    CSI v2.0: Genera reportes de todos los estados del diagnóstico.
    - HEVC/H264 TV y Movie: candidatos a upload (ESTADO_NO_SUBIDO)
    - DUPE_POTENCIAL: ítems con mismo TMDB pero diferente versión (revisar manualmente)
    - FALTA_CLIENTE: en tracker pero sin seedear (descargar .torrent)
    - INCIDENCIA: ítems que no se pudieron verificar (error de sonda)
    """
    dupe_items        = dupe_items        or []
    falta_cliente_items = falta_cliente_items or []
    incidencia_items  = incidencia_items  or []

    # Reportes de upload (ESTADO_NO_SUBIDO) — comportamiento v1.6.5 intacto
    upload_sets = [
        ("TV",    "HEVC", hevc_tv),
        ("TV",    "H264", h264_tv),
        ("MOVIE", "HEVC", hevc_m),
        ("MOVIE", "H264", h264_m),
    ]
    generated_upload = []
    for cat, codec, data in upload_sets:
        if data:
            p = get_report_path(cat, codec, subcat)
            with open(p, "w", encoding="utf-8") as f:
                # CSI v1.6.5: Strict Output Protocol (Absolute Paths Only)
                # No headers, no metadata, one per line.
                f.write("\n".join(data) + "\n")
            generated_upload.append(p)

    # CSI v2.0: Reportes adicionales de diagnóstico
    generated_diag = []
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    subdir_map = {"local": "local_cases", "user": "user_cases", "global": "global_cases"}
    base_dir = REPORTS_DIR / subdir_map.get(subcat, subcat)

    if dupe_items:
        p_dupe = base_dir / f"DUPE_POTENCIAL_{ts}.txt"
        p_dupe.parent.mkdir(parents=True, exist_ok=True)
        with open(p_dupe, "w", encoding="utf-8") as f:
            f.write("# CSI v2.0 — DUPE POTENCIAL: misma película, versión diferente en tracker\n")
            f.write("# Revisar manualmente antes de hacer upload\n")
            f.write("\n".join(dupe_items) + "\n")
        generated_diag.append(("DUPE_POTENCIAL", p_dupe))
        dbg(f"[REPORT] DUPE_POTENCIAL: {len(dupe_items)} ítems → {p_dupe}")

    if falta_cliente_items:
        p_fc = base_dir / f"FALTA_CLIENTE_{ts}.txt"
        p_fc.parent.mkdir(parents=True, exist_ok=True)
        with open(p_fc, "w", encoding="utf-8") as f:
            f.write("# CSI v2.0 — FALTA EN CLIENTE: en tracker pero no seeding en qBittorrent\n")
            f.write("# Descargar el .torrent y añadir al cliente para reanudar seeding\n")
            f.write("\n".join(falta_cliente_items) + "\n")
        generated_diag.append(("FALTA_CLIENTE", p_fc))
        dbg(f"[REPORT] FALTA_CLIENTE: {len(falta_cliente_items)} ítems → {p_fc}")

    if incidencia_items:
        p_inc = base_dir / f"INCIDENCIA_{ts}.txt"
        p_inc.parent.mkdir(parents=True, exist_ok=True)
        with open(p_inc, "w", encoding="utf-8") as f:
            f.write("# CSI v2.0 — INCIDENCIA: error de sonda, no se pudo verificar estado\n")
            f.write("# Reintentar cuando la conexión al tracker esté restaurada\n")
            f.write("\n".join(incidencia_items) + "\n")
        generated_diag.append(("INCIDENCIA", p_inc))
        dbg(f"[REPORT] INCIDENCIA: {len(incidencia_items)} ítems → {p_inc}")

    # ── Mostrar resultados ────────────────────────────────────────────────────
    if generated_upload or generated_diag:
        console.print(Panel("[bold green]CSI Reports Generated (v2.0)[/bold green]", border_style="green"))

        if generated_upload:
            console.print(f"\n  [bold cyan]Candidatos a Upload (ESTADO_NO_SUBIDO):[/bold cyan]")
            for i, g in enumerate(generated_upload, 1):
                relative_path = g.relative_to(REPORTS_DIR)
                host_path = f"{HOST_REPORTS_DIR}/{relative_path}"
                console.print(f"  {i}. [cyan]{host_path}[/cyan]")
                dbg(f"[OK] Report saved to: {host_path}")

        if generated_diag:
            console.print(f"\n  [bold yellow]Reportes de Diagnóstico:[/bold yellow]")
            for label, p in generated_diag:
                color = STATE_COLORS.get(f"ESTADO_{label}", "yellow")
                relative_path = p.relative_to(REPORTS_DIR)
                host_path = f"{HOST_REPORTS_DIR}/{relative_path}"
                console.print(f"  [{color}]{label}[/{color}]: [dim]{host_path}[/dim]")

        if generated_upload:
            if Confirm.ask("\nFeed Singularity for upload?"):
                choices = [str(i) for i in range(1, len(generated_upload) + 1)]
                sel = Prompt.ask("Select report number", choices=choices)
                _feed_singularity(generated_upload[int(sel) - 1], config)
    else:
        console.print(Panel("[yellow]No new items found for reporting.[/yellow]", border_style="yellow"))

def _feed_singularity(report_path: Path, config: dict):
    rawloadrr_dir = BASE_DIR / "RawLoadrr"
    if not rawloadrr_dir.exists():
        dbg(f"RawLoadrr directory not found: {rawloadrr_dir}")
        return

    tracker = config.get("TRACKER_DEFAULT") or "MILNU"
    cmd = [
        "python3", "auto-upload.py",
        "--list", str(report_path), "--tracker", tracker,
    ]
    console.print(f"[cyan]Launching: {' '.join(cmd)}[/cyan]")
    try:
        subprocess.run(cmd, cwd=rawloadrr_dir, check=True)
    except subprocess.CalledProcessError as e:
        dbg(f"auto-upload.py failed with exit code {e.returncode}")
    except Exception as e:
        dbg(f"Error launching singularity feed: {e}")

# ─── qBIT LOCAL ───────────────────────────────────────────────────────────────
def get_client_torrents(config: dict):
    """
    CSI v3.0: Retorna un diccionario de torrents indexados por ruta absoluta.
    Clave  : os.path.abspath(content_path).lower()
    Valor  : {"hash": str, "size": int}
    Filtrado por dominio del TRACKER_URL configurado (si está disponible).
    Retorna None si la conexión con qBittorrent falla (señal de error para el llamador).
    Retorna {} si qbittorrentapi no está instalado (no-op silencioso).
    """
    if not qbittorrentapi:
        dbg("qbittorrentapi not installed")
        return {}

    tracker_domain = ""
    tracker_url = config.get("TRACKER_URL", "") or ""
    if tracker_url:
        m = re.match(r"https?://([^/]+)", tracker_url)
        if m:
            tracker_domain = m.group(1).lower()

    try:
        qbt = qbittorrentapi.Client(
            host=config["QBIT_URL"],
            username=config["QBIT_USER"],
            password=config["QBIT_PASS"],
            REQUESTS_ARGS={'timeout': (5, 15), 'headers': {'User-Agent': 'undici'}}
        )
        qbt.auth_log_in()

        if not qbt.is_logged_in:
            dbg(f"qBit: Authentication failed for {config['QBIT_URL']}")
            return None

        result: dict = {}
        skipped = 0
        for t in qbt.torrents_info():
            if tracker_domain:
                t_tracker = str(getattr(t, "tracker", "") or "").lower()
                if t_tracker and tracker_domain not in t_tracker:
                    skipped += 1
                    continue
            abs_path = os.path.abspath(str(t.content_path)).lower()
            result[abs_path] = {
                "hash": str(getattr(t, "hash", "") or ""),
                "size": int(getattr(t, "size", 0) or 0),
            }

        dbg(
            f"qBit: {len(result)} torrent paths loaded"
            + (f" (filtered by '{tracker_domain}', skipped {skipped})" if tracker_domain else "")
        )
        return result

    except Exception as e:
        dbg(f"qBit error: {e}")
        return None

# ─── MENU HELPERS ─────────────────────────────────────────────────────────────
def welcome():
    console.clear()
    console.print(Align.center(DETECTIVE_ART))
    console.print(Align.center(
        Panel.fit("[bold cyan]Forensic Detective[/bold cyan] · Check · Search · Identify", border_style="cyan")
    ))

def _status_panel(config: dict):
    t_url  = config["TRACKER_URL"] or "[red]NOT SET[/red]"
    t_key  = "[green]✓[/green]" if config["TRACKER_API_KEY"] else "[red]✗[/red]"
    t_user = f"[cyan]{config['TRACKER_USERNAME']}[/cyan]" if config["TRACKER_USERNAME"] else "[yellow]no username[/yellow]"
    lib    = config["LIBRARY_PATH"] or "[red]NOT SET[/red]"
    tor    = "[red]ON ⚠[/red]"  if config["USE_TOR"]  else "[green]OFF[/green]"
    dbg_s  = "[green]ON[/green]" if DEBUG_MODE         else "[dim]OFF[/dim]"
    console.print(Panel(
        f"Tracker : {t_url}  API:{t_key}  user:{t_user}\n"
        f"Library : [cyan]{lib}[/cyan]\n"
        f"TOR: {tor}   Debug: {dbg_s}",
        border_style="cyan", title="[bold]CSI Status[/bold]",
    ))
    if config["USE_TOR"]:
        console.print(Panel(
            "[bold red]TOR IS ENABLED[/bold red]\n"
            "CF Rule 1 blocks ALL paths (incl. /api/) from non-ES IPs with threat_score>15.\n"
            "Disable TOR in Settings before running any investigation.",
            border_style="red", title="⚠ CF Firewall Warning",
        ))

def _confirm_scan_path(config: dict) -> dict:
    current = config.get("LIBRARY_PATH")
    if current and os.path.isdir(current):
        console.print(f"Library path: [cyan]{current}[/cyan]")
        if Confirm.ask("Use this path?", default=True):
            return config
    while True:
        lib = Prompt.ask("[bold]Enter library path to scan[/bold]")
        if os.path.isdir(lib):
            save_config("CSI_LIBRARY_PATH", lib)
            return load_config()
        console.print(f"[red]Path not found: {lib}[/red]")

# ─── CONFIGURE TRACKER ────────────────────────────────────────────────────────
def configure_tracker(config: dict) -> dict:
    rl_cfg      = config.get("RAWLOADRR_CFG", {})
    rl_trackers = [
        k for k, v in rl_cfg.get("TRACKERS", {}).items()
        if isinstance(v, dict) and not k.startswith("default")
    ]

    while True:
        console.print(Panel("CSI Settings & Tracker Management", border_style="cyan"))
        cur_url  = config["TRACKER_URL"]  or "None"
        cur_name = config["TRACKER_DEFAULT"] or "None"
        cur_user = config["TRACKER_USERNAME"] or "None"
        cur_ua   = config["CUSTOM_USER_AGENT"]
        cur_tmp  = config["TMP_PATH"]
        cur_qbit = config["QBIT_URL"]
        
        console.print(f"  Tracker: [cyan]{cur_url}[/cyan]  ID:[bold]{cur_name}[/bold]  user:[bold]{cur_user}[/bold]")
        console.print(f"  TMP Path: [green]{cur_tmp}[/green]")
        console.print(f"  qBit URL: [green]{cur_qbit}[/green]")
        console.print(f"  User-Agent: [bold yellow]{cur_ua}[/bold yellow]")
        
        console.print(
            f"\n  1. Edit Tracker (URL, API, Cookies)\n"
            f"  2. Import from RawLoadrr config\n"
            f"  3. Set TMP Path\n"
            f"  4. Set qBittorrent URL\n"
            f"  5. Set Custom User-Agent\n"
            f"  6. Toggle TOR: {'[red]ON[/red]' if config.get('USE_TOR') else '[green]OFF[/green]'}\n"
            f"  7. Toggle Debug: {'[green]ON[/green]' if DEBUG_MODE else '[dim]OFF[/dim]'}\n"
            f"  0. Back"
        )
        c = Prompt.ask("Select", choices=["1", "2", "3", "4", "5", "6", "7", "0"], default="0")

        if c == "0":
            return config

        elif c == "1":
            name = Prompt.ask("Tracker ID", default=config.get("TRACKER_DEFAULT") or "NOBS")
            url = Prompt.ask("Base URL", default=config.get("TRACKER_URL") or "")
            user = Prompt.ask("Username", default=config.get("TRACKER_USERNAME") or "")
            api_key = Prompt.ask("API Key", default=config.get("TRACKER_API_KEY") or "")
            
            # Cookie handling v1.6.2
            old_cookie = config.get("TRACKER_COOKIE") or config.get("TRACKER_COOKIE_VALUE") or ""
            cookie_val = Prompt.ask("TRACKER_COOKIE (Session Value)", default=old_cookie)
            
            n = name.strip().upper()
            save_config("TRACKER_DEFAULT", n)
            save_config("TRACKER_BASE_URL", url)
            save_config(f"TRACKER_{n}_URL", url)
            save_config("TRACKER_USERNAME", user)
            save_config("TRACKER_API_KEY", api_key)
            save_config(f"TRACKER_{n}_API_KEY", api_key)
            save_config("TRACKER_COOKIE", cookie_val)
            save_config("TRACKER_COOKIE_VALUE", cookie_val)
            
            # Propagar cambios
            updates = {
                "TRACKER_DEFAULT": n,
                "TRACKER_URL": url,
                "TRACKER_USERNAME": user,
                "TRACKER_COOKIE_VALUE": cookie_val
            }
            
            # Pedir Announce URL para RawLoadrr
            announce = Prompt.ask("Announce URL (para RawLoadrr)", default="")
            if announce:
                updates["ANNOUNCE_URL"] = announce
            
            _propagate_config(updates)
            config = load_config()

        elif c == "3":
            new_tmp = Prompt.ask("Enter TMP path", default=config["TMP_PATH"])
            save_config("TMP_PATH", new_tmp)
            config = load_config()

        elif c == "4":
            new_qbit = Prompt.ask("Enter qBittorrent URL", default=config["QBIT_URL"])
            save_config("QBIT_URL", new_qbit)
            config = load_config()

        elif c == "5":
            new_ua = Prompt.ask("Enter Custom User-Agent", default=config["CUSTOM_USER_AGENT"])
            save_config("CUSTOM_USER_AGENT", new_ua)
            config = load_config()

        elif c == "6":
            config["USE_TOR"] = not config.get("USE_TOR", False)
            save_config("CSI_USE_TOR", str(config["USE_TOR"]))
            config = load_config()

        elif c == "7":
            toggle_debug()
            save_config("CSI_DEBUG", str(DEBUG_MODE))
            config = load_config()

        elif c == "2":
            if not rl_trackers:
                console.print("[yellow]No configured trackers found in RawLoadrr/data/config.py[/yellow]")
                continue
            console.print("\n[bold]Trackers available in RawLoadrr:[/bold]")
            for i, t in enumerate(rl_trackers, 1):
                ak, bu = _rl_tracker_info(rl_cfg, t)
                status = f"[green]API ✓[/green]" if ak else "[red]no API key[/red]"
                console.print(f"  {i}. {t} — {status}  {bu}")
            sel = Prompt.ask("Select", choices=["0"] + [str(i) for i in range(1, len(rl_trackers) + 1)], default="0")
            if sel != "0":
                name = rl_trackers[int(sel) - 1]
                ak, bu = _rl_tracker_info(rl_cfg, name)
                user = Prompt.ask("Username", default=config.get("TRACKER_USERNAME") or "")
                n = name.upper()
                save_config("TRACKER_DEFAULT", n)
                save_config("TRACKER_BASE_URL", bu or "")
                save_config(f"TRACKER_{n}_URL", bu or "")
                save_config("TRACKER_USERNAME", user)
                if ak:
                    save_config("TRACKER_API_KEY", ak)
                config = load_config()

def validate_cookie(config: dict) -> bool:
    """Perform a HEAD request to the tracker to validate the cookie."""
    if not config.get("TRACKER_URL") or not (config.get("TRACKER_COOKIE") or config.get("TRACKER_COOKIE_VALUE")):
        return False
    
    base = config["TRACKER_URL"].rstrip("/")
    sess = _session(config)
    try:
        # Check uploader's torrents page or home
        r = sess.head(f"{base}/torrents", timeout=10, allow_redirects=False)
        # If we get a 200, it's valid. If we get a 302 to /login, it's invalid.
        if r.status_code == 200:
            return True
        dbg(f"Cookie validation failed: HTTP {r.status_code}")
        return False
    except Exception as e:
        dbg(f"Cookie validation error: {e}")
        return False

def validate_qbit(config: dict) -> bool:
    """Test connectivity to qBittorrent."""
    if not qbittorrentapi:
        dbg("qbittorrentapi not installed")
        return False
    if not config.get("QBIT_URL"):
        return False
    try:
        # CSI v1.6.4: Robust Client Initialization
        qbt = qbittorrentapi.Client(
            host=config["QBIT_URL"],
            username=config["QBIT_USER"],
            password=config["QBIT_PASS"],
            REQUESTS_ARGS={'timeout': (5, 10), 'headers': {'User-Agent': 'undici'}}
        )
        qbt.auth_log_in()
        return qbt.is_logged_in
    except Exception as e:
        dbg(f"qBit validation error: {e}")
        return False

def check_integrations_config(config: dict) -> dict:
    """
    CSI Auto-Configuration: Recon & Setup for TMDB, Sonarr, and Radarr.
    Prioriza descubrimiento en archivos de configuración, luego pregunta.
    """
    needs_save = False
    updates_to_propagate = {}

    def _recon_val(key: str, current: Optional[str]) -> Optional[str]:
        # Si ya lo tenemos en config y es válido, usarlo
        # FIX: Endurecer filtro de valores inválidos (YOUR_, None, vacíos)
        invalid_markers = ["tu_clave", "your_", "none", "null"]
        if current and current.strip() and not any(m in current.lower() for m in invalid_markers):
            return current
        
        # Búsqueda forense en archivos conocidos de la suite
        candidates = [BASE_DIR / ".env", BASE_DIR / "RawLoadrr" / ".env"]
        for p in candidates:
            if p.exists():
                try:
                    c = p.read_text(encoding="utf-8")
                    m = re.search(fr"^\s*{key}\s*=\s*['\"]?([^'\"]+)['\"]?", c, re.MULTILINE)
                    if m:
                        v = m.group(1).strip()
                        if v and not any(mk in v.lower() for mk in invalid_markers):
                            return v
                except:
                    pass
        return None

    console.print(Panel("[bold cyan]🕵️  RECON & AUTO-CONFIGURATION[/bold cyan]", border_style="cyan"))

    # 1. TMDB_API_KEY
    tmdb = _recon_val("TMDB_API_KEY", config.get("TMDB_API_KEY"))
    if tmdb:
        if tmdb != config.get("TMDB_API_KEY"):
            save_config("TMDB_API_KEY", tmdb)
            config["TMDB_API_KEY"] = tmdb
            needs_save = True
            updates_to_propagate["TMDB_API_KEY"] = tmdb
        console.print(f"[green]✓ [OK] TMDB detectado.[/green]")
    else:
        console.print("[yellow]⚠ TMDB API Key no encontrada.[/yellow]")
        val = Prompt.ask("TMDB API Key (v3)")
        if val:
            save_config("TMDB_API_KEY", val)
            config["TMDB_API_KEY"] = val
            needs_save = True
            updates_to_propagate["TMDB_API_KEY"] = val

    # 2. SONARR
    s_url = _recon_val("SONARR_URL", config.get("SONARR_URL"))
    s_key = _recon_val("SONARR_API_KEY", config.get("SONARR_API_KEY"))

    if s_url and s_key:
        if s_url != config.get("SONARR_URL") or s_key != config.get("SONARR_API_KEY"):
            save_config("SONARR_URL", s_url)
            save_config("SONARR_API_KEY", s_key)
            config["SONARR_URL"] = s_url
            config["SONARR_API_KEY"] = s_key
            needs_save = True
            updates_to_propagate["SONARR_URL"] = s_url
            updates_to_propagate["SONARR_API_KEY"] = s_key
        console.print(f"[green]✓ [OK] Sonarr detectado ({s_url}).[/green]")
    else:
        console.print("\n[bold]Configurando acceso a Sonarr...[/bold]")
        if Confirm.ask("¿Tienes Sonarr instalado?", default=True):
            s_url = Prompt.ask("Sonarr URL", default="http://localhost:8989")
            s_key = Prompt.ask("Sonarr API Key")
            if s_url and s_key:
                save_config("SONARR_URL", s_url)
                save_config("SONARR_API_KEY", s_key)
                config["SONARR_URL"] = s_url
                config["SONARR_API_KEY"] = s_key
                needs_save = True
                updates_to_propagate["SONARR_URL"] = s_url
                updates_to_propagate["SONARR_API_KEY"] = s_key

    # 3. RADARR
    r_url = _recon_val("RADARR_URL", config.get("RADARR_URL"))
    r_key = _recon_val("RADARR_API_KEY", config.get("RADARR_API_KEY"))

    if r_url and r_key:
        if r_url != config.get("RADARR_URL") or r_key != config.get("RADARR_API_KEY"):
            save_config("RADARR_URL", r_url)
            save_config("RADARR_API_KEY", r_key)
            config["RADARR_URL"] = r_url
            config["RADARR_API_KEY"] = r_key
            needs_save = True
            updates_to_propagate["RADARR_URL"] = r_url
            updates_to_propagate["RADARR_API_KEY"] = r_key
        console.print(f"[green]✓ [OK] Radarr detectado ({r_url}).[/green]")
    else:
        console.print("\n[bold]Configurando acceso a Radarr...[/bold]")
        if Confirm.ask("¿Tienes Radarr instalado?", default=True):
            r_url = Prompt.ask("Radarr URL", default="http://localhost:7878")
            r_key = Prompt.ask("Radarr API Key")
            if r_url and r_key:
                save_config("RADARR_URL", r_url)
                save_config("RADARR_API_KEY", r_key)
                config["RADARR_URL"] = r_url
                config["RADARR_API_KEY"] = r_key
                needs_save = True
                updates_to_propagate["RADARR_URL"] = r_url
                updates_to_propagate["RADARR_API_KEY"] = r_key

    if needs_save:
        console.print("[green]✓ Configuración guardada en .env[/green]")
        if updates_to_propagate:
            _propagate_config(updates_to_propagate)
        return load_config()
    return config

def check_essential_config(config: dict) -> dict:
    """Ensure mandatory v1.6.2 settings are present and valid (TUI Bootstrap)."""
    needs_save = False
    updates = {}
    
    # 1. Tracker Cookie
    cookie = config.get("TRACKER_COOKIE") or config.get("TRACKER_COOKIE_VALUE")
    if not cookie or not validate_cookie(config):
        console.print("[bold red]TRACKER_COOKIE missing or expired![/bold red]")
        new_cookie = Prompt.ask("Enter your tracker session cookie", default=cookie or "")
        if new_cookie:
            save_config("TRACKER_COOKIE", new_cookie)
            save_config("TRACKER_COOKIE_VALUE", new_cookie)
            config["TRACKER_COOKIE"] = new_cookie
            needs_save = True
            updates["TRACKER_COOKIE_VALUE"] = new_cookie

    # 2. qBittorrent
    if not validate_qbit(config):
        console.print("[bold yellow]qBittorrent connection failed or not configured.[/bold yellow]")
        new_qbit = Prompt.ask("qBittorrent URL", default=config.get("QBIT_URL") or "http://localhost:8888")
        new_user = Prompt.ask("qBit Username", default=config.get("QBIT_USER") or "admin")
        
        # Security: Do not echo password, don't pre-populate default unless empty
        new_pass = Prompt.ask("qBit Password", password=True)
        if not new_pass:
            new_pass = config.get("QBIT_PASS") or "adminadmin"
        
        save_config("QBIT_URL", new_qbit)
        save_config("QBIT_USER", new_user)
        save_config("QBIT_PASS", new_pass)
        config["QBIT_URL"] = new_qbit
        config["QBIT_USER"] = new_user
        config["QBIT_PASS"] = new_pass
        needs_save = True

    # 3. TMP Path
    if not os.path.exists(config.get("TMP_PATH", "")):
        console.print(f"[bold yellow]TMP_PATH not found: {config.get('TMP_PATH')}[/bold yellow]")
        new_tmp = Prompt.ask("Enter TMP path", default="/app/RawLoadrr/tmp")
        save_config("TMP_PATH", new_tmp)
        config["TMP_PATH"] = new_tmp
        needs_save = True

    if needs_save:
        if updates:
            _propagate_config(updates)
        return load_config()
    return config

# ─── INVESTIGATIONS ───────────────────────────────────────────────────────────
def tracker_investigation(config: dict):
    """
    CSI v2.0: Investigación principal con tracker.
    Integra carga/guardado del TrackerIndex (persistencia entre sesiones),
    máquina de estados completa y reportes de diagnóstico adicionales.
    """
    update_status("CSI", "Tracker Investigation", "STARTING")
    user = config.get("TRACKER_USERNAME", "").strip()
    if not user or user.lower() == "no username":
        console.print("[yellow]TRACKER_USERNAME is missing or set to 'no username'.[/yellow]")
        user = Prompt.ask("Enter your username on this tracker")
        if not user:
            return
        save_config("TRACKER_USERNAME", user)
        config["TRACKER_USERNAME"] = user
    console.print(Panel(
        f"Target: [bold cyan]{config['TRACKER_URL']}[/bold cyan]  "
        f"user:[bold]{config['TRACKER_USERNAME']}[/bold]",
        border_style="cyan",
    ))
    console.print("  a. Your Uploads\n  b. Global Search\n  r. Return")
    sub = Prompt.ask("Mode", choices=["a", "b", "r"], default="a")
    if sub == "r":
        return

    config = _confirm_scan_path(config)

    meta = MetadataManager(config)
    console.print("[cyan]Loading Sonarr / Radarr catalogs...[/cyan]")
    meta.load_sonarr()
    meta.load_radarr()

    tracker_index = TrackerIndex()
    do_global     = False

    if sub == "a":
        # CSI v2.0: Intentar cargar el índice persistido antes de reconstruir
        index_loaded = tracker_index.load_from_json(
            TRACKER_INDEX_PATH,
            tracker_url=config.get("TRACKER_URL", ""),
        )

        if index_loaded:
            console.print(
                "[dim green]▸ Índice cargado desde caché. "
                "Úsalo para esta sesión o reconstruye desde cero.[/dim green]"
            )
            rebuild = Confirm.ask("¿Reconstruir el índice desde el tracker?", default=False)
            if rebuild:
                tracker_index = TrackerIndex()  # Reset
                if not tracker_index.build_user(config):
                    return
        else:
            # No hay índice cacheado o es inválido → construir desde cero
            if not tracker_index.build_user(config):
                return

        subcat = "user"
    else:
        do_global = True
        subcat    = "global"
        console.print(
            "[yellow]Global mode: one API call per library item. "
            "Rate limiter active.[/yellow]"
        )

    # v1.6.5 + v2.0 + v3.0: Multi-codec scan con máquina de estados y path-first matching
    console.print("[cyan]Loading torrent client index...[/cyan]")
    _qbit_raw     = get_client_torrents(config)
    qbit_ok       = _qbit_raw is not None
    _client_map   = _qbit_raw if qbit_ok else {}
    _client_paths = set(_client_map.keys())

    if not qbit_ok:
        console.print(
            "[yellow]⚠ qBittorrent no disponible. Los ítems FALTA_CLIENTE se marcarán como "
            "INCIDENCIA hasta que el cliente vuelva a estar accesible.[/yellow]"
        )

    with LiveReport(subcat, config) as live:
        hevc_tv, h264_tv, hevc_m, h264_m, dupes, falta_cli, incidencias = forensic_scan(
            config, meta, tracker_index, do_global=do_global,
            client_paths=_client_paths, client_path_map=_client_map,
            qbit_available=qbit_ok, report=live,
        )

    update_status("CSI", "Tracker Investigation", "GENERATING_REPORTS")

    # CSI v2.0: Guardar el índice actualizado antes de generar reportes
    if sub == "a" and not do_global:
        tracker_index.save_to_json(TRACKER_INDEX_PATH)

    generate_reports(
        hevc_tv, h264_tv, hevc_m, h264_m, subcat, config,
        dupe_items=dupes,
        falta_cliente_items=falta_cli,
        incidencia_items=incidencias,
    )
    update_status("CSI", "Tracker Investigation", "FINISHED")

def local_investigation(config: dict):
    """
    CSI v2.0: Investigación local (sin tracker).
    Compara la biblioteca contra qBittorrent usando IDs de Sonarr/Radarr.
    El TrackerIndex se usa vacío (sin scraping) — solo cruce con cliente local.
    """
    update_status("CSI", "Local Investigation", "STARTING")
    config = _confirm_scan_path(config)
    console.print("[cyan]Loading torrent client index...[/cyan]")

    meta = MetadataManager(config)
    console.print("[cyan]Loading Sonarr / Radarr catalogs...[/cyan]")
    meta.load_sonarr()
    meta.load_radarr()

    tracker_index = TrackerIndex()
    console.print(
        "[yellow]Local mode: comparing library against torrent client. "
        "ID matching used where Sonarr/Radarr data is available.[/yellow]"
    )
    # v3.0: Build client_path_map for path-first matching
    _qbit_raw     = get_client_torrents(config)
    qbit_ok       = _qbit_raw is not None
    _client_map   = _qbit_raw if qbit_ok else {}
    _client_paths = set(_client_map.keys())
    if not qbit_ok:
        console.print(
            "[yellow]⚠ qBittorrent no disponible. Los ítems FALTA_CLIENTE se marcarán como "
            "INCIDENCIA hasta que el cliente vuelva a estar accesible.[/yellow]"
        )
    # v1.6.5 + v2.0 + v3.0: Multi-codec scan con máquina de estados
    with LiveReport("local", config) as live:
        hevc_tv, h264_tv, hevc_m, h264_m, dupes, falta_cli, incidencias = forensic_scan(
            config, meta, tracker_index, do_global=False,
            client_paths=_client_paths, client_path_map=_client_map,
            qbit_available=qbit_ok, report=live,
        )
    update_status("CSI", "Local Investigation", "GENERATING_REPORTS")
    generate_reports(
        hevc_tv, h264_tv, hevc_m, h264_m, "local", config,
        dupe_items=dupes,
        falta_cliente_items=falta_cli,
        incidencia_items=incidencias,
    )
    update_status("CSI", "Local Investigation", "FINISHED")

# ─── MAIN MENU ────────────────────────────────────────────────────────────────
def main_menu():
    _ensure_initialized()
    config = load_config()
    toggle_debug(config.get("DEBUG_MODE", False))
    config = check_integrations_config(config)
    config = check_essential_config(config)
    while True:
        welcome()
        config = load_config()
        toggle_debug(config.get("DEBUG_MODE", False))
        _status_panel(config)

        console.print(
            "\n  [bold]1.[/bold] Tracker Investigation"
            "\n  [bold]2.[/bold] Local Investigation"
            "\n  [bold]3.[/bold] Settings"
            "\n  [bold]0.[/bold] Exit\n"
        )
        choice = Prompt.ask("Mode", choices=["1", "2", "3", "0"], default="1")

        if choice == "0":
            sys.exit(0)

        elif choice == "3":
            configure_tracker(config)
            continue

        elif choice == "1":
            if not config["TRACKER_URL"]:
                console.print("[yellow]Tracker not configured. Use Settings (3) first.[/yellow]")
                time.sleep(2)
                continue
            if not config["TRACKER_API_KEY"]:
                console.print("[yellow]API key missing. Use Settings (3) to configure.[/yellow]")
                time.sleep(2)
                continue
            tracker_investigation(config)
            Prompt.ask("\n[dim]Press Enter to return to menu[/dim]", default="")

        elif choice == "2":
            local_investigation(config)
            Prompt.ask("\n[dim]Press Enter to return to menu[/dim]", default="")

# ─── ENTRY POINT ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted.[/dim]")
        sys.exit(0)
