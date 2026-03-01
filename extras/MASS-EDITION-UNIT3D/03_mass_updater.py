import requests
from bs4 import BeautifulSoup
import time
import json
import os
import urllib.parse
import sys
import random

# --- CONFIGURACIÓN DE SESIÓN ---
BASE_URL = "https://milnueve.neklair.es"
COOKIE_VALUE = "eyJpdiI6Ik9rV21oSExwR1Vsc29zZ1MyYWJXeUE9PSIsInZhbHVlIjoiOWl4ZWlERXduVUJJR3RBQjdkcjJ5N2dXbGhpQmIxT1pOUnpmUjdNR2pVTmoxWGk1Y1N5enQwVGYrM01nZ0gzbkErWEphQmdZYzFocDN6V1V4eTkycUlVUUtRYzM0U3p2dkcrMkQ2WXNoNFp5TVpITS9nTDdzQmEzc1o4SWIrSVAiLCJtYWMiOiJiNmU3OWZjMWYxM2M1ZjAxNGY4MGM4NDU3MWZmMTRhN2UzNTdjNDc5MjljMzNmMThmZTU0YTBjZTJlODVhZGI2IiwidGFnIjoiIn0%3D" # Asegúrate de poner tu cookie actual

# --- CONFIGURACIÓN DE REEMPLAZOS ---
MSG_VIEJO = "[center][b]PLEASE SEED MILNUEVE FAMILY[/b][/center]"
BANNER_VIEJO = "[center][url=https://codeberg.org/CvT/Uploadrr][img=400]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]"

MSG_NUEVO = "[center][b]🌱 ¡La magia del P2P eres tú! Por favor, quédate compartiendo (seeding) para mantener viva la comunidad. 🌱[/b][/center]"
BANNER_NUEVO = "[center][url=https://github.com/RawSmokeTerribilus/RaW-Suite-TUI-ed][img=400]https://i.ibb.co/1NLtMkN/banner-milnueve.png[/img][/url][/center]"

# --- CARGA DE ÍNDICE ---
if not os.path.exists("mapeo_maestro.json"):
    print("❌ Falta mapeo_maestro.json")
    sys.exit()

with open("mapeo_maestro.json", "r", encoding='utf-8') as f:
    MAPA = json.load(f)

session = requests.Session()
session.cookies.set("milnueve_session", COOKIE_VALUE, domain="milnueve.neklair.es")
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest"
}

def procesar_torrent(torrent_id):
    edit_url = f"{BASE_URL}/torrents/{torrent_id}/edit"
    
    # Intento de lectura con manejo de errores de red
    try:
        res = session.get(edit_url, headers=headers, timeout=15)
    except Exception as e:
        return False, f"Error de red: {e}"

    if res.status_code == 429: return False, "RATE_LIMIT"
    if res.status_code in [502, 503, 504]: return False, "CLOUDFLARE_ERROR"
    if res.status_code != 200: return False, f"HTTP {res.status_code}"

    soup = BeautifulSoup(res.text, 'html.parser')
    name_input = soup.find('input', {'name': 'name'})
    if not name_input: return False, "Formulario no encontrado (¿Cookie caducada?)"
    
    nombre_tracker = name_input['value']
    ruta_carpeta = MAPA.get(nombre_tracker)
    if not ruta_carpeta: return False, "Mapping fallido"

    try:
        with open(os.path.join(ruta_carpeta, "meta.json"), "r", encoding='utf-8') as f:
            m = json.load(f)
        with open(os.path.join(ruta_carpeta, "[MILNU]DESCRIPTION.txt"), "r", encoding='utf-8') as f:
            desc_limpia = f.read().strip()
    except Exception as e: return False, f"Error local: {e}"

    # LISTA NEGRA: Evitar disparadores de validación
    blacklist = ['imdb', 'tmdb_id', 'tmdb_movie_id', 'tmdb_tv_id', 'tvdb', 'mal', 'anime', 'description']
    form = soup.find('textarea', {'name': 'description'}).find_parent('form')
    payload = {}
    
    for tag in form.find_all(['input', 'select', 'textarea']):
        name = tag.get('name')
        if not name or any(b in name.lower() for b in blacklist): continue
        if tag.get('type') in ['checkbox', 'radio']:
            if tag.has_attr('checked'): payload[name] = tag.get('value', '1')
        elif tag.name == 'select':
            opt = tag.find('option', selected=True)
            payload[name] = opt['value'] if opt else ""
        else:
            payload[name] = tag.get('value', tag.text)

    # REEMPLAZO EXACTO DE MENSAJE Y BANNER
    if BANNER_VIEJO in desc_limpia or MSG_VIEJO in desc_limpia:
        desc_limpia = desc_limpia.replace(MSG_VIEJO, MSG_NUEVO)
        desc_limpia = desc_limpia.replace(BANNER_VIEJO, BANNER_NUEVO)
    else:
        desc_limpia = f"{desc_limpia}\n\n{MSG_NUEVO}\n{BANNER_NUEVO}"

    payload['description'] = desc_limpia
    payload['_method'] = "PATCH"

    # INYECCIÓN DE METADATOS LIMPIA
    def add_meta(payload_key, json_key):
        val = m.get(json_key)
        if val and str(val) != '0' and str(val).lower() != 'none':
            if payload_key == 'imdb': payload[payload_key] = str(val).replace('tt', '')
            else: payload[payload_key] = str(val)

    is_tv = m.get('category') == 'TV' or m.get('tmdb_type') == 'TV' or "Season" in nombre_tracker
    add_meta('imdb', 'imdb_id')
    if is_tv:
        add_meta('tmdb_tv_id', 'tmdb')
        add_meta('tvdb', 'tvdb_id')
    else:
        # AQUÍ ESTÁ EL CAMBIO MÁGICO
        add_meta('tmdb_movie_id', 'tmdb')
        
    if m.get('anime'): add_meta('mal', 'mal_id')

    # ENVÍO
    target_url = form.get('action')
    if target_url.startswith('/'): target_url = BASE_URL + target_url
    
    xsrf = session.cookies.get('XSRF-TOKEN')
    if xsrf: headers["X-XSRF-TOKEN"] = urllib.parse.unquote(xsrf)
    headers["Referer"] = edit_url

    try:
        post_res = session.post(target_url, data=payload, headers=headers, timeout=20)
    except Exception as e:
        return False, f"Timeout de envío: {e}"
    
    if post_res.status_code in [200, 302]: return True, "OK"
    if post_res.status_code == 429: return False, "RATE_LIMIT"
    
    # PARCHE CHIVATO
    if post_res.status_code == 422:
        try:
            errores = post_res.json().get('errors', 'Motivo desconocido')
            return False, f"Error 422: {errores}"
        except:
            return False, "Error 422: No devolvió JSON"
            
    return False, f"Error {post_res.status_code}"

if __name__ == "__main__":
    if not os.path.exists("ids.txt"):
        print("❌ Fila ids.txt no encontrada.")
        sys.exit()

    # Cargar IDs totales
    with open("ids.txt", "r") as f:
        todos_los_ids = [line.strip() for line in f if line.strip()]

    # Cargar completados (Checkpoint)
    completados = set()
    if os.path.exists("completados.txt"):
        with open("completados.txt", "r") as f:
            completados = set(line.strip() for line in f if line.strip())

    ids_pendientes = [tid for tid in todos_los_ids if tid not in completados]
    
    print(f"📦 Total: {len(todos_los_ids)} | ✅ Completados: {len(completados)} | ⏳ Pendientes: {len(ids_pendientes)}")
    print("🚀 Iniciando motor de restauración recursiva...\n")

    for i, tid in enumerate(ids_pendientes, 1):
        reintentos = 0
        exito = False
        mensaje = ""

        # Bucle de reintentos para un mismo ID (por si Cloudflare bloquea temporalmente)
        while reintentos < 3 and not exito:
            print(f"[{i}/{len(ids_pendientes)}] Procesando ID {tid}... ", end="", flush=True)
            exito, mensaje = procesar_torrent(tid)

            if exito:
                print("✨ ¡Restaurado!")
                # Guardar checkpoint
                with open("completados.txt", "a") as f:
                    f.write(f"{tid}\n")
            else:
                if mensaje == "RATE_LIMIT" or mensaje == "CLOUDFLARE_ERROR":
                    print(f"⚠️ {mensaje} detectado. Pausando 30s...")
                    time.sleep(30)
                    reintentos += 1
                elif "Cookie" in mensaje:
                    print(f"❌ ¡ALERTA! {mensaje}")
                    print("🛑 Deteniendo el script. Actualiza la cookie y vuelve a lanzarlo.")
                    sys.exit()
                else:
                    print(f"❌ {mensaje}")
                    break # Si es otro error (ej. Mapping), saltamos al siguiente ID
        
        # Comportamiento humano: Jitter entre 4.5 y 7.5 segundos
        if i < len(ids_pendientes):
            delay = random.uniform(4.5, 7.5)
            time.sleep(delay)

    print("\n🏁 ¡Proceso masivo finalizado!")
