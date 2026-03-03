#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rawncher — Lanzador interactivo para RawLoadrr (en español)
"""

import sys
import os
import json
import re
import logging
import importlib
import subprocess
from pathlib import Path
from typing import Optional
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from src.console import console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.table import Table
from rich.rule import Rule


class Rawncher:
    """Lanzador principal de RawLoadrr"""

    def __init__(self):
        self.base_dir = Path(__file__).parent
        self._logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        logs_dir = self.base_dir / "logs"
        logs_dir.mkdir(exist_ok=True)
        log_path = logs_dir / f"rawncher_{datetime.now().strftime('%Y-%m-%d')}.log"
        logger = logging.getLogger("rawncher")
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

    # ------------------------------------------------------------------ #
    #  Bucle principal                                                     #
    # ------------------------------------------------------------------ #

    def run(self) -> None:
        """Bucle principal del lanzador"""
        self._logger.info("Rawncher session started")
        console.print(Rule("[bold magenta]RAWNCHER — RawLoadrr Launcher[/bold magenta]"))
        while True:
            try:
                choice = self._menu_principal()
                self._logger.info(f"Menu selection: {choice}")
                if choice == "0":
                    console.print("\n[yellow]¡Hasta luego![/yellow]")
                    self._logger.info("Rawncher session ended by user")
                    break
                elif choice == "1":
                    self.opcion_1_usar_tracker()
                elif choice == "2":
                    self.opcion_2_configurar()
                elif choice == "3":
                    self.opcion_3_crear_tracker()
                elif choice == "4":
                    self.opcion_4_debug()
                elif choice == "5":
                    self.opcion_5_listar_sesiones()
                elif choice == "6":
                    self.opcion_6_cargar_sesion()
            except KeyboardInterrupt:
                console.print("\n[yellow]Operación cancelada.[/yellow]")
                self._logger.info("Operation cancelled by user (KeyboardInterrupt)")

    def _menu_principal(self) -> str:
        """Muestra el menú principal y devuelve la elección del usuario"""
        console.print()
        menu_text = (
            "\n"
            "  [bold cyan][1][/bold cyan]  Usar tracker existente\n"
            "  [bold cyan][2][/bold cyan]  Configurar tracker existente\n"
            "  [bold cyan][3][/bold cyan]  Crear nuevo tracker\n"
            "  [bold cyan][4][/bold cyan]  Modo debug [dim](sin subida real)[/dim]\n"
            "  [bold cyan][5][/bold cyan]  Listar sesiones guardadas\n"
            "  [bold cyan][6][/bold cyan]  Cargar sesión guardada\n"
            "  [bold cyan][0][/bold cyan]  Salir\n"
        )
        console.print(
            Panel(
                menu_text,
                title="[bold magenta]RAWNCHER[/bold magenta]",
                border_style="magenta",
            )
        )
        choice = Prompt.ask(
            "[bold]Elige una opción[/bold]",
            choices=["0", "1", "2", "3", "4", "5", "6"],
            default="1",
        )
        return choice

    # ------------------------------------------------------------------ #
    #  Helpers compartidos                                                 #
    # ------------------------------------------------------------------ #

    def _get_tracker_names_from_upload(self) -> list:
        """Lee upload.py como texto y extrae las abreviaciones de tracker_data['api']"""
        upload_path = self.base_dir / "upload.py"
        try:
            text = upload_path.read_text(encoding="utf-8")
            match = re.search(r"'api'\s*:\s*\[([^\]]+)\]", text)
            if not match:
                return []
            raw = match.group(1)
            return re.findall(r"'([A-Z0-9]+)'", raw)
        except Exception:
            return []

    def _build_tracker_table(self) -> tuple:
        """Construye tabla Rich con los trackers disponibles.

        Devuelve: (table, trackers_list)
        """
        table = Table(
            show_header=True,
            header_style="bold cyan",
            border_style="dim",
        )
        table.add_column("#", style="dim", justify="right")
        table.add_column("Tracker", style="bold")
        table.add_column("API ✓/✗", justify="center")

        trackers = []
        try:
            from data.config import config

            trackers_dict = config.get("TRACKERS", {})
            trackers = sorted(
                [t for t in trackers_dict if isinstance(trackers_dict[t], dict)]
            )
            for i, name in enumerate(trackers, 1):
                api_key = trackers_dict[name].get("api_key", "")
                configured = (
                    bool(api_key)
                    and "API_KEY" not in api_key
                    and len(api_key) >= 32
                )
                icon = "[green]✓[/green]" if configured else "[red]✗[/red]"
                table.add_row(str(i), name, icon)
        except ImportError:
            console.print("[red]✗ No se encontró data/config.py[/red]")

        return table, trackers

    def _seleccionar_tracker(self, preselected: Optional[str] = None) -> Optional[str]:
        """Muestra tabla de trackers y devuelve la abreviación elegida"""
        if preselected:
            return preselected

        table, trackers = self._build_tracker_table()
        if not trackers:
            console.print("[red]No hay trackers disponibles en la configuración.[/red]")
            return None

        console.print(table)
        raw = Prompt.ask("[bold]Número del tracker[/bold]", default="1")
        try:
            idx = int(raw)
        except ValueError:
            idx = 0

        if 1 <= idx <= len(trackers):
            return trackers[idx - 1]

        console.print("[red]Número no válido.[/red]")
        return None

    def _ejecutar_comando(self, cmd: list, cwd: Path = None) -> int:
        """Ejecuta un comando con salida en vivo desde base_dir por defecto"""
        cwd_path = str(cwd or self.base_dir)
        self._logger.info(f"CMD: {' '.join(str(c) for c in cmd)} (cwd={cwd_path})")
        result = subprocess.run(cmd, cwd=cwd_path)
        self._logger.info(f"EXIT: {result.returncode}")
        return result.returncode

    def _get_sessions(self) -> list:
        """Devuelve lista de rutas Path de sesiones guardadas (más recientes primero)"""
        sessions_dir = self.base_dir / "tmp" / "tracker_sessions"
        if not sessions_dir.exists():
            return []
        return sorted(sessions_dir.glob("session_*.json"), reverse=True)

    # ------------------------------------------------------------------ #
    #  Opción 1 — Usar tracker existente                                  #
    # ------------------------------------------------------------------ #

    def opcion_1_usar_tracker(self, preselected_tracker: Optional[str] = None) -> None:
        """Menú principal de la opción 1"""
        tracker = self._seleccionar_tracker(preselected=preselected_tracker)
        if tracker is None:
            return

        console.print()
        console.print(
            Panel(
                "\n"
                "  [bold cyan][1][/bold cyan]  Subir desde una ruta (archivo o carpeta)\n"
                "  [bold cyan][2][/bold cyan]  Usar lista existente (.txt con rutas)\n"
                "  [bold cyan][3][/bold cyan]  Triage primero (escanear directorio y elegir listas)\n",
                title=f"[bold green]Tracker: {tracker}[/bold green]",
                border_style="green",
            )
        )
        sub = Prompt.ask(
            "[bold]Elige sub-opción[/bold]",
            choices=["1", "2", "3"],
            default="1",
        )
        if sub == "1":
            self._flujo_ruta(tracker)
        elif sub == "2":
            self._flujo_lista_existente(tracker)
        elif sub == "3":
            self._flujo_triage(tracker)

    def _args_opcionales(self, debug: bool = False) -> list:
        """Muestra lista de flags opcionales para upload.py y devuelve los seleccionados"""
        flags = [
            ("--anon",            "Subida anónima"),
            ("--skip-dupe-check", "Saltar comprobación de duplicados"),
            ("--stream",          "Stream Optimized Upload"),
            ("--personalrelease", "Personal Release"),
            ("--no-seed",         "No añadir torrent al cliente"),
            ("--debug",           "Modo debug (sin subida real)"),
        ]

        selected = set()
        if debug:
            selected.add("--debug")

        while True:
            console.print()
            table = Table(
                show_header=True,
                header_style="bold cyan",
                border_style="dim",
                title="[bold]Opciones adicionales[/bold]",
            )
            table.add_column("#", style="dim", justify="right")
            table.add_column("Flag")
            table.add_column("Descripción")
            table.add_column("Estado", justify="center")

            for i, (flag, desc) in enumerate(flags, 1):
                is_debug_flag = flag == "--debug"
                if is_debug_flag and debug:
                    estado = "[green]✓ (bloqueado)[/green]"
                elif flag in selected:
                    estado = "[green]✓[/green]"
                else:
                    estado = "[dim]✗[/dim]"
                table.add_row(str(i), f"[yellow]{flag}[/yellow]", desc, estado)

            console.print(table)
            console.print(
                "[dim]Escribe el número para activar/desactivar. "
                "[bold]c[/bold] para añadir --category, "
                "[bold]t[/bold] para añadir --type, "
                "[bold]ok[/bold] para continuar.[/dim]"
            )
            raw = Prompt.ask("[bold]Opción[/bold]", default="ok").strip().lower()

            if raw == "ok":
                break
            elif raw == "c":
                cat = Prompt.ask(
                    "Categoría",
                    choices=["movie", "tv", "fanres"],
                    default="tv",
                )
                selected_cats = {f for f in selected if f.startswith("--category")}
                selected -= selected_cats
                selected.add(f"--category {cat}")
            elif raw == "t":
                tipo = Prompt.ask(
                    "Tipo",
                    choices=["disc", "remux", "encode", "webdl", "webrip", "hdtv"],
                    default="encode",
                )
                selected_types = {f for f in selected if f.startswith("--type")}
                selected -= selected_types
                selected.add(f"--type {tipo}")
            else:
                try:
                    idx = int(raw)
                except ValueError:
                    console.print("[red]Entrada no válida.[/red]")
                    continue

                if not (1 <= idx <= len(flags)):
                    console.print("[red]Número fuera de rango.[/red]")
                    continue

                flag, _ = flags[idx - 1]
                if flag == "--debug" and debug:
                    console.print("[yellow]El flag --debug está bloqueado en modo debug.[/yellow]")
                    continue

                if flag in selected:
                    selected.discard(flag)
                else:
                    selected.add(flag)

        result = []
        for flag in selected:
            parts = flag.split()
            result.extend(parts)
        return result

    def _flujo_ruta(self, tracker: str, debug: bool = False) -> None:
        """Sub-flujo: subir desde una ruta de archivo o carpeta"""
        while True:
            ruta_raw = Prompt.ask("[bold]Ruta al archivo o carpeta[/bold]").strip()
            ruta = Path(ruta_raw)
            if ruta.exists():
                break
            console.print(f"[red]✗ No existe: {ruta_raw}[/red]")

        if ruta.is_file():
            if ruta.suffix.lower() == ".mkv":
                console.print(f"[green]✓ Archivo MKV detectado:[/green] {ruta.name}")
            else:
                console.print(f"[yellow]⚠ Archivo no-MKV — se procesará de todas formas.[/yellow]")
        elif ruta.is_dir():
            mkv_files = list(ruta.rglob("*.mkv"))
            if mkv_files:
                console.print(
                    f"[green]✓ Directorio con {len(mkv_files)} archivo(s) MKV.[/green]"
                )
            else:
                console.print(
                    "[yellow]⚠ Directorio sin archivos MKV — se procesará de todas formas.[/yellow]"
                )

        flags = self._args_opcionales(debug=debug)

        cmd = ["python3", "upload.py", "--tracker", tracker, "--input", str(ruta)] + flags

        cmd_str = " ".join(cmd)
        console.print()
        console.print(
            Panel(
                f"[bold yellow]{cmd_str}[/bold yellow]",
                title="[bold]Comando a ejecutar[/bold]",
                border_style="yellow",
            )
        )

        if Confirm.ask("[bold]¿Ejecutar?[/bold]", default=True):
            self._ejecutar_comando(cmd)

    def _flujo_lista_existente(self, tracker: str) -> None:
        """Sub-flujo: usar lista .txt con rutas ya preparada"""
        while True:
            ruta_raw = Prompt.ask("[bold]Ruta al archivo .txt con la lista[/bold]").strip()
            ruta = Path(ruta_raw)
            if not ruta.exists():
                console.print(f"[red]✗ No existe: {ruta_raw}[/red]")
                continue
            if not ruta.is_file():
                console.print(f"[red]✗ No es un archivo: {ruta_raw}[/red]")
                continue
            lines = [l.strip() for l in ruta.read_text(encoding="utf-8").splitlines() if l.strip()]
            if not lines:
                console.print("[red]✗ El archivo está vacío.[/red]")
                continue
            break

        console.print(f"[green]✓ Lista con {len(lines)} entrada(s).[/green]")

        cmd = ["python3", "auto-upload.py", "--list", str(ruta), "--tracker", tracker]
        cmd_str = " ".join(cmd)
        console.print()
        console.print(
            Panel(
                f"[bold yellow]{cmd_str}[/bold yellow]",
                title="[bold]Comando a ejecutar[/bold]",
                border_style="yellow",
            )
        )

        if Confirm.ask("[bold]¿Ejecutar?[/bold]", default=True):
            self._ejecutar_comando(cmd)

    def _flujo_triage(self, tracker: str) -> None:
        """Sub-flujo: ejecutar triage_mkv.py y luego subir las listas generadas"""
        while True:
            ruta_raw = Prompt.ask("[bold]Directorio a analizar con triage[/bold]").strip()
            ruta = Path(ruta_raw)
            if ruta.is_dir():
                break
            console.print(f"[red]✗ No es un directorio válido: {ruta_raw}[/red]")

        console.print(f"\n[cyan]Ejecutando triage en:[/cyan] {ruta}")
        self._ejecutar_comando(["python3", "../extras/Triaje-mkv/triage_mkv.py", str(ruta)])

        hevc_files = sorted(self.base_dir.glob("todo-hevc-*.txt"))
        h264_files = sorted(self.base_dir.glob("sigue-h264-*.txt"))

        if not hevc_files and not h264_files:
            console.print("[yellow]No se encontraron listas generadas por triage.[/yellow]")
            return

        console.print()
        if hevc_files:
            console.print(f"[green]HEVC:[/green] {hevc_files[-1].name} ({sum(1 for l in hevc_files[-1].read_text().splitlines() if l.strip())} entradas)")
        if h264_files:
            console.print(f"[cyan]H264:[/cyan] {h264_files[-1].name} ({sum(1 for l in h264_files[-1].read_text().splitlines() if l.strip())} entradas)")

        opciones_disp = []
        opciones_text = ""
        if hevc_files:
            opciones_disp.append("1")
            opciones_text += "  [bold cyan][1][/bold cyan]  Subir lista HEVC\n"
        if h264_files:
            opciones_disp.append("2")
            opciones_text += "  [bold cyan][2][/bold cyan]  Subir lista H264\n"
        if hevc_files and h264_files:
            opciones_disp.append("3")
            opciones_text += "  [bold cyan][3][/bold cyan]  Subir ambas listas\n"

        console.print(
            Panel(
                opciones_text,
                title="[bold]¿Qué listas subir?[/bold]",
                border_style="cyan",
            )
        )

        eleccion = Prompt.ask(
            "[bold]Elige[/bold]",
            choices=opciones_disp,
            default=opciones_disp[0],
        )

        listas_a_subir = []
        if eleccion == "1" and hevc_files:
            listas_a_subir = [hevc_files[-1]]
        elif eleccion == "2" and h264_files:
            listas_a_subir = [h264_files[-1]]
        elif eleccion == "3":
            if hevc_files:
                listas_a_subir.append(hevc_files[-1])
            if h264_files:
                listas_a_subir.append(h264_files[-1])

        for lista in listas_a_subir:
            cmd = ["python3", "auto-upload.py", "--list", str(lista), "--tracker", tracker]
            cmd_str = " ".join(cmd)
            console.print()
            console.print(
                Panel(
                    f"[bold yellow]{cmd_str}[/bold yellow]",
                    title=f"[bold]Lista: {lista.name}[/bold]",
                    border_style="yellow",
                )
            )
            if Confirm.ask("[bold]¿Ejecutar?[/bold]", default=True):
                self._ejecutar_comando(cmd)

    # ------------------------------------------------------------------ #
    #  Helpers de configuración (Options 2 & 3)                          #
    # ------------------------------------------------------------------ #

    def _leer_config(self) -> Optional[dict]:
        """Carga data/config.py y devuelve el dict config, o None si no existe"""
        config_path = self.base_dir / "data" / "config.py"
        if not config_path.exists():
            return None
        try:
            import data.config as cfg_mod
            importlib.reload(cfg_mod)
            return cfg_mod.config
        except Exception as e:
            console.print(f"[red]Error al leer config.py: {e}[/red]")
            return None

    def _escribir_config_tracker(self, tracker: str, field: str, value) -> bool:
        """
        Reemplaza el valor de un campo dentro del bloque de un tracker en data/config.py.
        Devuelve True si tuvo éxito.
        """
        config_path = self.base_dir / "data" / "config.py"
        if not config_path.exists():
            console.print("[red]No se encontró data/config.py[/red]")
            return False

        try:
            text = config_path.read_text(encoding="utf-8")
        except Exception as e:
            console.print(f"[red]No se pudo leer config.py: {e}[/red]")
            return False

        if isinstance(value, bool):
            new_val_repr = "True" if value else "False"
            pattern = (
                r'((?:"|\')' + re.escape(tracker) + r'(?:"|\')' +
                r'\s*:\s*\{[^}]*?' +
                r'(?:"|\')' + re.escape(field) + r'(?:"|\')' +
                r'\s*:\s*)(?:True|False)'
            )
            replacement = r'\g<1>' + new_val_repr
        else:
            new_val_repr = str(value)
            pattern = (
                r'((?:"|\')' + re.escape(tracker) + r'(?:"|\')' +
                r'\s*:\s*\{[^}]*?' +
                r'(?:"|\')' + re.escape(field) + r'(?:"|\')' +
                r'\s*:\s*")([^"]*)"'
            )
            replacement = r'\g<1>' + new_val_repr.replace('\\', '\\\\') + '"'

        new_text, count = re.subn(pattern, replacement, text, count=1, flags=re.DOTALL)

        if count == 0:
            console.print(f"[yellow]No se encontró el campo '{field}' en el bloque '{tracker}'. Nada cambió.[/yellow]")
            return False

        try:
            config_path.write_text(new_text, encoding="utf-8")
        except Exception as e:
            console.print(f"[red]No se pudo escribir config.py: {e}[/red]")
            return False

        try:
            import data.config as cfg_mod
            importlib.invalidate_caches()
            importlib.reload(cfg_mod)
        except Exception:
            pass

        return True

    # ------------------------------------------------------------------ #
    #  Opción 2 — Configurar tracker existente                            #
    # ------------------------------------------------------------------ #

    def opcion_2_configurar(self, preselected_tracker: Optional[str] = None) -> None:
        """Configura api_key, announce_url y anon de un tracker en data/config.py"""
        config_path = self.base_dir / "data" / "config.py"
        if not config_path.exists():
            console.print(
                Panel(
                    "[red]No se encontró [bold]data/config.py[/bold].\n"
                    "Crea el archivo copiando [bold]data/backup/example_config.py[/bold] "
                    "a [bold]data/config.py[/bold] y vuelve a intentarlo.[/red]",
                    title="[bold red]Sin configuración[/bold red]",
                    border_style="red",
                )
            )
            return

        tracker = self._seleccionar_tracker(preselected=preselected_tracker)
        if tracker is None:
            return

        cfg = self._leer_config()
        if cfg is None:
            return

        tracker_cfg = cfg.get("TRACKERS", {}).get(tracker)
        if tracker_cfg is None:
            console.print(f"[red]Tracker '{tracker}' no encontrado en config.py[/red]")
            return

        def _show_status(tcfg: dict) -> None:
            api_key = tcfg.get("api_key", "")
            announce_url = tcfg.get("announce_url", "")
            anon = tcfg.get("anon", False)

            api_ok = bool(api_key) and "API_KEY" not in api_key and len(api_key) >= 32
            announce_ok = (
                bool(announce_url)
                and "Custom_Announce_URL" not in announce_url
                and announce_url.startswith("https://")
            )

            tbl = Table(
                show_header=True,
                header_style="bold cyan",
                border_style="dim",
                title=f"[bold]Estado de configuración: {tracker}[/bold]",
            )
            tbl.add_column("Campo", style="bold")
            tbl.add_column("Valor actual")
            tbl.add_column("Estado", justify="center")

            api_display = (
                f"{api_key[:8]}...{api_key[-4:]}"
                if api_key and len(api_key) > 12
                else api_key or "[dim]vacío[/dim]"
            )
            tbl.add_row(
                "api_key",
                api_display,
                "[green]✓[/green]" if api_ok else "[red]✗[/red]",
            )

            announce_display = announce_url if announce_url else "[dim]vacío[/dim]"
            tbl.add_row(
                "announce_url",
                announce_display,
                "[green]✓[/green]" if announce_ok else "[red]✗[/red]",
            )

            tbl.add_row(
                "anon",
                "[green]True[/green]" if anon else "[red]False[/red]",
                "[dim]—[/dim]",
            )
            console.print(tbl)
            return api_ok, announce_ok

        api_ok, announce_ok = _show_status(tracker_cfg)

        if not api_ok:
            console.print()
            console.print("[bold yellow]La API key no está configurada o es inválida.[/bold yellow]")
            while True:
                nueva_key = Prompt.ask(
                    f"[bold]API key para {tracker}[/bold] [dim](mín. 32 caracteres)[/dim]"
                ).strip()
                if len(nueva_key) < 32:
                    console.print(f"[red]✗ Demasiado corta ({len(nueva_key)} chars). Mínimo 32.[/red]")
                    continue
                if "API_KEY" in nueva_key:
                    console.print("[red]✗ El valor contiene 'API_KEY', introduce la clave real.[/red]")
                    continue
                break
            if self._escribir_config_tracker(tracker, "api_key", nueva_key):
                console.print("[green]✓ API key guardada.[/green]")

        if not announce_ok:
            console.print()
            console.print("[bold yellow]La announce URL no está configurada o es inválida.[/bold yellow]")
            while True:
                nueva_url = Prompt.ask(
                    f"[bold]Announce URL para {tracker}[/bold] [dim](https://...)[/dim]"
                ).strip()
                if not nueva_url.startswith("https://"):
                    console.print("[red]✗ Debe empezar por 'https://'.[/red]")
                    continue
                if "Custom_Announce_URL" in nueva_url:
                    console.print("[red]✗ El valor sigue siendo el placeholder, introduce la URL real.[/red]")
                    continue
                break
            if self._escribir_config_tracker(tracker, "announce_url", nueva_url):
                console.print("[green]✓ Announce URL guardada.[/green]")

        console.print()
        anon_actual = tracker_cfg.get("anon", False)
        cambiar_anon = Confirm.ask(
            f"[bold]¿Cambiar el modo anónimo?[/bold] [dim](actualmente: {'activado' if anon_actual else 'desactivado'})[/dim]",
            default=False,
        )
        if cambiar_anon:
            nuevo_anon = Confirm.ask("[bold]¿Activar modo anónimo?[/bold]", default=anon_actual)
            if self._escribir_config_tracker(tracker, "anon", nuevo_anon):
                console.print(f"[green]✓ Anon → {'True' if nuevo_anon else 'False'}[/green]")

        cfg_final = self._leer_config()
        if cfg_final:
            tracker_cfg_final = cfg_final.get("TRACKERS", {}).get(tracker, {})
            console.print()
            _show_status(tracker_cfg_final)

        console.print()
        if Confirm.ask(
            f"[bold]¿Continuar a la opción 1 con el tracker {tracker}?[/bold]",
            default=True,
        ):
            self.opcion_1_usar_tracker(preselected_tracker=tracker)

    # ------------------------------------------------------------------ #
    #  Opción 3 — Crear nuevo tracker                                     #
    # ------------------------------------------------------------------ #

    def opcion_3_crear_tracker(self) -> None:
        """Crea un nuevo tracker basado en la plantilla MILNU"""
        console.print()
        console.print(
            Panel(
                "\n"
                "  Crea un nuevo tracker usando [bold cyan]MILNU[/bold cyan] como plantilla.\n"
                "  Se crearán los archivos necesarios y se configurará el sistema.\n",
                title="[bold cyan]Crear nuevo tracker[/bold cyan]",
                border_style="cyan",
            )
        )

        nombre_completo = Prompt.ask(
            "[bold]Nombre completo del tracker[/bold] [dim](ej: MilNueve)[/dim]"
        ).strip()
        if not nombre_completo:
            console.print("[red]✗ El nombre no puede estar vacío.[/red]")
            return

        while True:
            abrev_raw = Prompt.ask(
                "[bold]Abreviación del tracker[/bold] [dim](ej: MILNU — se fuerza a mayúsculas)[/dim]"
            ).strip()
            abrev = abrev_raw.upper()
            if not abrev:
                console.print("[red]✗ La abreviación no puede estar vacía.[/red]")
                continue
            if not re.match(r'^[A-Z0-9]+$', abrev):
                console.print("[red]✗ Solo letras mayúsculas y números.[/red]")
                continue
            existentes = self._get_tracker_names_from_upload()
            if abrev in existentes:
                console.print(f"[red]✗ '{abrev}' ya existe en upload.py. Elige otra.[/red]")
                continue
            break

        while True:
            base_url = Prompt.ask(
                "[bold]URL base del tracker[/bold] [dim](ej: https://mitracker.ejemplo.es)[/dim]"
            ).strip()
            if not base_url.startswith("https://") and not base_url.startswith("http://"):
                console.print("[red]✗ La URL debe empezar por https:// o http://[/red]")
                continue
            base_url = base_url.rstrip("/")
            break

        console.print()
        console.print("[bold]Configuración inicial del tracker:[/bold]")

        api_key_inicial = ""
        while True:
            val = Prompt.ask(
                "  [bold]API Key[/bold] [dim](deja en blanco para configurar después)[/dim]",
                default="",
            ).strip()
            if val and (len(val) < 32 or "API_KEY" in val.upper()):
                console.print("[red]✗ La API Key parece inválida (mínimo 32 caracteres).[/red]")
                continue
            api_key_inicial = val
            break

        announce_url_inicial = ""
        while True:
            val = Prompt.ask(
                "  [bold]Announce URL[/bold] [dim](deja en blanco para configurar después)[/dim]",
                default="",
            ).strip()
            if val and (not val.startswith("https://") and not val.startswith("http://")):
                console.print("[red]✗ La announce URL debe empezar por https:// o http://[/red]")
                continue
            announce_url_inicial = val
            break

        tracker_py = self.base_dir / "src" / "trackers" / f"{abrev}.py"
        milnu_py = self.base_dir / "src" / "trackers" / "MILNU.py"
        upload_py = self.base_dir / "upload.py"
        config_py = self.base_dir / "data" / "config.py"

        errores = []

        if not milnu_py.exists():
            console.print("[red]✗ No se encontró la plantilla MILNU.py[/red]")
            return

        api_display = api_key_inicial[:8] + "..." if api_key_inicial else "[dim]pendiente[/dim]"
        ann_display = announce_url_inicial if announce_url_inicial else "[dim]pendiente[/dim]"
        console.print()
        console.print(
            Panel(
                f"  Tracker:      [bold]{nombre_completo}[/bold]\n"
                f"  Abrev:        [bold cyan]{abrev}[/bold cyan]\n"
                f"  URL base:     [bold]{base_url}[/bold]\n"
                f"  API Key:      {api_display}\n"
                f"  Announce URL: {ann_display}\n"
                f"  Archivo:      [dim]src/trackers/{abrev}.py[/dim]",
                title="[bold]Resumen de creación[/bold]",
                border_style="blue",
            )
        )

        if not Confirm.ask("[bold]¿Confirmar creación?[/bold]", default=True):
            console.print("[yellow]Operación cancelada.[/yellow]")
            return

        milnu_text = milnu_py.read_text(encoding="utf-8")
        nuevo_text = milnu_text
        nuevo_text = nuevo_text.replace(f"class MILNU(", f"class {abrev}(")
        nuevo_text = nuevo_text.replace(f"self.tracker = 'MILNU'", f"self.tracker = '{abrev}'")
        nuevo_text = nuevo_text.replace(
            f"self.source_flag = 'Milnueve'",
            f"self.source_flag = '{nombre_completo}'"
        )
        nuevo_text = nuevo_text.replace(
            "https://milnueve.neklair.es/api/torrents/upload",
            f"{base_url}/api/torrents/upload",
        )
        nuevo_text = nuevo_text.replace(
            "https://milnueve.neklair.es/api/torrents/filter",
            f"{base_url}/api/torrents/filter",
        )
        nuevo_text = re.sub(r'\bMILNU\b', abrev, nuevo_text)
        nuevo_text = re.sub(r'\bMilnueve\b', nombre_completo, nuevo_text)
        nuevo_text = re.sub(r'\bmilnu_name\b', f'{abrev.lower()}_name', nuevo_text)

        try:
            tracker_py.write_text(nuevo_text, encoding="utf-8")
            console.print(f"[green]✓ Creado:[/green] src/trackers/{abrev}.py")
        except Exception as e:
            console.print(f"[red]✗ No se pudo crear el archivo del tracker: {e}[/red]")
            errores.append(f"tracker .py: {e}")

        cfg_api = api_key_inicial if api_key_inicial else f"{abrev}_API_KEY"
        cfg_announce = announce_url_inicial if announce_url_inicial else f"{base_url}/announce/Custom_Announce_URL"

        if config_py.exists():
            try:
                cfg_text = config_py.read_text(encoding="utf-8")
                sig = f"\\n[center][b]PLEASE SEED {nombre_completo.upper()} FAMILY[/b][/center]\\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]"
                anon_sig = "\\n[center][url=https://codeberg.org/CvT/Uploadrr][img=40]https://i.ibb.co/n0jF73x/hacker.png[/img][/url][/center]"
                pr_sig = f"\\n [center][b][size=6]PERSONAL RELEASE[/size][/b][/center] \\n[center][b]PLEASE SEED {nombre_completo.upper()} FAMILY[/b][/center]\\n[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]"
                nuevo_bloque = (
                    f',\n\n    "{abrev}" : {{\n'
                    f'            "api_key" : "{cfg_api}",\n'
                    f'            "announce_url" : "{cfg_announce}",\n'
                    f'            "anon" : False,\n'
                    f'            "signature": "{sig}",\n'
                    f'            "anon_signature": "{anon_sig}",\n'
                    f'            "pr_signature": "{pr_sig}",\n'
                    f'            "anon_pr_signature": "{anon_sig}"\n'
                    f'}}'
                )
                trackers_match = re.search(r'"TRACKERS"\s*:\s*\{', cfg_text)
                if trackers_match:
                    # Find closing } of the TRACKERS dict using brace counting
                    depth = 1
                    pos = trackers_match.end()
                    insert_pos = -1
                    while pos < len(cfg_text) and depth > 0:
                        ch = cfg_text[pos]
                        if ch == '{':
                            depth += 1
                        elif ch == '}':
                            depth -= 1
                            if depth == 0:
                                insert_pos = pos
                        pos += 1
                    if insert_pos != -1:
                        cfg_text = cfg_text[:insert_pos] + nuevo_bloque + "\n" + cfg_text[insert_pos:]
                        config_py.write_text(cfg_text, encoding="utf-8")
                        console.print(f"[green]✓ Bloque añadido a data/config.py[/green]")
                        importlib.invalidate_caches()
                    else:
                        console.print("[yellow]⚠ No se encontró el cierre del dict TRACKERS en config.py[/yellow]")
                        errores.append("config.py: no se encontró cierre de TRACKERS")
                else:
                    console.print("[yellow]⚠ No se encontró 'TRACKERS' en config.py[/yellow]")
                    errores.append("config.py: no se encontró TRACKERS")
            except Exception as e:
                console.print(f"[red]✗ Error al modificar config.py: {e}[/red]")
                errores.append(f"config.py: {e}")
        else:
            console.print(
                "[yellow]⚠ data/config.py no existe — añade el bloque manualmente:[/yellow]\n"
                f'    "{abrev}" : {{\n'
                f'            "api_key" : "{cfg_api}",\n'
                f'            "announce_url" : "{cfg_announce}",\n'
                f'            "anon" : False\n'
                f'}}'
            )

        if upload_py.exists():
            try:
                up_text = upload_py.read_text(encoding="utf-8")
                new_up_text, count = re.subn(
                    r"('api'\s*:\s*\[)([^\]]+)(\])",
                    lambda m: m.group(1) + m.group(2).rstrip() + f", '{abrev}'" + m.group(3),
                    up_text,
                    count=1,
                )
                if count:
                    upload_py.write_text(new_up_text, encoding="utf-8")
                    console.print(f"[green]✓ '{abrev}' añadido a tracker_data['api'] en upload.py[/green]")
                else:
                    console.print("[yellow]⚠ No se encontró tracker_data['api'] en upload.py[/yellow]")
                    errores.append("upload.py: no se encontró tracker_data['api']")
            except Exception as e:
                console.print(f"[red]✗ Error al modificar upload.py: {e}[/red]")
                errores.append(f"upload.py: {e}")
        else:
            console.print("[yellow]⚠ upload.py no encontrado[/yellow]")
            errores.append("upload.py no encontrado")

        console.print()
        if errores:
            console.print(
                Panel(
                    "\n".join(f"  [red]✗[/red] {e}" for e in errores),
                    title="[bold red]Errores durante la creación[/bold red]",
                    border_style="red",
                )
            )
        else:
            console.print(
                Panel(
                    f"  [green]✓[/green] src/trackers/{abrev}.py creado\n"
                    f"  [green]✓[/green] data/config.py actualizado\n"
                    f"  [green]✓[/green] upload.py actualizado\n",
                    title=f"[bold green]Tracker '{abrev}' creado con éxito[/bold green]",
                    border_style="green",
                )
            )

        console.print()
        console.print(
            Panel(
                "\n"
                "  [bold yellow]INFORMACIÓN SOBRE TOR:[/bold yellow]\n\n"
                "  Algunos ISP (especialmente en España) bloquean conexiones a ciertos trackers.\n"
                "  Cloudflare puede estar bloqueado durante eventos deportivos.\n"
                "  [bold]Se recomienda configurar Tor[/bold] para mayor estabilidad.\n"
                "  El script [cyan]setup_milnueve.sh[/cyan] instala y configura Tor automáticamente.\n",
                title="[bold yellow]Tor — Estabilidad de conexión[/bold yellow]",
                border_style="yellow",
            )
        )

        setup_sh = self.base_dir / "setup_milnueve.sh"
        if setup_sh.exists():
            if Confirm.ask("[bold]¿Configurar Tor ahora?[/bold]", default=False):
                subprocess.run(["bash", str(setup_sh)])
        else:
            console.print("[dim]setup_milnueve.sh no encontrado — configura Tor manualmente si es necesario.[/dim]")

        console.print()
        if Confirm.ask(
            f"[bold]¿Continuar a configurar el tracker '{abrev}'?[/bold]",
            default=True,
        ):
            self.opcion_2_configurar(preselected_tracker=abrev)

    # ------------------------------------------------------------------ #
    #  Opción 4 — Modo debug (stub)                                       #
    # ------------------------------------------------------------------ #

    def opcion_4_debug(self) -> None:
        """Modo debug: lanza upload.py con --debug (sin subida real), log completo"""
        console.print()
        console.print(
            Panel(
                "\n"
                "  [bold red]ATENCIÓN:[/bold red] En este modo los torrents "
                "[bold]NO se subirán[/bold] al tracker.\n"
                "  Se activará el log completo en pantalla y en archivo.\n",
                title="[bold red]Modo Debug Activo[/bold red]",
                border_style="red",
            )
        )

        tracker = self._seleccionar_tracker()
        if tracker is None:
            return

        self._logger.info(f"Debug mode started for tracker: {tracker}")
        self._flujo_ruta(tracker, debug=True)

        session_log = self.base_dir / "logs" / f"rawncher_{datetime.now().strftime('%Y-%m-%d')}.log"
        console.print()
        console.print(
            Panel(
                f"[bold]Session log:[/bold] [cyan]{session_log}[/cyan]",
                title="[bold green]Sesión de debug completada[/bold green]",
                border_style="green",
            )
        )
        self._logger.info(f"Debug mode completed for tracker: {tracker}")

    # ------------------------------------------------------------------ #
    #  Opción 5 — Listar sesiones guardadas                               #
    # ------------------------------------------------------------------ #

    def opcion_5_listar_sesiones(self) -> None:
        """Lista todas las sesiones guardadas en una tabla Rich"""
        sessions = self._get_sessions()

        table = Table(
            show_header=True,
            header_style="bold cyan",
            border_style="dim",
            title="[bold]Sesiones guardadas[/bold]",
        )
        table.add_column("#", style="dim", justify="right")
        table.add_column("Archivo")
        table.add_column("Tracker", style="bold")
        table.add_column("Tamaño", justify="right")

        if not sessions:
            table.add_row("-", "[dim]Sin sesiones[/dim]", "", "")
        else:
            for i, path in enumerate(sessions, 1):
                tracker_name = "-"
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    tracker_name = data.get("name", "-")
                except Exception:
                    pass
                size = f"{path.stat().st_size} B"
                table.add_row(str(i), path.name, tracker_name, size)

        console.print(table)

    # ------------------------------------------------------------------ #
    #  Opción 6 — Cargar sesión guardada                                  #
    # ------------------------------------------------------------------ #

    def opcion_6_cargar_sesion(self) -> None:
        """Carga una sesión guardada y lanza la opción 1 con ese tracker"""
        sessions = self._get_sessions()

        if not sessions:
            console.print("[yellow]No hay sesiones guardadas.[/yellow]")
            return

        table = Table(
            show_header=True,
            header_style="bold cyan",
            border_style="dim",
            title="[bold]Sesiones guardadas[/bold]",
        )
        table.add_column("#", style="dim", justify="right")
        table.add_column("Archivo")
        table.add_column("Tracker", style="bold")
        table.add_column("Tamaño", justify="right")

        sessions_data = []
        for i, path in enumerate(sessions, 1):
            tracker_name = "-"
            session_dict = None
            try:
                session_dict = json.loads(path.read_text(encoding="utf-8"))
                tracker_name = session_dict.get("name", "-")
            except Exception:
                pass
            size = f"{path.stat().st_size} B"
            table.add_row(str(i), path.name, tracker_name, size)
            sessions_data.append(session_dict)

        console.print(table)

        raw = Prompt.ask("[bold]Número de sesión a cargar[/bold]", default="1")
        try:
            idx = int(raw)
        except ValueError:
            idx = 0

        if not (1 <= idx <= len(sessions)):
            console.print("[red]Número no válido.[/red]")
            return

        session = sessions_data[idx - 1]
        if session is None:
            console.print("[red]No se pudo leer la sesión seleccionada.[/red]")
            return

        tracker_name = session.get("name", "?")
        url = session.get("url", "?")
        api_key = session.get("api_key", "")
        api_display = (
            f"{api_key[:8]}..." if api_key and len(api_key) > 8 else api_key or "?"
        )
        saved_at = session.get("saved_at", "?")

        summary = (
            f"[bold]Tracker:[/bold]   {tracker_name}\n"
            f"[bold]URL:[/bold]       {url}\n"
            f"[bold]API Key:[/bold]   {api_display}\n"
            f"[bold]Origen:[/bold]    {session.get('source', '?')}\n"
            f"[bold]Guardada:[/bold]  {saved_at}"
        )
        console.print(
            Panel(
                summary,
                title="[bold green]Sesión cargada[/bold green]",
                border_style="green",
            )
        )

        self.opcion_1_usar_tracker(preselected_tracker=tracker_name)


if __name__ == "__main__":
    try:
        Rawncher().run()
    except KeyboardInterrupt:
        console.print("\n[yellow]¡Hasta luego![/yellow]")
        sys.exit(0)
