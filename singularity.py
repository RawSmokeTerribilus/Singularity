#!/usr/bin/env python3
import os
import sys
import time
import random
import logging
import subprocess
import threading
import socket
import shutil
from core.status_manager import update_status, clear_all_statuses
from pathlib import Path
from datetime import datetime
from rich.console import Console

from core.status_manager import update_status
from core.dashboard import run_dashboard

# CSI Integration
sys.path.append(str(Path(__file__).parent / "extras" / "CSI"))
try:
    import csi
except ImportError:
    csi = None

from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, IntPrompt
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
from rich.align import Align
from rich.rule import Rule

from singularity_config import GOD_PHRASES, MSG_NUEVO, ID_INICIO, ID_FIN, LOGS_DIR, BASE_URL, COOKIE_VALUE, IMGBB_API, PTSCREENS_API

console = Console()

# --- TROLLING SUBSYSTEM INJECTION ---
if GOD_PHRASES:
    if not hasattr(console, 'original_print'):
        console.original_print = console.print

    def troll_print(*args, **kwargs):
        if random.random() < 0.01: # 1% de probabilidad
            phrase = random.choice(GOD_PHRASES)
            console.original_print(f"[dim italic magenta]« {phrase} »[/dim italic magenta]")
        console.original_print(*args, **kwargs)

    console.print = troll_print
# ------------------------------------
BASE_DIR = Path(__file__).parent


# --- Path setup for MKVerything ---
# This ensures that linters and IDEs can find the 'modules' package,
# which is located inside the 'MKVerything' directory.
MKVE_ROOT = BASE_DIR / "MKVerything"
if str(MKVE_ROOT) not in sys.path:
    sys.path.insert(0, str(MKVE_ROOT))

bin_dir = MKVE_ROOT / "bin" / "linux"
if bin_dir.exists():
    os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")
    os.environ["LD_LIBRARY_PATH"] = str(bin_dir) + os.pathsep + os.environ.get("LD_LIBRARY_PATH", "")
# ------------------------------------



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
            "  [bold cyan][1.1][/bold cyan]  Lanzador (todos los modos)\n"
            "  [bold cyan][1.2][/bold cyan]  Ajustes / Dependencias\n"
            "  [bold cyan][1.3][/bold cyan]  Testeo rápido de herramientas\n"
            "  [bold cyan][b][/bold cyan]    Atrás\n",
            title="[bold green]MKVerything[/bold green]",
            border_style="green",
        ))
        sub = Prompt.ask("root@singularidad:mkve", choices=["1.1", "1.2", "1.3", "b"], default="1.1")
        log.info(f"MKVerything submenu: {sub}")

        if sub == "1.1":
            _run(["python3", "MKVerything/launcher.py"])
        elif sub == "1.2":
            console.print(Panel(
                "  Necesitas estas dependencias binarias:\n"
                "  [cyan]ffmpeg[/cyan]  [cyan]ffprobe[/cyan]  [cyan]makemkvcon[/cyan]  "
                "[cyan]mkvmerge[/cyan]  [cyan]mediainfo[/cyan]\n\n"
                "  Déjalos en [bold]MKVerything/bin/linux/[/bold]\n"
                "  Python deps: [bold]pip install -r MKVerything/requirements.txt[/bold]",
                title="[bold yellow]Ajustes de MKVerything[/bold yellow]",
                border_style="yellow",
            ))
            if Prompt.ask("¿Abro el lanzador ahora?", choices=["s", "n"], default="s") == "s":
                _run(["python3", "MKVerything/launcher.py"])
        elif sub == "1.3":
            console.print()
            console.print(Rule("[bold]Testeo de herramientas[/bold]"))
            all_ok = True
            for tool in ["ffmpeg", "ffprobe", "mkvmerge", "mediainfo", "makemkvcon"]:
                rc = subprocess.run(["which", tool], capture_output=True).returncode
                status = "[green]✓ Fetén[/green]" if rc == 0 else "[red]✗ Ni rastro[/red]"
                if rc != 0:
                    all_ok = False
                console.print(f"  {tool:14s} {status}")
            console.print()
            if all_ok:
                console.print("[green]✓ Todas las herramientas están a punto.[/green]")
            else:
                console.print("[yellow]⚠ Faltan herramientas. Ajusta la carpeta MKVerything/bin/linux/ y el PATH.[/yellow]")
            log.info(f"Tool test completed, all_ok={all_ok}")
            Prompt.ask("\nPulsa Enter para volver", default="")
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
            "  [bold cyan][4.1][/bold cyan]  Ingestor de Tags\n"
            "  [bold cyan][4.2][/bold cyan]  Comparador de Torrents\n"
            "  [bold cyan][4.3][/bold cyan]  Triaje MKV (HEVC vs H264)\n"
            "  [bold cyan][4.4][/bold cyan]  Chaos Maker  [dim red](⚠ JODE MKVs — solo para pruebas)[/dim red]\n"
            "  [bold cyan][4.5][/bold cyan]  CSI: Check, Search, Identify\n"
            "  [bold cyan][b][/bold cyan]    Atrás\n",
            title="[bold blue]Extras[/bold blue]",
            border_style="blue",
        ))
        sub = Prompt.ask("root@singularidad:extras", choices=["4.1", "4.2", "4.3", "4.4", "4.5", "b"], default="b")
        log.info(f"Extras submenu: {sub}")

        if sub == "4.1":
            script = BASE_DIR / "core" / "tag_ingestor.py"
            if script.exists():
                _run(["python3", str(script)])
            else:
                console.print("[yellow]⚠ No encuentro el script core/tag_ingestor.py.[/yellow]")
                Prompt.ask("Pulsa Enter para seguir", default="")

        elif sub == "4.2":
            script = BASE_DIR / "extras" / "torrents comparison" / "checkit.py"
            if script.exists():
                _run(["python3", str(script)], cwd=script.parent)
            else:
                console.print("[yellow]⚠ No encuentro el script extras/torrents comparison/checkit.py.[/yellow]")
                Prompt.ask("Pulsa Enter para seguir", default="")

        elif sub == "4.3":
            while True:
                path_raw = Prompt.ask("[bold]Dime qué directorio analizar[/bold]").strip()
                path = Path(path_raw)
                if path.is_dir():
                    break
                console.print(f"[red]✗ Esto no es un directorio válido: {path_raw}[/red]")
            
            # Correct path for Triage MKV script
            triage_script = "extras/Triaje-mkv/triage_mkv.py"
            _run(["python3", triage_script, str(path)])

        elif sub == "4.4":
            console.print()
            console.print(Panel(
                "[bold red]⚠ AVISO IMPORTANTE[/bold red]\n\n"
                "El Chaos Maker JODE los MKVs a propósito metiéndoles ruido.\n"
                "Úsalo SOLO con archivos de prueba, NUNCA con tus cosas de verdad.",
                border_style="red",
            ))
            if Prompt.ask("¿Estás seguro de la que vas a liar?", choices=["s", "n"], default="n") == "s":
                while True:
                    path_raw = Prompt.ask("[bold]Dime el directorio con los MKVs de prueba[/bold]").strip()
                    path = Path(path_raw)
                    if path.is_dir():
                        break
                    console.print(f"[red]✗ Esto no es un directorio válido: {path_raw}[/red]")
                log.warning(f"Chaos Maker launched on: {path}")
                _run(["python3", "extras/Chaos-Maker/chaos-maker.py", str(path)])

        elif sub == "4.5":
            _run(["python3", "extras/CSI/csi.py"])

        elif sub == "b":
            break


# ------------------------------------------------------------------ #
#  Opción 3 — UNIT3D Orchestrator                                    #
# ------------------------------------------------------------------ #

def unit3d_orchestrator():
    console.print(Panel(
        "[bold green]ORQUESTADOR UNIT3D EDITION[/bold green]\nConfiguración para esta sesión",
        border_style="green",
    ))

    banner = Prompt.ask(
        "El texto del banner en BBCode para añadir a las descripciones\n"
        "  [dim](pulsa Enter para usar el que está por defecto)[/dim]",
        default=MSG_NUEVO,
    )
    start = IntPrompt.ask(
        "ID del primer torrent que quieres editar\n"
        "  [dim](el número que se ve en la URL: tracker.com/torrents/[bold]14[/bold])[/dim]",
        default=ID_INICIO,
    )
    end = IntPrompt.ask(
        "ID del último torrent que quieres editar\n"
        "  [dim](se tocarán todos los IDs entre el primero y este)[/dim]",
        default=ID_FIN,
    )

    confirm = Prompt.ask(f"¿Lanzo la secuencia 01-04 para los IDs del {start} al {end}?", choices=["s", "n"], default="s")

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
                console.print(f"[yellow]⚠ Script no encontrado, se salta: {script}[/yellow]")
                log.warning(f"UNIT3D script not found: {script}")
                continue
            console.print(Panel(f"[bold yellow]DÁNDOLE CAÑA A:[/bold yellow] {script}", style="bold"))
            _run(["python3", str(script_path)])
        console.print("[bold green]✓ Secuencia masiva finiquitada.[/bold green]")
        time.sleep(2)


# ------------------------------------------------------------------ #
#  Menú principal                                                     #
# ------------------------------------------------------------------ #

# ------------------------------------------------------------------ #

def _submenu_mantenimiento():
    base_data = Path("work_data")
    
    while True:
        console.print()
        console.print(Panel(
            "[1] Purgar Temporales (work_data/tmp/*)\n"
            "[2] Purgar Logs (*.log y vestigios)\n"
            "[3] Purgar Reportes (*.txt)\n"
            "[4] Resetear Dashboard (Estado Neutro)\n"
            "[5] DEFCON 1 (Fuego purificador total)\n"
            "[0] Volver al Menú Principal",
            title="[bold red]MANTENIMIENTO & PULICIÓN[/bold red]",
            border_style="red",
            padding=(1, 2)
        ))
        
        sel = Prompt.ask("root@mantenimiento", choices=["1", "2", "3", "4", "5", "0"])
        
        if sel == "0":
            break
            
        if sel in ["1", "5"]:
            tmp_dir = base_data / "tmp"
            count = 0
            if tmp_dir.exists():
                for item in tmp_dir.iterdir():
                    if item.is_file() or item.is_symlink():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
                    count += 1
            console.print(f"[green]✓ TMP pulicionado. {count} focos de basura eliminados.[/green]")

        if sel in ["2", "5"]:
            count = 0
            for log_file in base_data.rglob("*.log"):
                log_file.unlink()
                count += 1
            # Destruir la fosa común fósil de CSI si existe
            csi_fosa = base_data / "logs" / "csi_log"
            if csi_fosa.exists() and csi_fosa.is_dir():
                shutil.rmtree(csi_fosa)
                count += 1
            console.print(f"[green]✓ Logs fulminados. {count} archivos al pozo.[/green]")

        if sel in ["3", "5"]:
            count = 0
            for txt_file in base_data.rglob("*.txt"):
                txt_file.unlink()
                count += 1
            console.print(f"[green]✓ Reportes aniquilados. {count} .txt destruidos.[/green]")

        if sel in ["4", "5"]:
            clear_all_statuses()
            console.print("[green]✓ Dashboard reseteado. Tabula rasa en la FastAPI.[/green]")

        if sel == "5":
            console.print(Rule("[bold red]DEFCON 1 COMPLETO — EL ENTORNO ESTÁ ESTÉRIL[/bold red]", style="red"))

def main_menu():
    # Iniciar dashboard en segundo plano si no está corriendo
    def is_dashboard_running(port=8002):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0

    if not is_dashboard_running():
        dash_thread = threading.Thread(target=run_dashboard, daemon=True)
        dash_thread.start()
        details_msg = "Radar operativo en el puerto 8002"
    else:
        details_msg = "Radar persistente detectado (Puerto 8002)"
    
    update_status("CORE", "Menú Principal", "EN LÍNEA", details=details_msg)
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

        menu.add_row("1", "MKVerything (Auditoría y Spam)", "[green]EN LÍNEA[/green]")
        menu.add_row("2", "RawLoadrr (Subidas automáticas)", "[green]EN LÍNEA[/green]")
        menu.add_row("3", "UNIT3D Ed. (Edita en el Tracker)", "[yellow]LISTO[/yellow]")
        menu.add_row("4", "Extras (Ingestor, Triaje, Chaos)", "[blue]ACTIVO[/blue]")
        menu.add_row("5", "SINGULARIDAD (God Mode - Full Check)", "[red]LENTO[/red]")
        menu.add_row("6", "SINGULARIDAD (Goddess Mode - Fast Check)", "[magenta]VUELO[/magenta]")
        menu.add_row("7", "Mantenimiento & Limpieza", "[red]PELIGRO[/red]")
        menu.add_row("8", "Download more RAM", "[magenta]GRATIS[/magenta]") # <--- Desplazada al 8
        menu.add_row("0", "Cerrar Conexión", "")

        console.print(Align.center(Panel(menu, border_style="cyan", padding=(1, 5))))

        sel = Prompt.ask("root@singularidad", choices=["1", "2", "3", "4", "5", "6", "7", "8", "0"])
        log.info(f"Main menu selection: {sel}")

        if sel == "1":
            _submenu_mkverything()
        elif sel == "2":
            _run(["python3", "RawLoadrr/rawncher.py"])
        elif sel == "3":
            unit3d_orchestrator()
        elif sel == "4":
            _submenu_extras()
        elif sel in ["5", "6"]:
            fast_scan_flag = (sel == "6")
            singularity_mode(fast_scan=fast_scan_flag)  
        elif sel == "7":
            _submenu_mantenimiento()
        elif sel == "8":
            _run(["python3", "RawLoadrr/data/reconfig.py"])
        elif sel == "0":
            log.info("User exited Singularity")
            break


def _singularity_summary(results: dict, elapsed_total: float):
    status_icons = {
        "OK":    "[green]✓ OK[/green]",
        "WARN":  "[yellow]⚠ OJO[/yellow]",
        "ERROR": "[red]✗ ERROR[/red]",
        "SKIP":  "[dim]— SALTADO[/dim]",
    }
    labels = {
        "fase1": "Fase 1 · MKVerything Modo Dios",
        "fase2": "Fase 2 · Triaje MKV",
        "fase3": "Fase 3 · Auto-Upload",
        "fase4": "Fase 4 · Orquestador UNIT3D",
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
                f"ISOs {s.get('isos_ok', 0)}ok/{s.get('isos_fail', 0)}fallos  "
                f"conv={s.get('processed', 0)}  ahorro={mb}MB"
            )
        if "count" in r:
            parts.append(f"{r['count']} carpetas con HEVC")
        if "hevc_list" in r:
            parts.append(Path(r["hevc_list"]).name)
        if r.get("rc") is not None:
            parts.append(f"salida={r['rc']}")
        if "scripts" in r:
            ok_scripts = sum(1 for s in r["scripts"] if s.get("rc") == 0)
            parts.append(f"{ok_scripts}/{len(r['scripts'])} scripts correctos")
        if "error" in r:
            parts.append(f"[red]{str(r['error'])[:60]}[/red]")
        if "msg" in r:
            parts.append(r["msg"])
        t.add_row(label, icon, "  ".join(parts))

    total_min = int(elapsed_total // 60)
    total_sec = int(elapsed_total % 60)
    console.print()
    console.print(Rule("[bold cyan]SINGULARIDAD — REPORTE DE DAÑOS[/bold cyan]"))
    console.print(Panel(
        t,
        title=f"[bold cyan]Pipeline finiquitado en {total_min}m {total_sec}s[/bold cyan]",
        border_style="cyan",
        padding=(1, 2),
    ))


def _ensure_credentials(need_unit3d: bool) -> None:
    """Prompt for any credentials that are missing from the environment."""
    env_path = BASE_DIR / ".env"

    _creds: list[tuple[str, str, str, bool]] = [
        (
            "TRACKER_BASE_URL",
            "La URL base de tu tracker (ej: https://mitracker.com)",
            BASE_URL,
            need_unit3d,
        ),
        (
            "TRACKER_COOKIE_VALUE",
            "La cookie de sesión del tracker\n"
            "  → Abre tu tracker en el navegador, F12 → Application → Cookies\n"
            "  → Copia el valor de la cookie de sesión (normalmente *_session)",
            COOKIE_VALUE,
            need_unit3d,
        ),
        (
            "IMGBB_API_KEY",
            "La API Key de ImgBB (para las capturas de portada)\n"
            "  → Regístrate en https://imgbb.com y genera tu clave en 'API'",
            IMGBB_API,
            need_unit3d,
        ),
        (
            "PTSCREENS_API_KEY",
            "La API Key de PTScreens (otro servicio para imágenes)\n"
            "  → Obtén tu clave en https://ptscreens.com/api",
            PTSCREENS_API,
            need_unit3d,
        ),
        (
            "SONARR_API_KEY",
            "La API Key de Sonarr (opcional, para indexar)\n"
            "  → Settings -> General -> API Key",
            os.getenv("SONARR_API_KEY", ""),
            False,
        ),
        (
            "SONARR_URL",
            "La URL de Sonarr (ej: http://localhost:8989)",
            os.getenv("SONARR_URL", "http://127.0.0.1:8989"),
            False,
        ),
        (
            "RADARR_API_KEY",
            "La API Key de Radarr (opcional, para indexar)\n"
            "  → Settings -> General -> API Key",
            os.getenv("RADARR_API_KEY", ""),
            False,
        ),
        (
            "RADARR_URL",
            "La URL de Radarr (ej: http://localhost:7878)",
            os.getenv("RADARR_URL", "http://127.0.0.1:7878"),
            False,
        ),
        (
            "TMP_ROOT",
            "Carpeta temporal para el curro",
            os.getenv("TMP_ROOT", str(BASE_DIR / "tmp")),
            False,
        ),
    ]

    missing = [(env_key, desc, cur) for env_key, desc, cur, required in _creds if required and not cur]
    if not missing:
        return

    console.print()
    console.print(Panel(
        "[yellow]Ojo, que faltan credenciales para poder arrancar el pipeline.\n"
        "Te las pediré ahora. Puedes guardarlas en el archivo .env\n"
        "para no dar la brasa otra vez.[/yellow]",
        title="[bold yellow]⚠ A rellenar credenciales[/bold yellow]",
        border_style="yellow",
    ))

    new_vals: dict[str, str] = {}
    for env_key, desc, _ in missing:
        console.print(f"\n[bold cyan]{env_key}[/bold cyan]")
        console.print(f"[dim]{desc}[/dim]")
        val = Prompt.ask(f"[bold]Mete el valor[/bold]", password=("COOKIE" in env_key or "KEY" in env_key)).strip()
        os.environ[env_key] = val
        new_vals[env_key] = val

    if new_vals:
        save = Prompt.ask(
            "\n¿Te guardo estas credenciales en el .env para no dar la brasa otra vez?",
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
            console.print("[green]✓ ¡Ale! Credenciales guardadas en el .env[/green]")


def singularity_mode(fast_scan=False):
    clear_screen()
    
    # --- Lógica de Identidad Visual ---
    if fast_scan:
        mode_label = "GODDESS MODE — PIPELINE LUDICROUS"
        mode_style = "magenta"
    else:
        mode_label = "MODO SINGULARIDAD — PIPELINE AUTOMÁTICO"
        mode_style = "red"

    # --- Aplicamos el estilo al Banner ---
    console.print(Rule(f"[bold {mode_style}]⚡ {mode_label}[/bold {mode_style}]", style=mode_style))
    
    # --- Panel con las fases ---
    console.print(Panel(
        "\n"
        "  Estas son las fases que se van a ejecutar solitas:\n\n"
        "  [bold red][1][/bold red]  MKVerything God Mode   — Saca de ISOs + convierte viejales + rescata MKVs\n"
        "  [bold yellow][2][/bold yellow]  Triaje MKV             — Separa HEVC de H264\n"
        "  [bold green][3][/bold green]  RawLoadrr Auto-Upload  — Sube a cholón la lista de HEVC\n"
        "  [bold blue][4][/bold blue]  Orquestador UNIT3D     — (Opcional) Lanza los scripts 01-04\n",
        title="[bold white]Qué se va a liar[/bold white]",
        border_style="white",
    ))

    while True:
        media_root_str = Prompt.ask(
            "[bold]Dime la carpeta raíz donde guardas los vídeos[/bold]\n"
            "  [dim](mete la ruta completa, ej: /media/peliculas)[/dim]"
        ).strip()
        media_root = Path(media_root_str)
        if media_root.is_dir():
            break
        console.print(f"[red]✗ No es un directorio válido: {media_root_str}[/red]")

    iso_output_str = Prompt.ask(
        "[bold]¿Dónde escupo los archivos que saque de las ISOs?[/bold]\n"
        "  [dim](pulsa Enter para usar la misma carpeta raíz)[/dim]",
        default=str(media_root),
    ).strip()
    iso_output = Path(iso_output_str) if iso_output_str else media_root

    tracker = Prompt.ask(
        "[bold]Dime la abreviatura del tracker para subir[/bold]\n"
        "  [dim](ej: MILNU, BHD, HDB — tiene que coincidir con tu config de RawLoadrr)[/dim]",
        default="MILNU",
    )

    console.print()
    console.print(Panel(
        "\n"
        "  [bold cyan][1][/bold cyan]  Solo lo bueno (HEVC)         [dim](todo-hevc-*.txt)[/dim]   — carpetas listas para subir\n"
        "  [bold cyan][2][/bold cyan]  Lo de antes (H264/Legacy)  [dim](sigue-h264-*.txt)[/dim]  — carpetas con cosas aún por convertir\n"
        "  [bold cyan][3][/bold cyan]  Una lista tuya, a medida                    — tú metes la ruta a tu propio fichero\n"
        "  [bold cyan][4][/bold cyan]  Todo lo que pille en el directorio       — mezcla de las dos listas anteriores\n",
        title="[bold cyan]¿Qué le metemos al Auto-Upload en la Fase 3?[/bold cyan]",
        border_style="cyan",
    ))
    list_mode = Prompt.ask("[bold]Venga, elige[/bold]", choices=["1", "2", "3", "4"], default="1")
    custom_list_path: "Path | None" = None
    if list_mode == "3":
        while True:
            cl_raw = Prompt.ask(
                "[bold]Pásame la ruta completa del fichero con tu lista[/bold]"
            ).strip()
            cl_path = Path(cl_raw)
            if cl_path.is_file():
                custom_list_path = cl_path
                break
            console.print(f"[red]✗ Esto no es un fichero válido: {cl_raw}[/red]")

    run_unit3d = Prompt.ask(
        "¿Le damos caña a la [bold]Fase 4 - Orquestador UNIT3D[/bold]?\n"
        "  [dim](edita en masa los torrents del tracker: scraping, indexado, descripciones e imágenes)[/dim]",
        choices=["s", "n"],
        default="n",
    )
    unit3d_start = unit3d_end = None
    if run_unit3d == "s":
        unit3d_start = IntPrompt.ask(
            "Dime el ID del primer torrent a editar en UNIT3D\n"
            "  [dim](el número de ID que se ve en la URL, ej: tracker.com/torrents/[bold]14[/bold])[/dim]",
            default=ID_INICIO,
        )
        unit3d_end = IntPrompt.ask(
            "Y ahora el ID del último torrent a tocar\n"
            "  [dim](se procesarán todos los IDs entre el primero y este)[/dim]",
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

    if Prompt.ask("¿Arrancamos el pipeline de Singularidad?", choices=["s", "n"], default="s") != "s":
        return

    phase_results: dict = {}
    start_time_total = time.time()

    # ------------------------------------------------------------------ #
    # FASE 1 — MKVerything God Mode                                       #
    # ------------------------------------------------------------------ #
    console.print()
    console.print(Rule("[bold red]FASE 1 — MKVerything: MODO DIOS[/bold red]", style="red"))
    update_status("PIPELINE", "FASE 1: MKVerything", "CURRANDO", progress=10, details="Empezando extracción y rescate")
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
            console.print(f"[cyan]💿 {len(isos)} ISOs localizadas — a destriparlas...[/cyan]")
            extractor = IsoExtractor()
            for iso in isos:
                console.print(f"  → {iso.name}")
                ok = extractor.extraer_iso(str(iso), str(iso_output))
                if ok:
                    god_stats["isos_ok"] += 1
                else:
                    god_stats["isos_fail"] += 1
        else:
            console.print("[dim]  (No he visto ISOs por aquí)[/dim]")

        video_exts = ('.avi', '.mp4', '.mkv', '.wmv', '.mov', '.divx', '.m4v')
        all_video_files = [
            str(f) for f in media_root.rglob("*")
            if f.suffix.lower() in video_exts
        ]

        if all_video_files:
            console.print(f"[cyan]🎬 {len(all_video_files)} vídeos en el punto de mira — a procesar...[/cyan]")
            rescuer = UniversalRescuer()
            for vpath in all_video_files:
                is_mkv = vpath.lower().endswith('.mkv')
                res = rescuer.procesar_lista([vpath], modo_estricto=is_mkv, fast_scan=fast_scan)
                if res:
                    god_stats["processed"] += res.get("processed", 0)
                    god_stats["saved_bytes"] += res.get("saved_bytes", 0)
                    god_stats["failed"] += len(res.get("failed", []))
                    god_stats["skipped"] += len(res.get("skipped", []))
        else:
            console.print("[dim]  (No he encontrado vídeos para toquetear)[/dim]")

        phase_results["fase1"] = {
            "status": "OK",
            "elapsed": time.time() - t1,
            "stats": god_stats,
        }
        console.print("[green]✓ Fase 1 finiquitada.[/green]")
        log.info(f"Singularity Phase 1 OK: {god_stats}")

    except Exception as exc:
        log.error(f"Singularity Phase 1 failed: {exc}")
        phase_results["fase1"] = {
            "status": "ERROR",
            "elapsed": time.time() - t1,
            "error": str(exc),
        }
        console.print(f"[red]✗ La Fase 1 ha petado: {exc}[/red]")

    # ------------------------------------------------------------------ #
    # FASE 2 — Triage MKV                                                 #
    # ------------------------------------------------------------------ #
    console.print()
    console.print(Rule("[bold yellow]FASE 2 — Triaje MKV (HEVC vs Jurásico)[/bold yellow]", style="yellow"))
    update_status("PIPELINE", "FASE 2: Triaje", "CURRANDO", progress=40, details="Analizando codecs")
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
                f"[green]✓ Fase 2 finiquitada — {count} carpetas en la lista '{list_label_p2}' listas para el despegue.[/green]"
            )
        else:
            phase_results["fase2"] = {
                "status": "WARN",
                "elapsed": time.time() - t2,
                "msg": f"Lista {list_label_p2} vacía o no encontrada",
            }
            console.print(
                f"[yellow]⚠ Fase 2: La lista '{list_label_p2}' no se ha generado o está a cero.[/yellow]"
            )
        log.info(f"Singularity Phase 2 done, upload_list={upload_list_path}, mode={list_mode}")

    except Exception as exc:
        log.error(f"Singularity Phase 2 failed: {exc}")
        phase_results["fase2"] = {
            "status": "ERROR",
            "elapsed": time.time() - t2,
            "error": str(exc),
        }
        console.print(f"[red]✗ La Fase 2 ha petado: {exc}[/red]")

    # ------------------------------------------------------------------ #
    # FASE 3 — RawLoadrr Auto-Upload                                      #
    # ------------------------------------------------------------------ #
    console.print()
    console.print(Rule("[bold green]FASE 3 — RawLoadrr: Fuego a Discreción[/bold green]", style="green"))
    update_status("PIPELINE", "FASE 3: Auto-Upload", "CURRANDO", progress=70, details="Inyectando torrents al tracker")
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
            console.print(f"[{color}]{symbol} Fase 3 finiquitada (código de salida: {rc}).[/{color}]")
            log.info(f"Singularity Phase 3: rc={rc}")
        except Exception as exc:
            log.error(f"Singularity Phase 3 failed: {exc}")
            phase_results["fase3"] = {
                "status": "ERROR",
                "elapsed": time.time() - t3,
                "error": str(exc),
            }
            console.print(f"[red]✗ La Fase 3 ha petado: {exc}[/red]")
    else:
        phase_results["fase3"] = {
            "status": "SKIP",
            "elapsed": 0,
            "msg": "Sin lista de upload — fase omitida",
        }
        console.print("[yellow]⚠ Fase 3 omitida: no tengo lista para subir nada.[/yellow]")

    # ------------------------------------------------------------------ #
    # FASE 4 — UNIT3D Orchestrator (opcional)                             #
    # ------------------------------------------------------------------ #
    if run_unit3d == "s":
        console.print()
        console.print(Rule("[bold blue]FASE 4 — Orquestador UNIT3D[/bold blue]", style="blue"))
        update_status("PIPELINE", "FASE 4: Orquestador", "CURRANDO", progress=90, details="Haciendo mantenimiento masivo en el tracker")
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
                    console.print(f"[yellow]  ⚠ No lo encuentro: {script}[/yellow]")
                    script_results.append({"script": Path(script).name, "rc": None, "note": "not found"})
            phase_results["fase4"] = {
                "status": "OK",
                "elapsed": time.time() - t4,
                "scripts": script_results,
            }
            console.print("[green]✓ Fase 4 finiquitada.[/green]")
            log.info("Singularity Phase 4 OK")
        except Exception as exc:
            log.error(f"Singularity Phase 4 failed: {exc}")
            phase_results["fase4"] = {
                "status": "ERROR",
                "elapsed": time.time() - t4,
                "error": str(exc),
            }
            console.print(f"[red]✗ La Fase 4 ha petado: {exc}[/red]")

    _singularity_summary(phase_results, time.time() - start_time_total)
    update_status("PIPELINE", "COMPLETADO", "FINIQUITADO", progress=100, details="Pipeline completado con éxito")
    log.info("Singularity pipeline finished")
    Prompt.ask("\nPulsa Enter para volver al menú principal", default="")


if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        log.info("Singularity interrupted by user (KeyboardInterrupt)")
        console.print("\n[yellow]Conexión cerrada a las bravas.[/yellow]")
        sys.exit(0)
