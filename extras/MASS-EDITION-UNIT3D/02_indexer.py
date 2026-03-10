import os
import json
import sys

# Add project root to path to import singularity_config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.status_manager import update_status
try:
    from singularity_config import TMP_DIR_PATH as TMP_ROOT
except ImportError:
    # Fallback to hardcoded for standalone use or if config is missing
    TMP_ROOT = "/app/RawLoadrr/tmp" # Default in Docker

OUTPUT_INDEX = "mapeo_maestro.json"

def generar_indice():
    indice = {}
    print(f"🔍 Escaneando carpetas en {TMP_ROOT}...")
    update_status("UNIT3D", "Indexado Maestro", "PROCESSING", details=f"Escaneando: {TMP_ROOT}")
    
    if not os.path.exists(TMP_ROOT):
        print(f"❌ El directorio {TMP_ROOT} no existe.")
        return

    # Recorremos todas las subcarpetas de tmp
    for root, dirs, files in os.walk(TMP_ROOT):
        if "meta.json" in files:
            try:
                with open(os.path.join(root, "meta.json"), 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # El campo 'name' del JSON es la clave que nos une al tracker
                    nombre_tracker = data.get('name')
                    if nombre_tracker:
                        indice[nombre_tracker] = root
            except Exception as e:
                print(f"⚠️ Error leyendo {root}: {e}")

    with open(OUTPUT_INDEX, 'w', encoding='utf-8') as f:
        json.dump(indice, f, indent=4)
    
    print(f"✅ Índice creado con {len(indice)} entradas en {OUTPUT_INDEX}")
    update_status("UNIT3D", "Indexado Maestro", "COMPLETED", progress=100, details=f"Indexadas {len(indice)} carpetas")

if __name__ == "__main__":
    generar_indice()
