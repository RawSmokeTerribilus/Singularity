#!/usr/bin/env python3
"""
Script para hacer triaje de archivos MKV por codec de video.
Genera dos listas: una con carpetas 100% HEVC y otra con carpetas que tienen H264.
Uso: python3 triage_mkv.py [ruta]
Si no especificas ruta, usa la ruta actual.
"""

import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

HEVC_CODECS = {'hevc', 'h265', 'x265'}
LEGACY_CODECS = {'h264', 'x264', 'mpeg2', 'mpeg1', 'vp8', 'vp9', 'av1'}

def get_date_string():
    """Retorna la fecha en formato DD-MM-YY"""
    return datetime.now().strftime("%d-%m-%y")

def get_video_codec(mkv_file):
    """Extrae el codec de video de un archivo MKV usando mediainfo"""
    try:
        result = subprocess.run(
            ['mediainfo', '--Inform=Video;%Format%', mkv_file],
            capture_output=True,
            text=True,
            timeout=5
        )
        codec = result.stdout.strip().lower()
        return codec if codec else None
    except Exception:
        return None

def analyze_folder(folder_path):
    """
    Analiza una carpeta (no recursiva para evitar solapamientos) y retorna:
    - is_hevc_only: True si todos los MKV en esta carpeta son HEVC
    - has_legacy: True si hay al menos un H264 u otro legacy
    """
    # Usamos glob simple (*) en lugar de rglob (**) para que scan_directory
    # que ya es recursivo, maneje la jerarquía carpeta por carpeta.
    mkv_files = list(Path(folder_path).glob('*.mkv'))
    
    if not mkv_files:
        return None, False
    
    codecs_found = set()
    for mkv_file in mkv_files:
        codec = get_video_codec(str(mkv_file))
        if codec:
            codecs_found.add(codec)
    
    if not codecs_found:
        return None, False
    
    is_hevc_only = codecs_found <= HEVC_CODECS
    # Consideramos legacy cualquier cosa que no esté en HEVC_CODECS
    has_legacy = not is_hevc_only
    
    return is_hevc_only, has_legacy

def scan_directory(root_path):
    """
    Recorre el directorio y retorna dos listas de carpetas:
    - todo_hevc: carpetas con solo HEVC
    - sigue_h264: carpetas con H264 o legacy
    """
    todo_hevc = []
    sigue_h264 = []
    
    print(f"📁 Escaneando: {root_path}")
    print(f"⏳ Analizando carpetas...")
    
    # Recorrer todas las carpetas recursivamente
    for root, dirs, files in os.walk(root_path):
        # SOLO analizamos si la carpeta actual tiene MKVs directos
        mkv_count = len([f for f in files if f.lower().endswith('.mkv')])
        
        if mkv_count > 0:
            is_hevc, has_legacy = analyze_folder(root)
            
            if is_hevc is None:
                continue
            
            if is_hevc:
                todo_hevc.append(root)
                print(f"✅ {root}")
            elif has_legacy:
                sigue_h264.append(root)
                print(f"⏳ {root}")
    
    return todo_hevc, sigue_h264

def main():
    # Obtener ruta desde argumentos o usar la actual
    root_path = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    
    # Validar que la ruta existe
    if not os.path.isdir(root_path):
        print(f"❌ Error: '{root_path}' no es un directorio válido")
        sys.exit(1)
    
    # Ejecutar análisis
    todo_hevc, sigue_h264 = scan_directory(root_path)
    
    # Generar nombre de archivos con fecha
    date_str = get_date_string()
    file_hevc = f"todo-hevc-{date_str}.txt"
    file_h264 = f"sigue-h264-{date_str}.txt"
    
    # Guardar listas
    with open(file_hevc, 'w') as f:
        for path in sorted(todo_hevc):
            f.write(path + '\n')
    
    with open(file_h264, 'w') as f:
        for path in sorted(sigue_h264):
            f.write(path + '\n')
    
    # Resumen
    print(f"\n{'='*60}")
    print(f"📊 Resultado del análisis")
    print(f"{'='*60}")
    print(f"✅ Carpetas 100% HEVC: {len(todo_hevc)}")
    print(f"   Guardadas en: {file_hevc}")
    print(f"\n⏳ Carpetas con H264/Legacy: {len(sigue_h264)}")
    print(f"   Guardadas en: {file_h264}")
    print(f"{'='*60}\n")

if __name__ == '__main__':
    main()
