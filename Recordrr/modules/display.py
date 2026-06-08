# -*- coding: utf-8 -*-
"""Virtual display + audio + VNC lifecycle for Recordrr.

Brings up:
  - Xvfb on RECORDRR_DISPLAY at the configured geometry (the canvas Chrome paints
    onto and ffmpeg x11grab records).
  - A PulseAudio null sink named RECORDRR_SINK; Chrome plays into it and ffmpeg
    records its `.monitor` source -> clean audio without touching host output.
  - x11vnc on the display (optional) so a human can VNC in once to log into the
    streaming service. After login the persistent Chrome profile remembers it.

Run standalone:
    python3 -m Recordrr.modules.display up      # start Xvfb + pulse (+ vnc)
    python3 -m Recordrr.modules.display down     # tear everything down
    python3 -m Recordrr.modules.display up --vnc # also expose x11vnc for login
"""
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

try:
    from Recordrr.config import recordrr_config as cfg
except ImportError:  # allow `python3 modules/display.py` from within Recordrr/
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from Recordrr.config import recordrr_config as cfg

_PIDFILE_DIR = Path("/tmp/recordrr")


def _pidfile(name: str) -> Path:
    _PIDFILE_DIR.mkdir(parents=True, exist_ok=True)
    return _PIDFILE_DIR / f"{name}.pid"


def _spawn(name: str, cmd: list, env=None) -> int:
    """Start a detached background process, record its pid, return it."""
    log = open(_PIDFILE_DIR / f"{name}.out", "ab")
    proc = subprocess.Popen(
        cmd, stdout=log, stderr=subprocess.STDOUT,
        env=env or os.environ.copy(), start_new_session=True,
    )
    _pidfile(name).write_text(str(proc.pid))
    return proc.pid


def _alive(name: str) -> bool:
    pf = _pidfile(name)
    if not pf.exists():
        return False
    try:
        os.kill(int(pf.read_text().strip()), 0)
        return True
    except (OSError, ValueError):
        return False


def _kill(name: str):
    pf = _pidfile(name)
    if not pf.exists():
        return
    try:
        os.kill(int(pf.read_text().strip()), signal.SIGTERM)
    except (OSError, ValueError):
        pass
    finally:
        pf.unlink(missing_ok=True)


def start_xvfb() -> str:
    if _alive("xvfb"):
        return cfg.DISPLAY
    screen = f"{cfg.SCREEN_W}x{cfg.SCREEN_H}x{cfg.SCREEN_DEPTH}"
    # NOTE: netns isolation of Xvfb (unshare --net) was tried to stop the host
    # netns X11-abstract-socket leak, but Chrome's X client only uses the
    # abstract socket and won't fall back to the filesystem one -> "Missing X
    # server". So Xvfb must stay in the shared netns. The leak is handled
    # operationally for now (bring :99 down when not recording); the real fix
    # (task #5) is a bridge-networked sidecar, not netns isolation here.
    cmd = ["Xvfb", cfg.DISPLAY, "-screen", "0", screen, "-nolisten", "tcp", "-ac"]
    _spawn("xvfb", cmd)
    # Wait for the display socket to exist.
    sock = f"/tmp/.X11-unix/X{cfg.DISPLAY.lstrip(':')}"
    for _ in range(50):
        if os.path.exists(sock):
            break
        time.sleep(0.1)
    return cfg.DISPLAY


def start_pulse() -> str:
    """Start a user PulseAudio daemon + null sink; return the monitor source name."""
    monitor = f"{cfg.PULSE_SINK}.monitor"
    # Idempotent: if the sink already exists we're done.
    have = subprocess.run(["pactl", "list", "short", "sinks"],
                          capture_output=True, text=True)
    if cfg.PULSE_SINK in have.stdout:
        return monitor
    subprocess.run(["pulseaudio", "--start", "--exit-idle-time=-1"],
                   capture_output=True, text=True)
    subprocess.run([
        "pactl", "load-module", "module-null-sink",
        f"sink_name={cfg.PULSE_SINK}",
        f"sink_properties=device.description={cfg.PULSE_SINK}",
    ], capture_output=True, text=True)
    subprocess.run(["pactl", "set-default-sink", cfg.PULSE_SINK],
                   capture_output=True, text=True)
    return monitor


def start_vnc():
    if _alive("x11vnc"):
        return cfg.VNC_PORT
    env = os.environ.copy()
    env["DISPLAY"] = cfg.DISPLAY
    cmd = [
        "x11vnc", "-display", cfg.DISPLAY, "-rfbport", str(cfg.VNC_PORT),
        "-localhost", "-forever", "-shared", "-nopw", "-quiet",
        # Chrome's GPU-composited repaints often emit no XDAMAGE, so the injected
        # bar/clock didn't refresh live until reconnect. Poll instead.
        "-noxdamage",
    ]
    if cfg.VNC_SCALE:                      # downscale the served view to fit the viewer
        cmd += ["-scale", cfg.VNC_SCALE]
    _spawn("x11vnc", cmd, env=env)
    return cfg.VNC_PORT


def up(with_vnc: bool = False) -> dict:
    cfg.ensure_dirs()
    disp = start_xvfb()
    monitor = start_pulse()
    info = {"display": disp, "audio_monitor": monitor}
    if with_vnc:
        info["vnc_port"] = start_vnc()
    return info


def down():
    for name in ("x11vnc", "xvfb"):
        _kill(name)
    # Leave PulseAudio running; unloading the sink is cheap and avoids races.
    subprocess.run(["pactl", "unload-module", "module-null-sink"],
                   capture_output=True, text=True)


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "up"
    if action == "down":
        down()
        print("Recordrr display: down")
    else:
        info = up(with_vnc=("--vnc" in sys.argv))
        print("Recordrr display: up")
        for k, v in info.items():
            print(f"  {k}: {v}")
        if "vnc_port" in info:
            print(f"\n  VNC -> tunnel & connect:  ssh -L 5900:127.0.0.1:{info['vnc_port']} <host>")
            print("  then point a VNC viewer at 127.0.0.1:5900 to log in once.")
