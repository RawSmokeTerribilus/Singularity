# -*- coding: utf-8 -*-
"""Recordrr configuration.

Everything env-overridable, nothing hardcoded (multi-user, ships to the group).
Mirrors the singularity_config.py style: os.getenv with sane defaults.
"""
import os
from pathlib import Path

RECORDRR_ROOT = Path(__file__).resolve().parent.parent        # /app/Recordrr
APP_ROOT = RECORDRR_ROOT.parent                                # /app

# --- Display / capture geometry (Xvfb screen must match capture size) ---
DISPLAY = os.getenv("RECORDRR_DISPLAY", ":99")
SCREEN_W = int(os.getenv("RECORDRR_W", "1920"))
SCREEN_H = int(os.getenv("RECORDRR_H", "1080"))
SCREEN_DEPTH = int(os.getenv("RECORDRR_DEPTH", "24"))
FRAMERATE = int(os.getenv("RECORDRR_FPS", "30"))

# --- Audio: PulseAudio null sink; Chrome plays into it, ffmpeg grabs .monitor ---
PULSE_SINK = os.getenv("RECORDRR_SINK", "recordrr")

# --- GPU VAAPI encode (AMD Renoir radeonsi via /dev/dri passthrough) ---
VAAPI_DEVICE = os.getenv("RECORDRR_VAAPI", "/dev/dri/renderD128")
VIDEO_CODEC = os.getenv("RECORDRR_VCODEC", "h264_vaapi")   # or hevc_vaapi
QP = os.getenv("RECORDRR_QP", "22")
AUDIO_CODEC = os.getenv("RECORDRR_ACODEC", "aac")
AUDIO_BITRATE = os.getenv("RECORDRR_ABR", "192k")
CONTAINER_EXT = os.getenv("RECORDRR_EXT", "mkv")

# --- One-time interactive login view (x11vnc on the Xvfb display) ---
VNC_PORT = int(os.getenv("RECORDRR_VNC_PORT", "5900"))
# x11vnc -scale factor for the SERVED view (capture stays full-res). Empty = native.
# e.g. "0.75" or "1280x720" to fit a smaller viewer. Tune in the config menu.
VNC_SCALE = os.getenv("RECORDRR_VNC_SCALE", "")

# --- Browser: real Google Chrome (has Widevine CDM); per-user persistent profile ---
CHROME_CHANNEL = os.getenv("RECORDRR_CHROME_CHANNEL", "chrome")
PROFILES_DIR = Path(os.getenv("RECORDRR_PROFILES", str(RECORDRR_ROOT / "profiles")))
# Container runs non-root without a userns guarantee -> Chrome needs --no-sandbox.
# --kiosk: there is no window manager on the Xvfb display, so --start-maximized
# does nothing. Kiosk makes Chrome a borderless fullscreen app that fills :99
# exactly (no toolbar, no offset) -> clean full-frame capture without a WM.
CHROME_ARGS = [
    "--no-sandbox",
    "--disable-dev-shm-usage",        # belt-and-suspenders alongside shm_size: 2gb
    "--autoplay-policy=no-user-gesture-required",
    "--kiosk",
    "--window-position=0,0",
    f"--window-size={SCREEN_W},{SCREEN_H}",
]

# Opt-in remote debugging. Set RECORDRR_DEBUG_PORT=9222 to expose the DevTools
# protocol → with the container on network_mode: host, you then get FULL DevTools
# on the container's Chrome from your REAL desktop browser at http://localhost:9222
# (or chrome://inspect). Binds 127.0.0.1 only (host loopback, not LAN). Off by
# default — it's an inspection hole, only raise it while debugging.
DEBUG_PORT = os.getenv("RECORDRR_DEBUG_PORT", "")
if DEBUG_PORT:
    CHROME_ARGS.append(f"--remote-debugging-port={DEBUG_PORT}")
    CHROME_ARGS.append("--remote-debugging-address=127.0.0.1")

# --- Output: the mounted host Vídeos/PARA-IMPORTAR. SET THIS in config/.env. ---
# Inside the container the host path is preserved by the bind mount, so this must
# be the real host path (e.g. /home/<user>/Vídeos/PARA-IMPORTAR), not "~".
OUTPUT_DIR = Path(os.getenv("RECORDRR_OUTPUT", str(RECORDRR_ROOT / "output")))

# --- Logs (own dir, dashboard-visible via the recordrr logs volume) ---
LOGS_DIR = Path(os.getenv("RECORDRR_LOGS", str(RECORDRR_ROOT / "logs")))

# --- Adapter strategy packs (JSON, volume-mounted so edits need no rebuild) ---
ADAPTERS_DIR = Path(os.getenv("RECORDRR_ADAPTERS", str(RECORDRR_ROOT / "config" / "adapters")))

# --- Metadata sources (reuse Singularity's existing services) ---
SONARR_URL = os.getenv("SONARR_URL", "http://127.0.0.1:8989")
SONARR_API_KEY = os.getenv("SONARR_API_KEY", "")
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")

# --- Capture backend selection: "xvfb" (primary) | "obs" (fallback) ---
CAPTURE_BACKEND = os.getenv("RECORDRR_BACKEND", "xvfb")
OBS_WS_URL = os.getenv("RECORDRR_OBS_WS", "ws://127.0.0.1:4455")
OBS_WS_PASSWORD = os.getenv("RECORDRR_OBS_PW", "")


def ensure_dirs():
    """Create the writable dirs Recordrr needs. Safe to call repeatedly."""
    for d in (PROFILES_DIR, OUTPUT_DIR, LOGS_DIR, ADAPTERS_DIR):
        try:
            d.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
