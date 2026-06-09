#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Recordrr launcher — Rich TUI, reachable from the Singularity main menu (opt 9).

Run from /app:  python3 -m Recordrr.launcher

Provider-modular: the top menu pivots on the two things you actually do (grabar,
sesión) plus a Proveedores browser; POC primitives live under Diagnóstico. The
display lifecycle is auto-managed (see the owner contract below) so there's no
manual up/record/down sequence.

Display owner contract
----------------------
- Grabar: raises display+VNC if down; tears it down afterwards ONLY if it was the
  one that raised it (a running Sesión keeps its display). So unattended runs
  self-clean and close the netns-leak window (asbuilt gotcha #4).
- Sesión: raises display+VNC and leaves it up (you're logging in / browsing).
- Leaving Recordrr ([0]): always tears the display down — nothing needs :99 once
  you're out.
"""
import os
import subprocess
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

try:
    from Recordrr.config import recordrr_config as cfg
    from Recordrr.modules.adapter import Adapter
    from Recordrr.modules import display as disp
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from Recordrr.config import recordrr_config as cfg
    from Recordrr.modules.adapter import Adapter
    from Recordrr.modules import display as disp

try:
    from core.status_manager import update_status
except Exception:
    def update_status(*a, **k):
        pass

console = Console()
APP_ROOT = cfg.APP_ROOT
PY = sys.executable or "python3"
ENV_PATH = APP_ROOT / ".env"

# Knobs surfaced in the Ajustes menu: (env key, label, secret?)
CONFIG_KEYS = [
    ("RECORDRR_OUTPUT", "Salida (carpeta destino)", False),
    ("RECORDRR_W", "Ancho captura", False),
    ("RECORDRR_H", "Alto captura", False),
    ("RECORDRR_FPS", "FPS", False),
    ("RECORDRR_VCODEC", "Códec vídeo (h264_vaapi/hevc_vaapi)", False),
    ("RECORDRR_QP", "Calidad QP", False),
    ("RECORDRR_VNC_SCALE", "VNC escala (ej 0.75 / 1280x720, vacío=nativo)", False),
    ("RECORDRR_BACKEND", "Backend (xvfb/obs)", False),
    ("SONARR_URL", "Sonarr URL", False),
    ("SONARR_API_KEY", "Sonarr API key", True),
    ("TMDB_API_KEY", "TMDB API key", True),
]


# ---- subprocess + env helpers -------------------------------------------
def _run_module(module: str, *args) -> int:
    cmd = [PY, "-m", module, *[str(a) for a in args]]
    return subprocess.run(cmd, cwd=str(APP_ROOT)).returncode


def _write_env_key(key: str, value: str) -> None:
    """Persist key=value to /app/.env and update os.environ so subprocesses see it."""
    import os
    lines, found = [], False
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            if line.strip().startswith(f"{key}="):
                lines.append(f"{key}={value}"); found = True
            else:
                lines.append(line)
    if not found:
        lines.append(f"{key}={value}")
    ENV_PATH.write_text("\n".join(lines) + "\n")
    os.environ[key] = value


def _cur(key, default=""):
    import os
    return os.environ.get(key, default)


# ---- display lifecycle (the owner contract) -----------------------------
def _display_up() -> bool:
    return disp._alive("xvfb")


def _ensure_display() -> bool:
    """Raise display+audio+VNC if down. Returns True if WE raised it (caller owns
    the teardown), False if it was already up (someone else owns it)."""
    if _display_up():
        return False
    console.print("[dim]Levantando display virtual + audio + VNC…[/dim]")
    disp.up(with_vnc=True)
    console.print("[dim]VNC: apunta el viewer a 127.0.0.1:5900 (sin audio — es normal).[/dim]")
    return True


def _display_down():
    if _display_up():
        disp.down()
        console.print("[green]Display abajo (escritorio normal; cerrada la fuga netns).[/green]")


# ---- provider helpers ----------------------------------------------------
def _provider_rows():
    """[(name, Adapter|None, status_str)] for every adapter JSON."""
    rows = []
    for name in Adapter.available():
        try:
            a = Adapter.load(name)
            status = "[yellow]STUB (sin tunear)[/yellow]" if a.untuned else "[green]listo[/green]"
            rows.append((name, a, status))
        except Exception as e:
            rows.append((name, None, f"[red]error: {e}[/red]"))
    return rows


def _providers_inline() -> str:
    """One-line provider summary for the main banner."""
    parts = []
    for name, a, _ in _provider_rows():
        if a is None:
            parts.append(f"[red]{name}!"); continue
        mark = "[yellow]⚠[/yellow]" if (a and a.untuned) else "[green]✓[/green]"
        parts.append(f"{a.display if a else name} {mark}")
    return "  ".join(parts) or "[dim](ninguno)[/dim]"


def _pick_provider(prompt="Proveedor"):
    rows = _provider_rows()
    if not rows:
        console.print("[red]No hay adapters en config/adapters/. Añade un .json primero.[/red]")
        Prompt.ask("Enter", default=""); return None
    t = Table(box=None, show_header=True, header_style="bold magenta")
    t.add_column("#", justify="right"); t.add_column("Proveedor"); t.add_column("Estado")
    for i, (name, a, status) in enumerate(rows, 1):
        t.add_row(str(i), (a.display if a else name), status)
    console.print(t)
    sel = Prompt.ask(prompt + "  #", choices=[str(i) for i in range(1, len(rows) + 1)], default="1")
    return rows[int(sel) - 1][0]


# ---- top actions ---------------------------------------------------------
def _grabar(adapter_name=None):
    name = adapter_name or _pick_provider("Grabar con")
    if not name:
        return
    adapter = Adapter.load(name)
    if adapter.untuned:
        console.print(f"[yellow]Aviso: '{adapter.display}' es un STUB sin tunear — "
                      "los selectores casi seguro fallan. Útil para probar login/DOM.[/yellow]")
    show = Prompt.ask("Serie  [dim](como en Sonarr)[/dim]").strip()
    if not show:
        return
    season = Prompt.ask("Temporada  [dim](Enter = todas)[/dim]", default="").strip()
    start = Prompt.ask("Primer episodio", default="1").strip()
    count = Prompt.ask("Cuántos  [dim](0 = todos desde el primero)[/dim]", default="0").strip()
    profile = Prompt.ask("Perfil Chrome", default=name).strip() or name
    args = [show, "--adapter", name, "--start", start, "--count", count, "--profile", profile]
    if season:
        args += ["--season", season]

    _ensure_display()
    console.print("[yellow]Chrome arrancará en el display virtual. VNC in, login si "
                  "hace falta y ARRANCA EL EPISODIO 1 — graba sola al detectar play.[/yellow]")
    try:
        _run_module("Recordrr.modules.orchestrator", *args)
    finally:
        # A finished/stopped recording never needs :99 — ALWAYS tear it down to
        # close the netns X11 leak that poisons host Flatpak VLC (§12.1). The login
        # lives in the profile dir on disk, not the display, so nothing is lost.
        # (Previously torn down only "if we raised it" → a display left up by an
        # earlier Sesión/diag survived STOP and leaked; user had to kill it by hand.)
        _display_down()
    Prompt.ask("\nEnter para volver", default="")


def _grabar_pelicula(adapter_name=None):
    """Movie capture — single asset, Radarr metadata, same ad-pause + segment-concat
    engine as series. No season/episode loop; the player has no autoplay-next so the
    record ends on the movie's own near_end (the boundary backstop still covers a
    credits→'Up Next' src-swap)."""
    name = adapter_name or _pick_provider("Grabar con")
    if not name:
        return
    adapter = Adapter.load(name)
    if adapter.untuned:
        console.print(f"[yellow]Aviso: '{adapter.display}' es un STUB sin tunear — "
                      "los selectores casi seguro fallan. Útil para probar login/DOM.[/yellow]")
    movie = Prompt.ask("Película  [dim](como en Radarr)[/dim]").strip()
    if not movie:
        return
    profile = Prompt.ask("Perfil Chrome", default=name).strip() or name
    args = [movie, "--movie", "--adapter", name, "--profile", profile]

    _ensure_display()
    console.print("[yellow]Chrome arrancará en el display virtual. VNC in, login si "
                  "hace falta, navega a la película, dale PLAY y pulsa ⏺ REC.[/yellow]")
    try:
        _run_module("Recordrr.modules.orchestrator", *args)
    finally:
        _display_down()
    Prompt.ask("\nEnter para volver", default="")


def _grabar_tv(adapter_name=None):
    """Live-TV capture — linear channel, EPG wall-clock boundaries. Reuses the
    same capture + ad-pause + flight engine as series/movie; the index is the
    provider's in-page guide (no arr). Triage: channel → modo → nombrado."""
    name = adapter_name or _pick_provider("Grabar TV con")
    if not name:
        return
    adapter = Adapter.load(name)
    channel = Prompt.ask(
        "Canal  [dim](nombre/número, o Enter = lo sintonizo yo en VNC)[/dim]",
        default="").strip() or "auto"
    console.print(
        "  [bold]Modo[/bold]: "
        "[cyan]1[/cyan] un programa  ·  "
        "[cyan]2[/cyan] por reloj (trozos de N min)  ·  "
        "[cyan]3[/cyan] hasta que vuelva (archivo continuo, corta por programa)")
    mode_sel = Prompt.ask("Modo", choices=["1", "2", "3"], default="3")
    mode = {"1": "single", "2": "clock", "3": "till"}[mode_sel]
    chunk = "30"
    if mode == "clock":
        chunk = Prompt.ask("Minutos por archivo", default="30").strip() or "30"
    nm_sel = Prompt.ask("Nombrado  [dim](1 = adivinar de la guía+TMDB, 2 = lo nombro yo)[/dim]",
                        choices=["1", "2"], default="1")
    naming = "guess" if nm_sel == "1" else "name"
    override = ""
    if naming == "name":
        override = Prompt.ask("Nombre base").strip()
    profile = Prompt.ask("Perfil Chrome", default=name).strip() or name

    args = [channel, "--live", "--adapter", name, "--mode", mode,
            "--naming", naming, "--profile", profile]
    if mode == "clock":
        args += ["--chunk", chunk]
    if naming == "name" and override:
        args += ["--override", override]

    _ensure_display()
    console.print("[yellow]Chrome arrancará en el display virtual. VNC in (127.0.0.1:5900), "
                  "login si hace falta, espera a que cargue el canal y pulsa ⏺ REC.[/yellow]")
    console.print("[dim]Continuo: pulsa REC una vez y déjalo; corta y nombra cada programa "
                  "solo. Parar: 'q' o ⏹ STOP (NUNCA Ctrl-C).[/dim]")
    try:
        _run_module("Recordrr.modules.orchestrator", *args)
    finally:
        _display_down()
    Prompt.ask("\nEnter para volver", default="")


def _sesion(adapter_name=None):
    name = adapter_name or _pick_provider("Sesión en")
    if not name:
        return
    adapter = Adapter.load(name)
    profile = Prompt.ask("Perfil Chrome", default=name).strip() or name
    _ensure_display()    # leave it up — exit handler tears down
    console.print(f"[yellow]Chrome en {adapter.url} (perfil '{profile}'). "
                  "Logueate / navega en VNC. Ctrl-C en esta consola cierra Chrome.[/yellow]")
    _run_module("Recordrr.modules.browser", adapter.url, profile)
    Prompt.ask("\nEnter para volver", default="")


# ---- Proveedores submenu -------------------------------------------------
def _new_provider():
    import json
    src = Prompt.ask("Clonar desde  [dim](base)[/dim]", default="pluto").strip()
    try:
        base = Adapter.load(src).spec
    except Exception as e:
        console.print(f"[red]No puedo cargar '{src}': {e}[/red]"); return
    name = Prompt.ask("Nombre nuevo  [dim](minúsculas, sin espacios)[/dim]").strip().lower()
    if not name:
        return
    disp_name = Prompt.ask("Nombre visible", default=name.title()).strip() or name.title()
    url = Prompt.ask("URL del servicio", default="https://").strip()
    spec = dict(base)
    spec.update({"service": name, "display": disp_name, "url": url, "_untuned": True,
                 "_note": f"STUB clonado de {src} — tunear selectores con drift en vivo."})
    out = cfg.ADAPTERS_DIR / f"{name}.json"
    out.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    console.print(f"[green]✓ {out.name} creado (STUB). Edítalo y corre drift.[/green]")


def _manage_provider(name):
    while True:
        a = Adapter.load(name)
        ctl = ", ".join(a.controls.keys()) or "(ninguno)"
        console.print(Panel(
            f"  Proveedor : [magenta]{a.display}[/magenta]  ({name})\n"
            f"  URL       : {a.url}\n"
            f"  Estado    : {'[yellow]STUB sin tunear[/yellow]' if a.untuned else '[green]listo[/green]'}\n"
            f"  Controles : [cyan]{ctl}[/cyan]\n"
            f"  JSON      : [dim]{cfg.ADAPTERS_DIR / (name + '.json')}[/dim]\n\n"
            "  [bold green]\\[g][/bold green] Grabar    [bold cyan]\\[s][/bold cyan] Sesión/login\n"
            "  [bold cyan]\\[d][/bold cyan] Drift (abrir y comprobar selectores)\n"
            "  [bold cyan][0][/bold cyan] Volver",
            title=f"[bold magenta]Proveedor — {a.display}[/bold magenta]", border_style="magenta"))
        sel = Prompt.ask("acción", choices=["g", "s", "d", "0"], default="0")
        if sel == "0":
            return
        elif sel == "g":
            _grabar(name); return
        elif sel == "s":
            _sesion(name); return
        elif sel == "d":
            raised = _ensure_display()
            console.print("[dim]Abriendo Chrome; el drift real (controles rotos) se "
                          "reporta también al iniciar Grabar.[/dim]")
            try:
                _run_module("Recordrr.modules.browser", a.url, name)
            finally:
                if raised:
                    _display_down()
            Prompt.ask("\nEnter para volver", default="")


def _providers_menu():
    while True:
        rows = _provider_rows()
        t = Table(box=None, show_header=True, header_style="bold magenta")
        t.add_column("#", justify="right"); t.add_column("Proveedor")
        t.add_column("Estado"); t.add_column("URL", style="dim")
        for i, (name, a, status) in enumerate(rows, 1):
            t.add_row(str(i), (a.display if a else name), status, (a.url if a else ""))
        console.print()
        console.print(Panel(t, title="[bold magenta]RECORDRR — Proveedores[/bold magenta]",
                            border_style="magenta",
                            subtitle="[dim][#] gestionar · [+] nuevo · [0] volver[/dim]"))
        choices = [str(i) for i in range(1, len(rows) + 1)] + ["+", "0"]
        sel = Prompt.ask("seleccion", choices=choices, default="0")
        if sel == "0":
            return
        elif sel == "+":
            _new_provider()
        else:
            _manage_provider(rows[int(sel) - 1][0])


# ---- Diagnóstico submenu: display primitives + the analytics/recon suite ---
def _flight_logs():
    """All flight .jsonl, newest first."""
    d = cfg.LOGS_DIR / "flight"
    return sorted(d.glob("*.jsonl"), reverse=True) if d.exists() else []


def _diag_menu():
    while True:
        console.print()
        console.print(Panel(
            f"  display :09  [{'[green]ARRIBA[/green]' if _display_up() else '[dim]abajo[/dim]'}]\n\n"
            "  [dim]— Display / captura —[/dim]\n"
            "  [bold cyan][1][/bold cyan] Levantar display + audio + VNC\n"
            "  [bold cyan][2][/bold cyan] Bajar display\n"
            "  [bold cyan][3][/bold cyan] Capturar N segundos  [dim](prueba manual)[/dim]\n"
            "  [bold cyan][4][/bold cyan] Abrir Chrome en una URL libre\n\n"
            "  [dim]— Análisis (pasivo, sin display) —[/dim]\n"
            "  [bold cyan][5][/bold cyan] Veredictos de vuelo  [dim](flightcheck — revisa todas las grabaciones)[/dim]\n"
            "  [bold cyan][6][/bold cyan] Ver un log de vuelo  [dim](timeline poll-a-poll)[/dim]\n\n"
            "  [dim]— Recon en vivo (necesita VNC + reproducción) —[/dim]\n"
            "  [bold cyan][7][/bold cyan] Diag de audio    [dim](audiodiag — qué acción quita el mute real)[/dim]\n"
            "  [bold cyan][8][/bold cyan] Diag de capas    [dim](layerdiag — DOM de anuncios/overlays en vivo)[/dim]\n"
            "  [bold cyan][9][/bold cyan] Sondear selectores [dim](probe — vuelca los controles del player)[/dim]\n\n"
            "  [bold cyan][0][/bold cyan] Volver",
            title="[bold cyan]RECORDRR — Diagnóstico[/bold cyan]", border_style="cyan"))
        sel = Prompt.ask("diag", choices=[str(i) for i in range(10)], default="0")
        if sel == "0":
            return
        elif sel == "1":
            disp.up(with_vnc=True)
            console.print("[green]Display arriba. VNC: 127.0.0.1:5900[/green]")
            Prompt.ask("\nEnter", default="")
        elif sel == "2":
            _display_down(); Prompt.ask("\nEnter", default="")
        elif sel == "3":
            default_out = str(cfg.OUTPUT_DIR / "poc.mkv")
            out = Prompt.ask("Archivo salida", default=default_out).strip() or default_out
            secs = Prompt.ask("Segundos", default="60").strip()
            _run_module("Recordrr.modules.capture", out, secs)
            Prompt.ask("\nEnter", default="")
        elif sel == "4":
            url = Prompt.ask("URL", default="https://pluto.tv/").strip()
            profile = Prompt.ask("Perfil", default="default").strip() or "default"
            raised = _ensure_display()
            try:
                _run_module("Recordrr.modules.browser", url, profile)
            finally:
                if raised:
                    _display_down()
        elif sel == "5":
            # flightcheck: pure offline read of LOGS_DIR/flight — no display.
            verbose = Prompt.ask("¿Detalle por hallazgo? (s/n)", default="n").strip().lower()
            args = ["--verbose"] if verbose.startswith("s") else []
            _run_module("Recordrr.modules.flightcheck", *args)
            Prompt.ask("\nEnter", default="")
        elif sel == "6":
            logs = _flight_logs()
            if not logs:
                console.print(f"[yellow]No hay logs de vuelo en {cfg.LOGS_DIR / 'flight'}.[/yellow]")
                Prompt.ask("\nEnter", default=""); continue
            t = Table(box=None, show_header=True, header_style="bold cyan")
            t.add_column("#", justify="right"); t.add_column("Log (más reciente primero)")
            for i, p in enumerate(logs[:20], 1):
                t.add_row(str(i), p.name)
            console.print(t)
            pick = Prompt.ask("Log #", choices=[str(i) for i in range(1, min(len(logs), 20) + 1)], default="1")
            _run_module("Recordrr.modules.flightrecorder", str(logs[int(pick) - 1]))
            Prompt.ask("\nEnter", default="")
        elif sel in ("7", "8", "9"):
            # Live recon: these own their display (raise+teardown per the owner
            # contract), so we DON'T raise it here. They wait for VNC playback.
            name = _pick_provider("Proveedor a inspeccionar")
            if not name:
                continue
            profile = Prompt.ask("Perfil Chrome", default=name).strip() or name
            if sel == "7":
                _run_module("Recordrr.modules.audiodiag", name, profile)
            elif sel == "8":
                _run_module("Recordrr.modules.layerdiag", name, profile)
            else:
                # probe is browser-side, gated by RECORDRR_PROBE in the POC loop.
                os.environ["RECORDRR_PROBE"] = name
                adapter = Adapter.load(name)
                raised = _ensure_display()
                try:
                    _run_module("Recordrr.modules.browser", adapter.url, profile)
                finally:
                    os.environ.pop("RECORDRR_PROBE", None)
                    if raised:
                        _display_down()
            Prompt.ask("\nEnter", default="")


# ---- Ajustes (config + proveedores) --------------------------------------
def _ajustes_menu():
    """Ajustes = the env config editor + Proveedores (moved in here so the top
    menu stays all-numeric: 1/2/3 grabar, 4 ajustes, 5 diag — no letter keys)."""
    while True:
        console.print()
        console.print(Panel(
            "  [bold cyan][1][/bold cyan] Configuración  [dim](.env: salida, códec, claves…)[/dim]\n"
            "  [bold cyan][2][/bold cyan] Proveedores    [dim](gestionar / añadir / drift / sesión)[/dim]\n"
            "  [bold cyan][0][/bold cyan] Volver",
            title="[bold yellow]RECORDRR — Ajustes[/bold yellow]", border_style="yellow"))
        sel = Prompt.ask("ajustes", choices=["1", "2", "0"], default="0")
        if sel == "0":
            return
        elif sel == "1":
            _env_config_menu()
        elif sel == "2":
            _providers_menu()


def _env_config_menu():
    while True:
        t = Table(box=None, show_header=True, header_style="bold yellow")
        t.add_column("#", justify="right"); t.add_column("Ajuste"); t.add_column("Valor")
        for i, (key, label, secret) in enumerate(CONFIG_KEYS, 1):
            v = _cur(key)
            shown = ("…" + v[-6:]) if (secret and len(v) > 6) else (v or "[dim](vacío)[/dim]")
            t.add_row(str(i), label, shown)
        console.print()
        console.print(Panel(t, title="[bold yellow]RECORDRR — Ajustes[/bold yellow]",
                            border_style="yellow", subtitle="[dim]se guarda en .env[/dim]"))
        sel = Prompt.ask("Editar #  [dim](0 = volver)[/dim]",
                         choices=["0"] + [str(i) for i in range(1, len(CONFIG_KEYS) + 1)],
                         default="0")
        if sel == "0":
            return
        key, label, secret = CONFIG_KEYS[int(sel) - 1]
        val = Prompt.ask(f"Nuevo valor para [bold]{label}[/bold]", password=secret).strip()
        if val:
            _write_env_key(key, val)
            console.print(f"[green]✓ {key} guardado (aplica a próximas grabaciones)[/green]")


# ---- main menu -----------------------------------------------------------
def _banner():
    console.print()
    console.print(Panel(
        f"  Salida   : [green]{_cur('RECORDRR_OUTPUT', str(cfg.OUTPUT_DIR))}[/green]\n"
        f"  Captura  : [cyan]{cfg.SCREEN_W}x{cfg.SCREEN_H}@{cfg.FRAMERATE}  "
        f"{cfg.VIDEO_CODEC} qp{cfg.QP}[/cyan]  backend=[yellow]{cfg.CAPTURE_BACKEND}[/yellow]  "
        f"display=[{'[green]ON[/green]' if _display_up() else '[dim]off[/dim]'}]\n"
        f"  Provs    : {_providers_inline()}\n\n"
        "  [bold green][1][/bold green]  Grabar Serie           [dim](proveedor → serie)[/dim]\n"
        "  [bold green][2][/bold green]  Grabar Película        [dim](proveedor → película)[/dim] [yellow][WIP][/yellow]\n"
        "  [bold green][3][/bold green]  Grabar TV              [dim](canal en vivo → modo → nombrado)[/dim]\n"
        "  [bold yellow][4][/bold yellow]  Ajustes                [dim](configuración / proveedores)[/dim]\n"
        "  [bold cyan][5][/bold cyan]  Diagnóstico            [dim](display / captura manual)[/dim]\n"
        "  [bold cyan][0][/bold cyan]  Atrás\n"
        "  [dim]Salir de Recordrr: [0]. Parar una grabación: tecla 'q' (NUNCA Ctrl-C).[/dim]",
        title="[bold magenta]RECORDRR — captura por navegador[/bold magenta]",
        border_style="magenta",
    ))


def main():
    cfg.ensure_dirs()
    update_status("RECORDRR", "Launcher", "EN LÍNEA", details=f"backend={cfg.CAPTURE_BACKEND}")
    try:
        while True:
            _banner()
            sel = Prompt.ask("root@singularidad:recordrr",
                             choices=["1", "2", "3", "4", "5", "0"], default="0")
            if sel == "0":
                break
            elif sel == "1":
                _grabar()
            elif sel == "2":
                _grabar_pelicula()
            elif sel == "3":
                _grabar_tv()
            elif sel == "4":
                _ajustes_menu()
            elif sel == "5":
                _diag_menu()
    finally:
        # leaving Recordrr → tear down the display so the netns-leak window closes.
        _display_down()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Recordrr cerrado.[/yellow]")
        try:
            _display_down()
        except Exception:
            pass
        sys.exit(0)
