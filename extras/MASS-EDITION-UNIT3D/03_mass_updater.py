import requests
from bs4 import BeautifulSoup
import time
import json
import os
import re
import urllib.parse
import sys
import random

# Add project root to path to import singularity_config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.status_manager import update_status
from config import (
    BASE_URL, COOKIE_NAME, COOKIE_VALUE, CUSTOM_USER_AGENT,
    DELAY_MIN, DELAY_MAX, TRACKER_ABBREV,
    EDIT_MODE,
    BANNER_URL_NUEVA, BANNER_IMG_NUEVA,
    FIRMA_TEXT_NUEVA, FIRMA_FULL_NUEVA,
    FIND_URL, REPLACE_URL,
    BLOCK_VIEJO, BLOCK_NUEVO,
    get_target_ids,
)

# --- CARGA DE ÍNDICES ---
if not os.path.exists("mapeo_maestro.json"):
    print("❌ Falta mapeo_maestro.json — ejecuta 01_scraper.py y 02_indexer.py primero")
    sys.exit()

with open("mapeo_maestro.json", "r", encoding="utf-8") as f:
    MAPA = json.load(f)  # {id: carpeta_local}

MAPA_TITULO = {}
if os.path.exists("mapeo_por_titulo.json"):
    with open("mapeo_por_titulo.json", "r", encoding="utf-8") as f:
        MAPA_TITULO = json.load(f)  # {nombre_tracker: carpeta_local} — fallback

session = requests.Session()
session.cookies.set(COOKIE_NAME, COOKIE_VALUE)

headers = {
    "User-Agent": CUSTOM_USER_AGENT,
    "X-Requested-With": "XMLHttpRequest",
}

# Regex para el bloque firma + banner completo.
# \r?\n? cubre tanto la variante concatenada como la separada por newline (RawLoadrr).
FIRMA_PATTERN = (
    r'\[center\]\[b\].*?\[/b\]\[/center\]'
    r'\r?\n?'
    r'\[center\]\[url=[^\]]*\]\[img=\d+\][^\[]*\[/img\]\[/url\]\[/center\]'
)

# Códigos HTTP de CF/WAF throttling — recuperables con pausa y reintento
CF_RATE_CODES = {429, 403, 503}
# Códigos de gateway caído — misma estrategia de reintento
CF_GATEWAY_CODES = {502, 504}


def _load_meta_json(filepath):
    """El Yunque: carga meta.json con sanitización de JSON malformado.
    Abre en modo texto con errors='replace', purga comas huérfanas via regex."""
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        raw = f.read()
    raw = re.sub(r',\s*([}\]])', r'\1', raw)  # comas huérfanas antes de cierre
    raw = re.sub(r',{2,}', ',', raw)           # comas dobles consecutivas
    return json.loads(raw)


def aplicar_modo_edicion(desc):
    """
    Aplica el modo de edición configurado a la descripción.
    Retorna (desc_modificada, True) si hay cambios, o (None, False) si SKIP_NO_MATCH.
    """
    if EDIT_MODE == "BANNER_URL":
        if not BANNER_URL_NUEVA:
            return None, False
        # Ancla al cierre de la firma con \r?\n? opcional entre [/center] y [center]:
        # RawLoadrr genera [/b][/center]\n[center][url=...] — no concatenados.
        # Captura grupo 1 = prefijo, grupo 2 = sufijo; reemplaza solo la URL.
        def _repl_url(m):
            return m.group(1) + BANNER_URL_NUEVA + m.group(2)
        desc_nueva, n = re.subn(
            r'(\[/b\]\[/center\]\r?\n?\[center\]\[url=)[^\]]+(\]\[img=\d+\])',
            _repl_url, desc, count=1
        )
        if n == 0:
            return None, False
        return desc_nueva, True

    elif EDIT_MODE == "BANNER_IMG":
        if not BANNER_IMG_NUEVA:
            return None, False
        # Mismo ancla con \r?\n? opcional entre firma y banner.
        def _repl_img(m):
            return m.group(1) + BANNER_IMG_NUEVA + m.group(2)
        desc_nueva, n = re.subn(
            r'(\[/b\]\[/center\]\r?\n?\[center\]\[url=[^\]]+\]\[img=\d+\])[^\[]+(\[/img\]\[/url\]\[/center\])',
            _repl_img, desc, count=1
        )
        if n == 0:
            return None, False
        return desc_nueva, True

    elif EDIT_MODE == "FIRMA_TEXT":
        if not FIRMA_TEXT_NUEVA:
            return None, False
        desc_nueva, n = re.subn(
            r'(?<=\[center\]\[b\]).*?(?=\[/b\]\[/center\])',
            FIRMA_TEXT_NUEVA, desc, count=1, flags=re.DOTALL
        )
        if n == 0:
            return None, False
        return desc_nueva, True

    elif EDIT_MODE == "FIRMA_FULL":
        if not FIRMA_FULL_NUEVA:
            return None, False
        desc_nueva, n = re.subn(
            FIRMA_PATTERN, FIRMA_FULL_NUEVA, desc,
            count=1, flags=re.IGNORECASE | re.DOTALL
        )
        if n == 0:
            return None, False
        return desc_nueva, True

    elif EDIT_MODE == "URL_REPLACE":
        if not FIND_URL or FIND_URL not in desc:
            return None, False
        return desc.replace(FIND_URL, REPLACE_URL), True

    elif EDIT_MODE == "BLOCK_REPLACE":
        if not BLOCK_VIEJO or BLOCK_VIEJO not in desc:
            return None, False
        return desc.replace(BLOCK_VIEJO, BLOCK_NUEVO), True

    else:
        print(f"❌ EDIT_MODE desconocido: {EDIT_MODE!r}")
        sys.exit(1)


def procesar_torrent(torrent_id):
    # --- GET: formulario del tracker (XSRF + nombre exacto + campos) ---
    edit_url = f"{BASE_URL}/torrents/{torrent_id}/edit"
    try:
        res = session.get(edit_url, headers=headers, timeout=15)
    except Exception as e:
        return "ERROR", f"Error de red: {e}"

    if res.status_code == 401:
        print(f"\n\n🔑 AUTENTICACIÓN FALLIDA (401). Tracker: {BASE_URL}")
        print("   → Actualiza el cookie en Singularity → UNIT3D → [C] Configurar")
        sys.exit(1)
    if res.status_code in CF_RATE_CODES:
        return "RATE_LIMIT", f"CF/WAF throttle en GET ({res.status_code})"
    if res.status_code in CF_GATEWAY_CODES:
        return "RATE_LIMIT", f"Gateway caído en GET ({res.status_code})"
    if res.status_code != 200:
        return "ERROR", f"HTTP {res.status_code}"

    soup = BeautifulSoup(res.text, "html.parser")
    name_input = soup.find("input", {"name": "name"})
    if not name_input:
        return "ERROR", "Formulario no encontrado (¿Cookie caducada?)"

    nombre_tracker = name_input["value"]

    # --- Localizar carpeta local: ID-keyed primero, título como fallback ---
    ruta_carpeta = MAPA.get(torrent_id) or MAPA_TITULO.get(nombre_tracker)
    if not ruta_carpeta:
        return "SKIP", f"Sin mapeo local ({nombre_tracker[:50]})"
    if not os.path.exists(ruta_carpeta):
        return "SKIP", f"Carpeta no existe: {ruta_carpeta}"

    # --- Localizar archivo de descripción local ---
    desc_file = os.path.join(ruta_carpeta, f"[{TRACKER_ABBREV}]DESCRIPTION.txt")
    if not os.path.exists(desc_file):
        txt_files = [f for f in os.listdir(ruta_carpeta) if f.endswith("DESCRIPTION.txt")]
        if txt_files:
            desc_file = os.path.join(ruta_carpeta, txt_files[0])
        else:
            return "SKIP", "Archivo de descripción no encontrado"

    try:
        with open(desc_file, "r", encoding="utf-8") as f:
            desc_original = f.read().strip()
    except Exception as e:
        return "ERROR", f"Error leyendo descripción local: {e}"

    # --- Aplicar modo de edición ---
    desc_modificada, cambio = aplicar_modo_edicion(desc_original)
    if not cambio:
        return "SKIP_NO_MATCH", "Patrón no encontrado"

    # --- Leer meta.json con El Yunque ---
    try:
        m = _load_meta_json(os.path.join(ruta_carpeta, "meta.json"))
    except json.JSONDecodeError as e:
        return "ERROR", f"meta.json inválido: {e}"
    except Exception as e:
        return "ERROR", f"Error leyendo meta.json: {e}"

    # --- Construir payload ---
    blacklist = ["imdb", "tmdb_id", "tmdb_movie_id", "tmdb_tv_id", "tvdb", "mal", "anime", "description"]
    desc_area = soup.find("textarea", {"name": "description"})
    if not desc_area:
        return "ERROR", "Campo 'description' no encontrado (¿página de error disfrazada de 200?)"
    form = desc_area.find_parent("form")
    if not form:
        return "ERROR", "Formulario padre no encontrado en el DOM"

    payload = {}
    for tag in form.find_all(["input", "select", "textarea"]):
        name = tag.get("name")
        if not name or any(b in name.lower() for b in blacklist):
            continue
        if tag.get("type") in ["checkbox", "radio"]:
            if tag.has_attr("checked"):
                payload[name] = tag.get("value", "1")
        elif tag.name == "select":
            opt = tag.find("option", selected=True)
            payload[name] = opt["value"] if opt else ""
        else:
            payload[name] = tag.get("value", tag.text)

    payload["description"] = desc_modificada
    payload["_method"] = "PATCH"

    # --- Inyección de metadatos ---
    is_tv = m.get("category") == "TV" or m.get("tmdb_type") == "TV" or "Season" in nombre_tracker

    def add_meta(payload_key, json_key):
        val = m.get(json_key)
        if val and str(val) not in ("0", "None", "none"):
            payload[payload_key] = str(val).replace("tt", "") if payload_key == "imdb" else str(val)

    add_meta("imdb", "imdb_id")
    if is_tv:
        add_meta("tmdb_tv_id", "tmdb")
        add_meta("tvdb", "tvdb_id")
    else:
        add_meta("tmdb_movie_id", "tmdb")
    if m.get("anime"):
        add_meta("mal", "mal_id")

    # --- Escribir a local PRIMERO ---
    try:
        with open(desc_file, "w", encoding="utf-8") as f:
            f.write(desc_modificada)
    except Exception as e:
        return "ERROR", f"Error escribiendo descripción local: {e}"

    # --- Pausa humana entre GET y POST (anti-ban: simula tiempo de lectura) ---
    time.sleep(random.uniform(0.8, 2.0))

    # --- Enviar al tracker ---
    target_url = form.get("action")
    if target_url.startswith("/"):
        target_url = BASE_URL + target_url

    xsrf = session.cookies.get("XSRF-TOKEN")
    if xsrf:
        headers["X-XSRF-TOKEN"] = urllib.parse.unquote(xsrf)
    headers["Referer"] = edit_url

    try:
        post_res = session.post(target_url, data=payload, headers=headers, timeout=20)
    except Exception as e:
        return "ERROR", f"Timeout de envío: {e}"

    if post_res.status_code in [200, 302]:
        return "OK", "OK"
    if post_res.status_code in CF_RATE_CODES:
        return "RATE_LIMIT", f"CF/WAF throttle en POST ({post_res.status_code})"
    if post_res.status_code in CF_GATEWAY_CODES:
        return "RATE_LIMIT", f"Gateway caído en POST ({post_res.status_code})"
    if post_res.status_code == 422:
        try:
            errores = post_res.json().get("errors", "Motivo desconocido")
            return "ERROR", f"Error 422: {errores}"
        except Exception:
            return "ERROR", "Error 422: No devolvió JSON"

    return "ERROR", f"Error {post_res.status_code}"


if __name__ == "__main__":
    if not os.path.exists("ids.txt"):
        print("❌ ids.txt no encontrado.")
        sys.exit()

    ids_en_rango = get_target_ids()

    completados = set()
    if os.path.exists("completados.txt"):
        with open("completados.txt", "r") as f:
            completados = set(line.strip() for line in f if line.strip())

    ids_pendientes = [tid for tid in ids_en_rango if tid not in completados]

    total = len(ids_en_rango)
    print(f"📦 En rango: {total} | ✅ Completados: {len(completados)} | ⏳ Pendientes: {len(ids_pendientes)}")
    print(f"🛠️  Modo de edición: {EDIT_MODE}")
    print("🚀 Iniciando motor de edición masiva...\n")

    n_ok = 0
    n_skip = 0
    n_error = 0

    for i, tid in enumerate(ids_pendientes, 1):
        prog = int((i / len(ids_pendientes)) * 100)
        update_status("UNIT3D", "Actualización Masiva", "PROCESSING", progress=prog,
                      details=f"Editando ID: {tid} ({i}/{len(ids_pendientes)})")

        reintentos = 0
        resultado = ""
        mensaje = ""

        while reintentos < 3:
            print(f"[{i}/{len(ids_pendientes)}] ID {tid}... ", end="", flush=True)
            resultado, mensaje = procesar_torrent(tid)

            if resultado == "OK":
                print("✨ Actualizado")
                n_ok += 1
                with open("completados.txt", "a") as f:
                    f.write(f"{tid}\n")
                break

            elif resultado == "SKIP_NO_MATCH":
                print("⏭  Sin cambios (patrón no encontrado)")
                n_skip += 1
                break

            elif resultado == "SKIP":
                print(f"⏭  Saltado: {mensaje}")
                n_skip += 1
                break

            elif resultado == "RATE_LIMIT":
                reintentos += 1
                pausa = 30 * reintentos  # backoff escalonado: 30s → 60s → 90s
                print(f"🛑 {mensaje} — Pausa {pausa}s (intento {reintentos}/3)...")
                time.sleep(pausa)

            else:
                print(f"❌ {mensaje}")
                n_error += 1
                break

        if resultado == "RATE_LIMIT" and reintentos >= 3:
            print(f"❌ Máx. reintentos alcanzados para ID {tid}")
            n_error += 1

        if i < len(ids_pendientes):
            delay = random.uniform(DELAY_MIN, DELAY_MAX)
            time.sleep(delay)

    print(f"\n🏁 ¡Proceso masivo finalizado!")
    print(f"   ✅ Actualizados : {n_ok}")
    print(f"   ⏭  Sin cambios  : {n_skip}  (patrón no encontrado / sin mapeo)")
    print(f"   ❌ Errores      : {n_error}")
    update_status("UNIT3D", "Actualización Masiva", "COMPLETED", progress=100,
                  details=f"OK:{n_ok} Skip:{n_skip} Err:{n_error}")
