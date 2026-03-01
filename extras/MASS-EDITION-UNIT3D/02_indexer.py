import os
import json

TMP_ROOT = "/home/rawserver/scripts/Media-Management/WIP-milnueve-Uploadrr/tmp"
OUTPUT_INDEX = "mapeo_maestro.json"

def generar_indice():
    indice = {}
    print(f"🔍 Escaneando carpetas en {TMP_ROOT}...")
    
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

if __name__ == "__main__":
    generar_indice()
