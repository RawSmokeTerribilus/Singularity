#!/usr/bin/env python3
import os
import sys
import argparse
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

console = Console()

class Cleaner:
    def __init__(self, list_path, max_size_mb=1):
        self.list_path = list_path
        self.max_size_mb = max_size_mb
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.stats = {"deleted": 0, "skipped_safe": 0, "not_found": 0, "error": 0}

    def process(self):
        if not os.path.exists(self.list_path):
            console.print(f"[bold red]❌ Error:[/bold red] La lista {self.list_path} no existe.")
            return

        with open(self.list_path, 'r') as f:
            files = [line.strip() for line in f if line.strip()]

        console.print(Panel(f"🗑️ [bold]CLEANER v1.0[/bold]\n[grey]Objetivo:[/grey] {len(files)} archivos\n[grey]Máx tamaño seguro:[/grey] {self.max_size_mb}MB", expand=False))

        for idx, source_path in enumerate(files, 1):
            src = Path(source_path)
            
            if not src.exists():
                console.print(f"⚠️ [yellow]No existe:[/yellow] {source_path}")
                self.stats["not_found"] += 1
                continue

            # Chequeo de tamaño
            file_size = src.stat().st_size
            
            if file_size > self.max_size_bytes:
                console.print(f"🛡️ [red]SEGURO - Saltado:[/red] {source_path} ({file_size/1024/1024:.2f}MB)")
                self.stats["skipped_safe"] += 1
                continue

            try:
                os.remove(src)
                console.print(f"✅ [green]Borrado:[/green] {src.name} ({file_size} bytes)")
                self.stats["deleted"] += 1
            except Exception as e:
                console.print(f"💥 [bold red]ERROR al borrar {src.name}:[/bold red] {e}")
                self.stats["error"] += 1

        console.print(Panel(f"📊 [bold]RESUMEN[/bold]\n✅ Borrados: {self.stats['deleted']}\n🛡️ Saltados (seguros): {self.stats['skipped_safe']}\n⚠️ No encontrados: {self.stats['not_found']}\n❌ Errores: {self.stats['error']}"))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Limpiador de archivos dummy/corruptos")
    parser.add_argument("lista", help="Ruta al archivo .txt con la lista de archivos a borrar")
    parser.add_argument("--max-size", type=int, default=1, help="Tamaño máximo seguro en MB (Default: 1)")
    args = parser.parse_args()

    cleaner = Cleaner(args.lista, args.max_size)
    cleaner.process()
