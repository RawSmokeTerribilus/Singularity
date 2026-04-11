import os
import json
import re
import sys

# Add project root to path to import singularity_config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.status_manager import update_status
from config import TMP_DIR_PATH as TMP_ROOT

OUTPUT_INDEX = "mapeo_maestro.json"
FAILED_PARSE_LOG = "failed_parse.log"
SAVE_INTERVAL = 50


def _normalizar(s):
    """Normaliza un string para comparación flexible (fuzzy match)."""
    s = s.lower()
    s = re.sub(r'[:\-\(\)\[\]]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def _load_meta_json(filepath):
    """El Yunque: carga meta.json con sanitización de JSON malformado.

    Abre en modo texto con errors='replace', purga comas huérfanas via regex,
    luego intenta json.loads(). Si falla, propaga la excepción para auditoría.
    """
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        raw = f.read()
    # Purgar comas huérfanas antes de cierres de array/objeto
    raw = re.sub(r',\s*([}\]])', r'\1', raw)
    # Purgar comas dobles consecutivas
    raw = re.sub(r',{2,}', ',', raw)
    return json.loads(raw)


def _guardar_estado(indice, por_titulo):
    """Volcado atómico de ambos mapeos. Escribe en .tmp y usa os.replace()."""
    tmp = OUTPUT_INDEX + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(indice, f, ensure_ascii=False, indent=4)
    os.replace(tmp, OUTPUT_INDEX)

    tmp2 = "mapeo_por_titulo.tmp.json"
    with open(tmp2, "w", encoding="utf-8") as f:
        json.dump(por_titulo, f, ensure_ascii=False, indent=4)
    os.replace(tmp2, "mapeo_por_titulo.json")


def generar_indice():
    # --- CARGAR MAPA DE TÍTULOS DEL SCRAPER (id → título) ---
    if not os.path.exists("titulos_mapa.json"):
        print("❌ Falta titulos_mapa.json — ejecuta primero 01_scraper.py")
        return

    with open("titulos_mapa.json", "r", encoding="utf-8") as f:
        titulos_mapa = json.load(f)

    # Invertir para buscar por título → {título: id}
    titulo_a_id = {titulo: tid for tid, titulo in titulos_mapa.items()}
    # Versión normalizada para fuzzy match
    titulo_a_id_norm = {_normalizar(titulo): tid for titulo, tid in titulo_a_id.items()}

    print(f"🔍 Escaneando carpetas en {TMP_ROOT}...")
    update_status("UNIT3D", "Indexado Maestro", "PROCESSING", details=f"Escaneando: {TMP_ROOT}")

    if not os.path.exists(TMP_ROOT):
        print(f"❌ El directorio {TMP_ROOT} no existe.")
        return

    # --- MODO RESUME ---
    indice = {}
    por_titulo = {}

    if os.path.exists(OUTPUT_INDEX):
        with open(OUTPUT_INDEX, "r", encoding="utf-8") as f:
            indice = json.load(f)
        print(f"♻️  Resume: {len(indice)} carpetas ya indexadas.")

    if os.path.exists("mapeo_por_titulo.json"):
        with open("mapeo_por_titulo.json", "r", encoding="utf-8") as f:
            por_titulo = json.load(f)

    carpetas_indexadas = set(indice.values())  # O(1) lookup para skip

    sin_id = []
    errores = []
    carpetas_procesadas = 0

    for root, dirs, files in os.walk(TMP_ROOT):
        if "meta.json" not in files:
            continue

        # --- SKIP SI YA INDEXADO (MODO RESUME) ---
        if root in carpetas_indexadas:
            continue

        # --- EL YUNQUE: carga con sanitización ---
        try:
            data = _load_meta_json(os.path.join(root, "meta.json"))
        except json.JSONDecodeError as e:
            msg = f"PARSE_ERROR: {os.path.join(root, 'meta.json')} — {e}"
            errores.append((root, str(e)))
            print(f"⚠️ JSON inválido (logueado): {root}")
            with open(FAILED_PARSE_LOG, "a", encoding="utf-8") as log:
                log.write(msg + "\n")
            continue
        except Exception as e:
            msg = f"READ_ERROR: {os.path.join(root, 'meta.json')} — {e}"
            errores.append((root, str(e)))
            print(f"⚠️ Error leyendo {root}: {e}")
            with open(FAILED_PARSE_LOG, "a", encoding="utf-8") as log:
                log.write(msg + "\n")
            continue

        nombre_local = data.get("name")
        if not nombre_local:
            continue

        # Mapa fallback: siempre (cubre los casos sin ID)
        por_titulo[nombre_local] = root

        # --- EMPAREJAMIENTO: exacto primero, luego fuzzy normalizado ---
        tid = titulo_a_id.get(nombre_local)
        if not tid:
            tid = titulo_a_id_norm.get(_normalizar(nombre_local))

        if tid:
            indice[tid] = root
            carpetas_indexadas.add(root)
        else:
            sin_id.append((nombre_local, root))

        carpetas_procesadas += 1
        if carpetas_procesadas % SAVE_INTERVAL == 0:
            _guardar_estado(indice, por_titulo)
            print(f"💾 Checkpoint: {carpetas_procesadas} carpetas procesadas, {len(indice)} mapeadas.")

    # Volcado final
    _guardar_estado(indice, por_titulo)

    print(f"\n✅ mapeo_maestro.json generado")
    print(f"   🔗 Mapeados (ID ↔ carpeta)  : {len(indice)}")
    print(f"   📚 Fallback (título ↔ carpeta): {len(por_titulo)}")
    print(f"   ❓ Sin ID en titulos_mapa    : {len(sin_id)}")
    if sin_id:
        for nombre, carpeta in sin_id[:10]:
            print(f"      • {nombre!r} → {carpeta}")
        if len(sin_id) > 10:
            print(f"      ... y {len(sin_id) - 10} más")
    if errores:
        print(f"   ❌ Errores de lectura       : {len(errores)} (ver {FAILED_PARSE_LOG})")

    update_status("UNIT3D", "Indexado Maestro", "COMPLETED", progress=100,
                  details=f"Mapeadas {len(indice)} carpetas")

if __name__ == "__main__":
    generar_indice()
