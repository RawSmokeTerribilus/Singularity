import requests
import json
import os
import sys
import re
from rich.console import Console
from rich.table import Table
from rich.progress import Progress

# Configuración de imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from singularity_config import RADARR_URL, RADARR_API_KEY, SONARR_URL, SONARR_API_KEY

console = Console()

def is_garbage(tag):
    """Filtro inteligente para descartar grupos que no son grupos."""
    if not tag or tag.isdigit() or len(tag) < 2 or len(tag) > 15:
        return True
    # Patrones técnicos que NO son grupos
    garbage_patterns = [r'\d{3,4}p', r'x26[45]', r'h26[45]', r'AC3', r'DTS', r'AAC', r'10bit', r'HDR', r'HEVC', r'WEB', r'Bluray']
    for p in garbage_patterns:
        if re.search(p, tag, re.IGNORECASE):
            return True
    return False

def get_group(name):
    if name and '-' in name:
        potential = os.path.splitext(name)[0].split('-')[-1].strip()
        return None if is_garbage(potential) else potential
    return None

def fetch_data():
    all_found = {}
    headers = {"X-Api-Key": RADARR_API_KEY}
    
    with Progress() as progress:
        # Tarea Radarr
        t1 = progress.add_task("[cyan]Consultando Radarr...", total=100)
        try:
            r = requests.get(f"{RADARR_URL}/api/v3/movie", headers=headers, timeout=5)
            movies = r.json()
            for m in movies:
                file = m.get('movieFile')
                if file:
                    group = get_group(file.get('relativePath'))
                    if group:
                        quality = file.get('quality', {}).get('quality', {}).get('name', 'WEBDL')
                        all_found[group] = "WEBDL" if "WEB" in quality.upper() else "Bluray"
            progress.update(t1, completed=100)
        except:
            console.print("[red]✗ Radarr offline[/red]")

    return all_found

def main():
    console.print("[bold magenta]=== Singularity Tag Ingestor v2.0 ===[/bold magenta]\n")
    
    tags_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../RawLoadrr/data/tags.json'))
    with open(tags_path, 'r') as f:
        tags = json.load(f)

    new_data = fetch_data()
    
    table = Table(title="Nuevos Grupos Detectados")
    table.add_column("Grupo", style="green")
    table.add_column("Tipo", style="cyan")
    table.add_column("Estado", style="yellow")

    added = 0
    for g, t in new_data.items():
        if g not in tags:
            tags[g] = {"type": t}
            table.add_row(g, t, "NUEVO")
            added += 1
    
    if added > 0:
        console.print(table)
        with open(tags_path, 'w') as f:
            json.dump(tags, f, indent=4)
        console.print(f"\n[bold green]✓ ¡Éxito! {added} grupos reales añadidos.[/bold green]")
    else:
        console.print("\n[yellow]No se han encontrado grupos nuevos (o todos eran basura).[/yellow]")

if __name__ == "__main__":
    main()
