#!/usr/bin/env python3
import os
import sys
import time
import random
import logging
import subprocess
import threading
from pathlib import Path
from datetime import datetime
from rich.console import Console

from core.status_manager import update_status
from core.dashboard import run_dashboard
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, IntPrompt
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
from rich.align import Align
from rich.rule import Rule

from singularity_config import GOD_PHRASES, MSG_NUEVO, ID_INICIO, ID_FIN, LOGS_DIR, BASE_URL, COOKIE_VALUE, IMGBB_API, PTSCREENS_API

console = Console()
BASE_DIR = Path(__file__).parent


#redimensionar pantalla

def setup_terminal():
    """Configura el entorno visual de la terminal."""
    try:
        # 1. Limpiar pantalla para resetear el buffer
        os.system('clear')
        
        # 2. Redimensionar: 40 filas, 120 columnas
        # \x1b[8;{rows};{cols}t -> Redimensionar
        # \x1b[3;0;0t         -> Mover a la posición 0,0 (opcional)
        sys.stdout.write("\x1b[8;40;120t")
        sys.stdout.write("\x1b[3;0;0t") 
        sys.stdout.flush()
        
        # 3. Poner título a la ventana (aunque estés en Docker, el TTY lo propaga)
        sys.stdout.write("\033]0;S I N G U L A R I T Y   C O R E\007")
        sys.stdout.flush()
        
    except Exception:
        # Si falla (por ejemplo en un log sin TTY), que no rompa el programa
        pass

# Ejecutar la configuración visual
setup_terminal()

# ------------------------------------------------------------------ #
#  Logging (logs/singularity_YYYY-MM-DD.log)                         #
# ------------------------------------------------------------------ #

def _setup_logger() -> logging.Logger:
    log_path = Path(LOGS_DIR) / f"singularity_{datetime.now().strftime('%Y-%m-%d')}.log"
    logger = logging.getLogger("singularity")
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(
            "[%(asctime)s] %(levelname)-8s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        ))
        logger.addHandler(fh)
    return logger


log = _setup_logger()


# ------------------------------------------------------------------ #
#  Subprocess helper                                                  #
# ------------------------------------------------------------------ #

def _run(cmd: list, cwd: Path = None) -> int:
    cwd_path = str(cwd or BASE_DIR)
    log.info(f"RUN: {' '.join(str(c) for c in cmd)} (cwd={cwd_path})")
    result = subprocess.run(cmd, cwd=cwd_path)
    log.info(f"EXIT: {result.returncode}")
    return result.returncode


# ------------------------------------------------------------------ #
#  Boot sequence                                                      #
# ------------------------------------------------------------------ #

def boot_sequence():
    clear_screen()
    intro_art = """
    [bold cyan]
    ░██████╗██╗███╗   ██╗ ██████╗ ██╗   ██╗██╗      █████╗ ██████╗ ██╗████████╗██╗   ██╗
    ██╔════╝██║████╗  ██║██╔════╝ ██║   ██║██║     ██╔══██╗██╔══██╗██║╚══██╔══╝╚██╗ ██╔╝
    ╚█████╗ ██║██╔██╗ ██║██║  ███╗██║   ██║██║     ███████║██████╔╝██║   ██║    ╚████╔╝ 
     ╚═══██╗██║██║╚██╗██║██║   ██║██║   ██║██║     ██╔══██║██╔══██╗██║   ██║     ╚██╔╝  
    ██████╔╝██║██║ ╚████║╚██████╔╝╚██████╔╝███████╗██║  ██║██║  ██║██║   ██║      ██║   
    ╚═════╝ ╚═╝╚═╝  ╚═══╝ ╚═════╝  ╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝   ╚═╝      ╚═╝   
    [/bold cyan]
    """
    with Live(Align.center(intro_art), refresh_per_second=4):
        time.sleep(1)

    with Progress(SpinnerColumn("dots12"), TextColumn("[bold yellow]{task.description}"), console=console) as progress:
        task = progress.add_task("Mapeando sectores de memoria...", total=100)
        while not progress.finished:
            time.sleep(0.01)
            progress.update(task, advance=2)

    console.print(Align.center(f"[italic white]'{random.choice(GOD_PHRASES)}'[/italic white]\n"))
    log.info("Singularity boot sequence completed")
    time.sleep(0.8)


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


# ------------------------------------------------------------------ #
#  Sub-menú 1 — MKVerything                                          #
# ------------------------------------------------------------------ #

def _submenu_mkverything():
    while True:
        console.print()
        console.print(Panel(
            "\n"
            "  [bold cyan][1.1][/bold cyan]  Launcher (todos los modos)\n"
            "  [bold cyan][1.2][/bold cyan]  Setup / Dependencias\n"
            "  [bold cyan][1.3][/bold cyan]  Test rápido de herramientas externas\n"
            "  [bold cyan][b][/bold cyan]    Volver\n",
            title="[bold green]MKVerything[/bold green]",
            border_style="green",
        ))
        sub = Prompt.ask("root@singularity:mkve", choices=["1.1", "1.2", "1.3", "b"], default="1.1")
        log.info(f"MKVerything submenu: {sub}")

        if sub == "1.1":
            _run(["python3", "MKVerything/launcher.py"])
        elif sub == "1.2":
            console.print(Panel(
                "  Dependencias binarias requeridas:\n"
                "  [cyan]ffmpeg[/cyan]  [cyan]ffprobe[/cyan]  [cyan]makemkvcon[/cyan]  "
                "[cyan]mkvmerge[/cyan]  [cyan]mediainfo[/cyan]\n\n"
                "  Colócalos en [bold]MKVerything/bin/linux/[/bold]\n"
                "  Python deps: [bold]pip install -r MKVerything/requirements.txt[/bold]",
                title="[bold yellow]Setup MKVerything[/bold yellow]",
                border_style="yellow",
            ))
            if Prompt.ask("¿Abrir launcher ahora?", choices=["s", "n"], default="s") == "s":
                _run(["python3", "MKVerything/launcher.py"])
        elif sub == "1.3":
            console.print()
            console.print(Rule("[bold]Test de herramientas externas[/bold]"))
            all_ok = True
            for tool in ["ffmpeg", "ffprobe", "mkvmerge", "mediainfo", "makemkvcon"]:
                rc = subprocess.run(["which", tool], capture_output=True).returncode
                status = "[green]✓ OK[/green]" if rc == 0 else "[red]✗ NO ENCONTRADO[/red]"
                if rc != 0:
                    all_ok = False
                console.print(f"  {tool:14s} {status}")
            console.print()
            if all_ok:
                console.print("[green]✓ Todas las herramientas están disponibles.[/green]")
            else:
                console.print("[yellow]⚠ Faltan herramientas. Configura MKVerything/bin/linux/ y el PATH.[/yellow]")
            log.info(f"Tool test completed, all_ok={all_ok}")
            Prompt.ask("\nEnter para volver", default="")
        elif sub == "b":
            break


# ------------------------------------------------------------------ #
#  Sub-menú 4 — Extras                                               #
# ------------------------------------------------------------------ #

def _submenu_extras():
    while True:
        console.print()
        console.print(Panel(
            "\n"
            "  [bold cyan][4.1][/bold cyan]  Tag Ingestor\n"
            "  [bold cyan][4.2][/bold cyan]  Torrents Comparison\n"
            "  [bold cyan][4.3][/bold cyan]  Triage MKV (HEVC vs H264)\n"
            "  [bold cyan][4.4][/bold cyan]  Chaos Maker  [dim red](⚠ CORROMPE MKVs — solo testing)[/dim red]\n"
            "  [bold cyan][b][/bold cyan]    Volver\n",
            title="[bold blue]Extras[/bold blue]",
            border_style="blue",
        ))
        sub = Prompt.ask("root@singularity:extras", choices=["4.1", "4.2", "4.3", "4.4", "b"], default="b")
        log.info(f"Extras submenu: {sub}")

        if sub == "4.1":
            script = BASE_DIR / "core" / "tag_ingestor.py"
            if script.exists():
                _run(["python3", str(script)])
            else:
                console.print("[yellow]⚠ core/tag_ingestor.py no encontrado.[/yellow]")
                Prompt.ask("Enter para continuar", default="")

        elif sub == "4.2":
            script = BASE_DIR / "extras" / "torrents comparison" / "checkit.py"
            if script.exists():
                _run(["python3", str(script)], cwd=script.parent)
            else:
                console.print("[yellow]⚠ extras/torrents comparison/checkit.py no encontrado.[/yellow]")
                Prompt.ask("Enter para continuar", default="")

        elif sub == "4.3":
            while True:
                path_raw = Prompt.ask("[bold]Directorio a analizar[/bold]").strip()
                path = Path(path_raw)
                if path.is_dir():
                    break
                console.print(f"[red]✗ No es un directorio válido: {path_raw}[/red]")
            
            # Correct path for Triage MKV script
            triage_script = "extras/Triaje-mkv/triage_mkv.py"
            _run(["python3", triage_script, str(path)])

        elif sub == "4.4":
            console.print()
            console.print(Panel(
                "[bold red]⚠ ADVERTENCIA CRÍTICA[/bold red]\n\n"
                "Chaos Maker CORROMPE archivos MKV intencionalmente inyectando ruido binario.\n"
                "Úsalo SOLO con archivos de prueba, nunca con tu biblioteca real.",
                border_style="red",
            ))
            if Prompt.ask("¿Confirmar?", choices=["s", "n"], default="n") == "s":
                while True:
                    path_raw = Prompt.ask("[bold]Directorio con MKVs de prueba[/bold]").strip()
                    path = Path(path_raw)
                    if path.is_dir():
                        break
                    console.print(f"[red]✗ No es un directorio válido: {path_raw}[/red]")
                log.warning(f"Chaos Maker launched on: {path}")
                _run(["python3", "extras/Chaos-Maker/chaos-maker.py", str(path)])

        elif sub == "b":
            break


# ------------------------------------------------------------------ #
#  Opción 3 — UNIT3D Orchestrator                                    #
# ------------------------------------------------------------------ #

def unit3d_orchestrator():
    console.print(Panel(
        "[bold green]ORQUESTADOR UNIT3D EDITION[/bold green]\nConfiguración de sesión única",
        border_style="green",
    ))

    banner = Prompt.ask(
        "Texto del banner en BBCode que se añadirá a las descripciones\n"
        "  [dim](pulsa Enter para usar el banner por defecto)[/dim]",
        default=MSG_NUEVO,
    )
    start = IntPrompt.ask(
        "ID del primer torrent a editar\n"
        "  [dim](número visible en la URL: tracker.com/torrents/[bold]14[/bold])[/dim]",
        default=ID_INICIO,
    )
    end = IntPrompt.ask(
        "ID del último torrent a editar\n"
        "  [dim](se procesarán todos los IDs entre el inicial y este)[/dim]",
        default=ID_FIN,
    )

    confirm = Prompt.ask(f"¿Lanzar secuencia 01-04 para IDs {start}-{end}?", choices=["s", "n"], default="s")

    if confirm == "s":
        scripts = [
            "extras/MASS-EDITION-UNIT3D/01_scraper.py",
            "extras/MASS-EDITION-UNIT3D/02_indexer.py",
            "extras/MASS-EDITION-UNIT3D/03_mass_updater.py",
            "extras/MASS-EDITION-UNIT3D/04_image_resurrector.py"
        ]
        os.environ["ID_START"] = str(start)
        os.environ["ID_END"] = str(end)
        log.info(f"UNIT3D Orchestrator: IDs {start}-{end}")
        for script in scripts:
            script_path = BASE_DIR / script
            if not script_path.exists():
                console.print(f"[yellow]⚠ Script no encontrado, saltando: {script}[/yellow]")
                log.warning(f"UNIT3D script not found: {script}")
                continue
            console.print(Panel(f"[bold yellow]EJECUTANDO:[/bold yellow] {script}", style="bold"))
            _run(["python3", str(script_path)])
        console.print("[bold green]✓ Secuencia Masiva Finalizada.[/bold green]")
        time.sleep(2)


# ------------------------------------------------------------------ #
#  Menú principal                                                     #
# ------------------------------------------------------------------ #

def main_menu():
    # Iniciar dashboard en segundo plano
    dash_thread = threading.Thread(target=run_dashboard, daemon=True)
    dash_thread.start()
    
    update_status("CORE", "Menú Principal", "ONLINE", details="Dashboard activo en puerto 8002")
    boot_sequence()
    while True:
        clear_screen()
        menu = Table(
            title="[bold cyan]S I N G U L A R I T Y[/bold cyan]",
            box=None,
            show_header=True,
            header_style="bold magenta",
        )
        menu.add_column("SYS", justify="center")
        menu.add_column("MÓDULO", style="white")
        menu.add_column("ESTADO", justify="right")

        menu.add_row("1", "MKVerything (Auditoría & Spam)", "[green]ONLINE[/green]")
        menu.add_row("2", "RawLoadrr (Auto-Upload)", "[green]ONLINE[/green]")
        menu.add_row("3", "UNIT3D Edition (Orquestador 01-04)", "[yellow]READY[/yellow]")
        menu.add_row("4", "Extras (Ingestor, Triage, Chaos)", "[blue]ACTIVE[/blue]")
        menu.add_row("5", "SINGULARITY MODE (Full AI)", "[red]ONLINE[/red]")
        menu.add_row("0", "Cerrar Conexión", "")

        console.print(Align.center(Panel(menu, border_style="cyan", padding=(1, 5))))

        sel = Prompt.ask("root@singularity", choices=["1", "2", "3", "4", "5", "0"])
        log.info(f"Main menu selection: {sel}")

        if sel == "1":
            _submenu_mkverything()
        elif sel == "2":
            _run(["python3", "RawLoadrr/rawncher.py"])
        elif sel == "3":
            unit3d_orchestrator()
        elif sel == "4":
            _submenu_extras()
        elif sel == "5":
            singularity_mode()
        elif sel == "0":
            log.info("User exited Singularity")
            break


def _singularity_summary(results: dict, elapsed_total: float):
    status_icons = {
        "OK":    "[green]✓ OK[/green]",
        "WARN":  "[yellow]⚠ WARN[/yellow]",
        "ERROR": "[red]✗ ERROR[/red]",
        "SKIP":  "[dim]— SKIP[/dim]",
    }
    labels = {
        "fase1": "Fase 1 · MKVerything God Mode",
        "fase2": "Fase 2 · Triage MKV",
        "fase3": "Fase 3 · Auto-Upload",
        "fase4": "Fase 4 · UNIT3D Orchestrator",
    }
    t = Table(box=None, show_header=True, header_style="bold magenta")
    t.add_column("FASE", style="cyan")
    t.add_column("ESTADO", justify="center")
    t.add_column("DETALLES", style="white")

    for key, label in labels.items():
        r = results.get(key)
        if r is None:
            continue
        icon = status_icons.get(r.get("status", "?"), r.get("status", "?"))
        parts = []
        if "elapsed" in r:
            parts.append(f"{r['elapsed']:.1f}s")
        if "stats" in r:
            s = r["stats"]
            mb = s.get("saved_bytes", 0) // (1024 * 1024)
            parts.append(
                f"isos {s.get('isos_ok', 0)}ok/{s.get('isos_fail', 0)}fail  "
                f"conv={s.get('processed', 0)}  saved={mb}MB"
            )
        if "count" in r:
            parts.append(f"{r['count']} carpetas HEVC")
        if "hevc_list" in r:
            parts.append(Path(r["hevc_list"]).name)
        if r.get("rc") is not None:
            parts.append(f"rc={r['rc']}")
        if "scripts" in r:
            ok_scripts = sum(1 for s in r["scripts"] if s.get("rc") == 0)
            parts.append(f"{ok_scripts}/{len(r['scripts'])} scripts OK")
        if "error" in r:
            parts.append(f"[red]{str(r['error'])[:60]}[/red]")
        if "msg" in r:
            parts.append(r["msg"])
        t.add_row(label, icon, "  ".join(parts))

    total_min = int(elapsed_total // 60)
    total_sec = int(elapsed_total % 60)
    console.print()
    console.print(Rule("[bold cyan]SINGULARITY — RESUMEN FINAL[/bold cyan]"))
    console.print(Panel(
        t,
        title=f"[bold cyan]Pipeline completado en {total_min}m {total_sec}s[/bold cyan]",
        border_style="cyan",
        padding=(1, 2),
    ))


def _ensure_credentials(need_unit3d: bool) -> None:
    """Prompt for any credentials that are missing from the environment."""
    env_path = BASE_DIR / ".env"

    _creds: list[tuple[str, str, str, bool]] = [
        (
            "TRACKER_BASE_URL",
            "URL base de tu tracker (ej: https://mitracker.com)",
            BASE_URL,
            need_unit3d,
        ),
        (
            "TRACKER_COOKIE_VALUE",
            "Cookie de sesión del tracker\n"
            "  → Abre tu tracker en el navegador, F12 → Application → Cookies\n"
            "  → Copia el valor de la cookie de sesión (normalmente *_session)",
            COOKIE_VALUE,
            need_unit3d,
        ),
        (
            "IMGBB_API_KEY",
            "API Key de ImgBB (para subir capturas de portada)\n"
            "  → Regístrate en https://imgbb.com y genera tu clave en 'API'",
            IMGBB_API,
            need_unit3d,
        ),
        (
            "PTSCREENS_API_KEY",
            "API Key de PTScreens (servicio alternativo de imágenes)\n"
            "  → Obtén tu clave en https://ptscreens.com/api",
            PTSCREENS_API,
            need_unit3d,
        ),
        (
            "SONARR_API_KEY",
            "API Key de Sonarr (opcional para indexado)\n"
            "  → Settings -> General -> API Key",
            os.getenv("SONARR_API_KEY", ""),
            False,
        ),
        (
            "SONARR_URL",
            "URL de Sonarr (ej: http://localhost:8989)",
            os.getenv("SONARR_URL", "http://127.0.0.1:8989"),
            False,
        ),
        (
            "RADARR_API_KEY",
            "API Key de Radarr (opcional para indexado)\n"
            "  → Settings -> General -> API Key",
            os.getenv("RADARR_API_KEY", ""),
            False,
        ),
        (
            "RADARR_URL",
            "URL de Radarr (ej: http://localhost:7878)",
            os.getenv("RADARR_URL", "http://127.0.0.1:7878"),
            False,
        ),
        (
            "TMP_ROOT",
            "Carpeta temporal para procesado de datos",
            os.getenv("TMP_ROOT", str(BASE_DIR / "tmp")),
            False,
        ),
    ]

    missing = [(env_key, desc, cur) for env_key, desc, cur, required in _creds if required and not cur]
    if not missing:
        return

    console.print()
    console.print(Panel(
        "[yellow]Faltan credenciales necesarias para ejecutar el pipeline.\n"
        "Se te pedirán a continuación. Puedes guardarlas en el archivo .env\n"
        "para no tener que introducirlas de nuevo la próxima vez.[/yellow]",
        title="[bold yellow]⚠ Configuración de credenciales[/bold yellow]",
        border_style="yellow",
    ))

    new_vals: dict[str, str] = {}
    for env_key, desc, _ in missing:
        console.print(f"\n[bold cyan]{env_key}[/bold cyan]")
        console.print(f"[dim]{desc}[/dim]")
        val = Prompt.ask(f"[bold]Valor[/bold]", password=("COOKIE" in env_key or "KEY" in env_key)).strip()
        os.environ[env_key] = val
        new_vals[env_key] = val

    if new_vals:
        save = Prompt.ask(
            "\n¿Guardar estas credenciales en .env para futuras sesiones?",
            choices=["s", "n"],
            default="s",
        )
        if save == "s":
            existing: dict[str, str] = {}
            if env_path.exists():
                for line in env_path.read_text().splitlines():
                    line = line.strip()
                    if "=" in line and not line.startswith("#"):
                        k, _, v = line.partition("=")
                        existing[k.strip()] = v.strip()
            existing.update(new_vals)
            with open(env_path, "w") as fh:
                for k, v in existing.items():
                    fh.write(f"{k}={v}\n")
            console.print("[green]✓ Credenciales guardadas en .env[/green]")


def singularity_mode():
    clear_screen()
    console.print(Rule("[bold red]⚡ SINGULARITY MODE — PIPELINE AUTOMÁTICO[/bold red]", style="red"))
    console.print(Panel(
        "\n"
        "  Fases que se ejecutarán de forma desatendida:\n\n"
        "  [bold red][1][/bold red]  MKVerything God Mode   — extracción ISO + conversión legacy + rescate MKV\n"
        "  [bold yellow][2][/bold yellow]  Triage MKV             — clasificación HEVC / H264\n"
        "  [bold green][3][/bold green]  RawLoadrr Auto-Upload  — subida masiva de la lista HEVC\n"
        "  [bold blue][4][/bold blue]  UNIT3D Orchestrator    — (opcional) scripts 01-04\n",
        title="[bold white]Descripción[/bold white]",
        border_style="white",
    ))

    while True:
        media_root_str = Prompt.ask(
            "[bold]Carpeta raíz donde están tus vídeos[/bold]\n"
            "  [dim](introduce la ruta completa, ej: /media/peliculas)[/dim]"
        ).strip()
        media_root = Path(media_root_str)
        if media_root.is_dir():
            break
        console.print(f"[red]✗ No es un directorio válido: {media_root_str}[/red]")

    iso_output_str = Prompt.ask(
        "[bold]Carpeta donde se guardarán los archivos extraídos de las ISOs[/bold]\n"
        "  [dim](pulsa Enter para usar la misma carpeta raíz)[/dim]",
        default=str(media_root),
    ).strip()
    iso_output = Path(iso_output_str) if iso_output_str else media_root

    tracker = Prompt.ask(
        "[bold]Abreviatura del tracker al que vas a subir[/bold]\n"
        "  [dim](ej: MILNU, BHD, HDB — debe coincidir con tu config de RawLoadrr)[/dim]",
        default="MILNU",
    )

    console.print()
    console.print(Panel(
        "\n"
        "  [bold cyan][1][/bold cyan]  Lista HEVC         [dim](todo-hevc-*.txt)[/dim]   — carpetas donde todo está en HEVC (listas para subir)\n"
        "  [bold cyan][2][/bold cyan]  Lista H264/Legacy  [dim](sigue-h264-*.txt)[/dim]  — carpetas que aún tienen archivos en H264 sin convertir\n"
        "  [bold cyan][3][/bold cyan]  Lista personalizada                    — tú introduces la ruta a tu propio fichero de lista\n"
        "  [bold cyan][4][/bold cyan]  Todo el contenido del directorio       — combina ambas listas (HEVC + H264/Legacy)\n",
        title="[bold cyan]¿Qué lista de archivos usará el Auto-Upload? (Fase 3)[/bold cyan]",
        border_style="cyan",
    ))
    list_mode = Prompt.ask("[bold]Elige una opción[/bold]", choices=["1", "2", "3", "4"], default="1")
    custom_list_path: "Path | None" = None
    if list_mode == "3":
        while True:
            cl_raw = Prompt.ask(
                "[bold]Ruta completa al fichero con la lista de archivos a subir[/bold]"
            ).strip()
            cl_path = Path(cl_raw)
            if cl_path.is_file():
                custom_list_path = cl_path
                break
            console.print(f"[red]✗ No es un fichero válido: {cl_raw}[/red]")

    run_unit3d = Prompt.ask(
        "¿Incluir [bold]Fase 4 — UNIT3D Orchestrator[/bold]?\n"
        "  [dim](edita en masa los torrents del tracker: scraping, indexado, actualización de descripciones e imágenes)[/dim]",
        choices=["s", "n"],
        default="n",
    )
    unit3d_start = unit3d_end = None
    if run_unit3d == "s":
        unit3d_start = IntPrompt.ask(
            "ID del primer torrent a editar en UNIT3D\n"
            "  [dim](número de ID visible en la URL del torrent, ej: tracker.com/torrents/[bold]14[/bold])[/dim]",
            default=ID_INICIO,
        )
        unit3d_end = IntPrompt.ask(
            "ID del último torrent a editar en UNIT3D\n"
            "  [dim](el script procesará todos los IDs entre el inicial y este)[/dim]",
            default=ID_FIN,
        )

    _ensure_credentials(need_unit3d=(run_unit3d == "s"))

    cfg_table = Table(box=None, show_header=False)
    cfg_table.add_column(style="cyan", no_wrap=True)
    cfg_table.add_column(style="white")
    _list_mode_labels = {
        "1": "HEVC  (todo-hevc-*.txt)",
        "2": "H264/Legacy  (sigue-h264-*.txt)",
        "3": f"Personalizada  → {custom_list_path}",
        "4": "Todo el directorio  (HEVC + H264/Legacy)",
    }
    cfg_table.add_row("Raíz de medios", str(media_root))
    cfg_table.add_row("Salida ISOs", str(iso_output))
    cfg_table.add_row("Tracker", tracker)
    cfg_table.add_row("Lista Fase 3", _list_mode_labels[list_mode])
    cfg_table.add_row("UNIT3D", "Sí" if run_unit3d == "s" else "No")
    if run_unit3d == "s":
        cfg_table.add_row("IDs UNIT3D", f"{unit3d_start} → {unit3d_end}")

    console.print()
    console.print(Panel(cfg_table, title="[bold yellow]Configuración[/bold yellow]", border_style="yellow"))

    if Prompt.ask("¿Lanzar pipeline Singularity?", choices=["s", "n"], default="s") != "s":
        return

    phase_results: dict = {}
    start_time_total = time.time()

    mkve_root = BASE_DIR / "MKVerything"
    bin_dir = mkve_root / "bin" / "linux"
    if bin_dir.exists():
        current_path = os.environ.get("PATH", "")
        if str(bin_dir) not in current_path:
            os.environ["PATH"] = str(bin_dir) + os.pathsep + current_path
            os.environ["LD_LIBRARY_PATH"] = (
                str(bin_dir) + os.pathsep + os.environ.get("LD_LIBRARY_PATH", "")
            )
    if str(mkve_root) not in sys.path:
        sys.path.insert(0, str(mkve_root))

    # ------------------------------------------------------------------ #
    # FASE 1 — MKVerything God Mode                                       #
    # ------------------------------------------------------------------ #
    console.print()
    console.print(Rule("[bold red]FASE 1 — MKVerything God Mode[/bold red]", style="red"))
    update_status("PIPELINE", "FASE 1: MKVerything", "IN_PROGRESS", progress=10, details="Iniciando extracción y rescate")
    log.info("Singularity Phase 1 start (MKVerything God Mode)")
    t1 = time.time()
    try:
        from modules.extract import IsoExtractor
        from modules.universal_rescuer import UniversalRescuer

        god_stats = {
            "isos_ok": 0, "isos_fail": 0,
            "processed": 0, "saved_bytes": 0,
            "failed": 0, "skipped": 0,
        }

        isos = list(media_root.rglob("*.iso"))
        if isos:
            console.print(f"[cyan]💿 {len(isos)} ISOs encontradas — extrayendo...[/cyan]")
            extractor = IsoExtractor()
            for iso in isos:
                console.print(f"  → {iso.name}")
                ok = extractor.extraer_iso(str(iso), str(iso_output))
                if ok:
                    god_stats["isos_ok"] += 1
                else:
                    god_stats["isos_fail"] += 1
        else:
            console.print("[dim]  (Sin ISOs en la ruta indicada)[/dim]")

        video_exts = ('.avi', '.mp4', '.mkv', '.wmv', '.mov', '.divx', '.m4v')
        all_video_files = [
            str(f) for f in media_root.rglob("*")
            if f.suffix.lower() in video_exts
        ]

        if all_video_files:
            console.print(f"[cyan]🎬 {len(all_video_files)} archivos de video — procesando...[/cyan]")
            rescuer = UniversalRescuer()
            for vpath in all_video_files:
                is_mkv = vpath.lower().endswith('.mkv')
                res = rescuer.procesar_lista([vpath], modo_estricto=is_mkv)
                if res:
                    god_stats["processed"] += res.get("processed", 0)
                    god_stats["saved_bytes"] += res.get("saved_bytes", 0)
                    god_stats["failed"] += len(res.get("failed", []))
                    god_stats["skipped"] += len(res.get("skipped", []))
        else:
            console.print("[dim]  (Sin archivos de video encontrados)[/dim]")

        phase_results["fase1"] = {
            "status": "OK",
            "elapsed": time.time() - t1,
            "stats": god_stats,
        }
        console.print("[green]✓ Fase 1 completada.[/green]")
        log.info(f"Singularity Phase 1 OK: {god_stats}")

    except Exception as exc:
        log.error(f"Singularity Phase 1 failed: {exc}")
        phase_results["fase1"] = {
            "status": "ERROR",
            "elapsed": time.time() - t1,
            "error": str(exc),
        }
        console.print(f"[red]✗ Fase 1 falló: {exc}[/red]")

    # ------------------------------------------------------------------ #
    # FASE 2 — Triage MKV                                                 #
    # ------------------------------------------------------------------ #
    console.print()
    console.print(Rule("[bold yellow]FASE 2 — Triage MKV (HEVC vs Legacy)[/bold yellow]", style="yellow"))
    update_status("PIPELINE", "FASE 2: Triage", "IN_PROGRESS", progress=40, details="Analizando codecs")
    log.info("Singularity Phase 2 start (Triage)")
    t2 = time.time()
    upload_list_path: "Path | None" = None
    try:
        # Correct path for Triage MKV script
        triage_script = "extras/Triaje-mkv/triage_mkv.py"
        _run(["python3", triage_script, str(media_root)])
        date_str = datetime.now().strftime("%d-%m-%y")
        if list_mode == "1":
            candidate = BASE_DIR / f"todo-hevc-{date_str}.txt"
            list_label_p2 = "HEVC"
        elif list_mode == "2":
            candidate = BASE_DIR / f"sigue-h264-{date_str}.txt"
            list_label_p2 = "H264/Legacy"
        elif list_mode == "4":
            hevc_candidate = BASE_DIR / f"todo-hevc-{date_str}.txt"
            h264_candidate = BASE_DIR / f"sigue-h264-{date_str}.txt"
            combined_path = BASE_DIR / f"todo-all-{date_str}.txt"
            combined_lines: list[str] = []
            for src in (hevc_candidate, h264_candidate):
                if src.exists() and src.stat().st_size > 0:
                    combined_lines.extend(
                        ln for ln in src.read_text(encoding="utf-8").splitlines() if ln.strip()
                    )
            combined_path.write_text("\n".join(combined_lines) + ("\n" if combined_lines else ""), encoding="utf-8")
            candidate = combined_path
            list_label_p2 = "Todo el directorio (HEVC + H264/Legacy)"
        else:
            candidate = custom_list_path
            list_label_p2 = "personalizada"
        if candidate and candidate.exists() and candidate.stat().st_size > 0:
            upload_list_path = candidate
            count = sum(
                1 for ln in upload_list_path.read_text(encoding="utf-8").splitlines()
                if ln.strip()
            )
            phase_results["fase2"] = {
                "status": "OK",
                "elapsed": time.time() - t2,
                "hevc_list": str(upload_list_path),
                "count": count,
            }
            console.print(
                f"[green]✓ Fase 2 completada — {count} carpetas en lista {list_label_p2} para subir.[/green]"
            )
        else:
            phase_results["fase2"] = {
                "status": "WARN",
                "elapsed": time.time() - t2,
                "msg": f"Lista {list_label_p2} vacía o no encontrada",
            }
            console.print(
                f"[yellow]⚠ Fase 2: lista {list_label_p2} no generada o vacía.[/yellow]"
            )
        log.info(f"Singularity Phase 2 done, upload_list={upload_list_path}, mode={list_mode}")

    except Exception as exc:
        log.error(f"Singularity Phase 2 failed: {exc}")
        phase_results["fase2"] = {
            "status": "ERROR",
            "elapsed": time.time() - t2,
            "error": str(exc),
        }
        console.print(f"[red]✗ Fase 2 falló: {exc}[/red]")

    # ------------------------------------------------------------------ #
    # FASE 3 — RawLoadrr Auto-Upload                                      #
    # ------------------------------------------------------------------ #
    console.print()
    console.print(Rule("[bold green]FASE 3 — RawLoadrr Auto-Upload[/bold green]", style="green"))
    update_status("PIPELINE", "FASE 3: Auto-Upload", "IN_PROGRESS", progress=70, details="Inyectando torrents en tracker")
    log.info("Singularity Phase 3 start (Auto-Upload)")
    t3 = time.time()
    if upload_list_path and upload_list_path.exists():
        try:
            rc = _run(
                ["python3", "auto-upload.py", "--list", str(upload_list_path), "--tracker", tracker],
                cwd=BASE_DIR / "RawLoadrr",
            )
            status = "OK" if rc == 0 else "WARN"
            phase_results["fase3"] = {"status": status, "elapsed": time.time() - t3, "rc": rc}
            color = "green" if rc == 0 else "yellow"
            symbol = "✓" if rc == 0 else "⚠"
            console.print(f"[{color}]{symbol} Fase 3 completada (rc={rc}).[/{color}]")
            log.info(f"Singularity Phase 3: rc={rc}")
        except Exception as exc:
            log.error(f"Singularity Phase 3 failed: {exc}")
            phase_results["fase3"] = {
                "status": "ERROR",
                "elapsed": time.time() - t3,
                "error": str(exc),
            }
            console.print(f"[red]✗ Fase 3 falló: {exc}[/red]")
    else:
        phase_results["fase3"] = {
            "status": "SKIP",
            "elapsed": 0,
            "msg": "Sin lista de upload — fase omitida",
        }
        console.print("[yellow]⚠ Fase 3 omitida: no hay lista disponible para subida.[/yellow]")

    # ------------------------------------------------------------------ #
    # FASE 4 — UNIT3D Orchestrator (opcional)                             #
    # ------------------------------------------------------------------ #
    if run_unit3d == "s":
        console.print()
        console.print(Rule("[bold blue]FASE 4 — UNIT3D Orchestrator[/bold blue]", style="blue"))
        update_status("PIPELINE", "FASE 4: Orchestrator", "IN_PROGRESS", progress=90, details="Mantenimiento masivo del tracker")
        log.info(f"Singularity Phase 4 start (UNIT3D), IDs {unit3d_start}-{unit3d_end}")
        t4 = time.time()
        try:
            os.environ["ID_START"] = str(unit3d_start)
            os.environ["ID_END"] = str(unit3d_end)
            scripts = [
                "extras/MASS-EDITION-UNIT3D/01_scraper.py",
                "extras/MASS-EDITION-UNIT3D/02_indexer.py",
                "extras/MASS-EDITION-UNIT3D/03_mass_updater.py",
                "extras/MASS-EDITION-UNIT3D/04_image_resurrector.py",
            ]
            script_results = []
            for script in scripts:
                sp = BASE_DIR / script
                if sp.exists():
                    console.print(f"[blue]  → {Path(script).name}[/blue]")
                    rc = _run(["python3", str(sp)])
                    script_results.append({"script": Path(script).name, "rc": rc})
                else:
                    console.print(f"[yellow]  ⚠ No encontrado: {script}[/yellow]")
                    script_results.append({"script": Path(script).name, "rc": None, "note": "not found"})
            phase_results["fase4"] = {
                "status": "OK",
                "elapsed": time.time() - t4,
                "scripts": script_results,
            }
            console.print("[green]✓ Fase 4 completada.[/green]")
            log.info("Singularity Phase 4 OK")
        except Exception as exc:
            log.error(f"Singularity Phase 4 failed: {exc}")
            phase_results["fase4"] = {
                "status": "ERROR",
                "elapsed": time.time() - t4,
                "error": str(exc),
            }
            console.print(f"[red]✗ Fase 4 falló: {exc}[/red]")

    _singularity_summary(phase_results, time.time() - start_time_total)
    update_status("PIPELINE", "COMPLETADO", "SUCCESS", progress=100, details="Pipeline finalizado con éxito")
    log.info("Singularity pipeline finished")
    Prompt.ask("\nEnter para volver al menú principal", default="")


if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        log.info("Singularity interrupted by user (KeyboardInterrupt)")
        console.print("\n[yellow]Conexión cerrada.[/yellow]")
        sys.exit(0)
