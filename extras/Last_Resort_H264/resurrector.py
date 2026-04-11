import os
import sys
import shutil
import subprocess
import argparse
import json
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.live import Live
from rich.table import Table

console = Console()

def get_video_info(file_path):
    """Recon de codecs y duración usando ffprobe"""
    cmd = [
        'ffprobe', '-v', 'error', '-select_streams', 'v:0',
        '-show_entries', 'stream=codec_name:format=duration',
        '-of', 'json', file_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        codec = data['streams'][0]['codec_name']
        duration = float(data['format']['duration'])
        return codec, duration
    except:
        return None, 0


class Resurrector:
    def __init__(self, list_path, threads=6):
        self.list_path = list_path
        self.threads = threads
        self.work_dir = Path.cwd()
        self.stats = {"ok": 0, "error": 0, "skipped": 0}

    def process(self):
        if not os.path.exists(self.list_path):
            console.print(f"[bold red]❌ Error:[/bold red] La lista {self.list_path} no existe.")
            return

        with open(self.list_path, 'r') as f:
            files = [line.strip() for line in f if line.strip()]

        console.print(Panel(f"🚀 [bold core]RESURRECTOR ENGINE v1.0[/bold core]\n[grey]Objetivo:[/grey] {len(files)} archivos\n[grey]Buffer NVMe:[/grey] {self.work_dir}", expand=False))

        for idx, source_path in enumerate(files):
            src = Path(source_path)
            if not src.exists():
                console.print(f"⚠️ [yellow]Saltado:[/yellow] No existe -> {source_path}")
                self.stats["skipped"] += 1
                continue

            # 1. IDEMPOTENCIA: ¿Ya es H.264?
            codec, src_duration = get_video_info(str(src))
            if codec == 'h264':
                console.print(f"✅ [blue]Skip:[/blue] Ya es H.264 -> {src.name}")
                self.stats["skipped"] += 1
                continue

            self.run_pipeline(src, src_duration)

    def run_pipeline(self, src, src_duration):
        tmp_input = self.work_dir / src.name
        tmp_output = self.work_dir / f"resurrected_{src.stem}.mkv"
        final_dest = src.with_suffix('.mkv')

        try:
            # A. COPIA AL NVMe (Local)
            console.print(f"\n📦 [bold]Step 1/4:[/bold] Copiando a NVMe... ⏩ {src.name}")
            shutil.copy2(src, tmp_input)

            # B. TRANSCODE
            console.print(f"🔥 [bold]Step 2/4:[/bold] Transcodificando (CPU Threads: {self.threads})...")
            
            # Comando optimizado: Map 0 (todo), H264 CRF 18, AAC para Tdarr
            ff_cmd = [
                'ffmpeg', '-v', 'error', '-stats', '-i', str(tmp_input),
                '-threads', str(self.threads),
                '-c:v', 'libx264', '-crf', '18', '-preset', 'slow', '-pix_fmt', 'yuv420p',
                '-map', '0:v:0', '-map', '0:a', '-c:a', 'aac', '-b:a', '192k',
                '-map', '0:s?', '-c:s', 'copy',
                '-y', str(tmp_output)
            ]
            
            subprocess.run(ff_cmd, check=True)

            # C. HEALTH CHECK
            console.print(f"🩺 [bold]Step 3/4:[/bold] Validando integridad...")
            _, new_duration = get_video_info(str(tmp_output))
            
            if abs(src_duration - new_duration) < 2.0:
                # D. SUSTITUCIÓN ATÓMICA
                console.print(f"💎 [bold]Step 4/4:[/bold] Sustituyendo original... 💾")
                shutil.move(str(tmp_output), str(final_dest))
                
                # Si el original no era .mkv, lo borramos
                if src != final_dest:
                    os.remove(src)
                
                self.stats["ok"] += 1
                console.print(f"✨ [bold green]¡ÉXITO![/bold green] {src.name} purificado.")
            else:
                raise Exception(f"Fallo de duración: Orig {src_duration}s vs New {new_duration}s")

        except Exception as e:
            console.print(f"💥 [bold red]FALLO CRÍTICO en {src.name}:[/bold red] {e}")
            self.stats["error"] += 1
            if tmp_output.exists(): os.remove(tmp_output)
        
        finally:
            # Limpieza del buffer NVMe
            if tmp_input.exists(): os.remove(tmp_input)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Resurrector de videos MPEG4 a H.264")
    parser.add_argument("lista", help="Ruta al archivo .txt con la lista de videos")
    parser.add_argument("--threads", type=int, default=6, help="Hilos de CPU (Default: 6)")
    args = parser.parse_args()

    engine = Resurrector(args.lista, args.threads)
    engine.process()
    
    console.print(Panel(f"📊 [bold]RESUMEN DE OPERACIÓN[/bold]\n✅ Procesados: {engine.stats['ok']}\n⏭️ Saltados: {engine.stats['skipped']}\n❌ Errores: {engine.stats['error']}"))
