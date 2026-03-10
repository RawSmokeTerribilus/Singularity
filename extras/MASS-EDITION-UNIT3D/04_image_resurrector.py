import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from core.status_manager import update_status
from singularity_config import BASE_URL, COOKIE_VALUE, IMGBB_API, PTSCREENS_API, MSG_NUEVO, FIRMAS_VIEJAS, TMP_DIR_PATH, get_target_ids

import requests
from bs4 import BeautifulSoup
import time
import json
import re
from datetime import datetime
import urllib.parse



# ==========================================
# 🔄 MOTORES DE SUBIDA (CON FALLBACK AUTOMÁTICO)
# ==========================================
uploader_actual = 0

def subir_imagen(ruta_imagen, log_buffer):
    global uploader_actual
    
    # Intentamos hasta 2 veces (una por cada host) para esquivar caídas
    for intento in range(2):
        host = uploader_actual % 2
        uploader_actual += 1

        try:
            if host == 0:
                log_buffer.append(f"  [>] Subiendo a ImgBB: {os.path.basename(ruta_imagen)}")
                with open(ruta_imagen, "rb") as f:
                    res = requests.post("https://api.imgbb.com/1/upload", data={"key": IMGBB_API}, files={"image": f}, timeout=60)
                url_directa = res.json().get('data', {}).get('url')
            else:
                log_buffer.append(f"  [>] Subiendo a PtScreens: {os.path.basename(ruta_imagen)}")
                with open(ruta_imagen, "rb") as f:
                    res = requests.post("https://ptscreens.com/api/1/upload", data={"key": PTSCREENS_API}, files={"source": f}, timeout=60)
                url_directa = res.json().get('image', {}).get('url')
                
            if url_directa: 
                log_buffer.append(f"      [OK] URL: {url_directa}")
                return url_directa
            else: 
                log_buffer.append(f"      [WARN] El host no devolvió URL. Fallback al otro host...")
        except Exception as e:
            log_buffer.append(f"      [WARN] Error de red o timeout ({e}). Fallback al otro host...")
        
        # Pausa táctica de 3 segundos antes de reintentar con el otro servidor
        time.sleep(3)
        
    log_buffer.append("      [ERROR] Ambos hosts fallaron consecutivamente.")
    return None

# ==========================================
# 🚀 MOTOR DE SINCRONIZACIÓN
# ==========================================
with open("mapeo_maestro.json", "r", encoding='utf-8') as f: MAPA = json.load(f)

session = requests.Session()
session.cookies.set("milnueve_session", COOKIE_VALUE, domain="milnueve.neklair.es")
headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)", "X-Requested-With": "XMLHttpRequest"}

def procesar_total(torrent_id):
    log_buffer = [f"=== INICIO SINCRONIZACIÓN ID {torrent_id} ==="]
    edit_url = f"{BASE_URL}/torrents/{torrent_id}/edit"
    
    try: res = session.get(edit_url, headers=headers, timeout=15)
    except Exception as e: return False, f"Error red: {e}", log_buffer

    if res.status_code != 200: return False, f"HTTP {res.status_code}", log_buffer

    soup = BeautifulSoup(res.text, 'html.parser')
    nombre_web = soup.find('input', {'name': 'name'})['value']
    
    ruta_carpeta = MAPA.get(nombre_web)
    if not ruta_carpeta or not os.path.exists(ruta_carpeta): return False, "Mapping fallido", log_buffer
    
    ruta_txt_local = os.path.join(ruta_carpeta, "[MILNU]DESCRIPTION.txt")
    if not os.path.exists(ruta_txt_local): return False, "Falta TXT local", log_buffer

    with open(ruta_txt_local, "r", encoding="utf-8") as f: desc_local = f.read()

    if 'pixhost.to' not in desc_local.lower() and 'PLEASE SEED' not in desc_local:
        return True, "Ya está limpio", log_buffer

    archivos_locales = os.listdir(ruta_carpeta)
    imagenes_locales = sorted([f for f in archivos_locales if f.lower().endswith(('.png', '.jpg', '.jpeg')) and not f.startswith('.')])[:6]
    
    if not imagenes_locales: return False, "No hay imágenes locales", log_buffer

    nuevos_bbcodes = []
    for img in imagenes_locales:
        url_nueva = subir_imagen(os.path.join(ruta_carpeta, img), log_buffer)
        if url_nueva:
            nuevos_bbcodes.append(f"[url={url_nueva}][img=500]{url_nueva}[/img][/url]")
            time.sleep(1)
        else: return False, f"Fallo al subir {img}", log_buffer

    bloque_bbcode = f"[center]\n{' '.join(nuevos_bbcodes)}\n[/center]"

    # --- LIMPIEZA Y RECONSTRUCCIÓN CON TRAILER ---
    desc_limpia = desc_local
    for firma in FIRMAS_VIEJAS: desc_limpia = desc_limpia.replace(firma, "")
    desc_limpia = re.sub(r'\[url=[^\]]*pixhost\.to[^\]]*\]\[img.*?\[/img\]\[/url\]\s*', '', desc_limpia, flags=re.IGNORECASE | re.DOTALL)
    desc_limpia = re.sub(r'\[center\]\s*\[/center\]\s*', '', desc_limpia, flags=re.IGNORECASE)

    # Buscar y extraer el trailer (video)
    trailer_bbcode = ""
    video_match = re.search(r'\[video\].*?\[/video\]', desc_limpia, flags=re.IGNORECASE | re.DOTALL)
    if video_match:
        trailer_bbcode = video_match.group(0)
        desc_limpia = desc_limpia.replace(trailer_bbcode, "") # Lo quitamos de donde estaba

    # Montamos el bloque final: Trailer -> Fotos -> Banner -> Resto de info
    partes_descripcion = []
    if trailer_bbcode:
        partes_descripcion.append(f"[center]{trailer_bbcode}[/center]")
    partes_descripcion.append(bloque_bbcode)
    partes_descripcion.append(MSG_NUEVO)
    if desc_limpia.strip():
        partes_descripcion.append(desc_limpia.strip())

    desc_final = "\n\n".join(partes_descripcion)

    # Guardar en disco
    try:
        with open(ruta_txt_local, "w", encoding='utf-8') as f: f.write(desc_final)
    except Exception as e: return False, f"Error escribiendo TXT: {e}", log_buffer

    # --- ENVÍO AL TRACKER ---
    form = soup.find('textarea', {'name': 'description'}).find_parent('form')
    try:
        with open(os.path.join(ruta_carpeta, "meta.json"), "r", encoding='utf-8') as f: m = json.load(f)
    except: return False, "Falta meta.json", log_buffer

    blacklist = ['imdb', 'tmdb_id', 'tmdb_movie_id', 'tmdb_tv_id', 'tvdb', 'mal', 'anime', 'description']
    payload = {}
    for tag in form.find_all(['input', 'select', 'textarea']):
        name = tag.get('name')
        if not name or any(b in name.lower() for b in blacklist): continue
        if tag.get('type') in ['checkbox', 'radio']:
            if tag.has_attr('checked'): payload[name] = tag.get('value', '1')
        elif tag.name == 'select':
            opt = tag.find('option', selected=True)
            payload[name] = opt['value'] if opt else ""
        else: payload[name] = tag.get('value', tag.text)

    payload['description'] = desc_final
    payload['_method'] = "PATCH"

    def add_meta(p_key, j_key):
        val = m.get(j_key)
        if val and str(val) not in ['0', 'None']:
            payload[p_key] = str(val).replace('tt', '') if p_key == 'imdb' else str(val)

    is_tv = m.get('category') == 'TV' or m.get('tmdb_type') == 'TV' or "Season" in nombre_web
    add_meta('imdb', 'imdb_id')
    if is_tv: add_meta('tmdb_tv_id', 'tmdb'); add_meta('tvdb', 'tvdb_id')
    else: add_meta('tmdb_movie_id', 'tmdb')
    if m.get('anime'): add_meta('mal', 'mal_id')

    target_url = form.get('action')
    if target_url.startswith('/'): target_url = BASE_URL + target_url
    
    xsrf = session.cookies.get('XSRF-TOKEN')
    if xsrf: headers["X-XSRF-TOKEN"] = urllib.parse.unquote(xsrf)
    headers["Referer"] = edit_url
    headers["Accept"] = "application/json"

    post_res = session.post(target_url, data=payload, headers=headers, timeout=20)
    
    if post_res.status_code in [200, 302]: return True, "Sincronizado en Local y Web ✨", log_buffer
    if post_res.status_code == 422:
        try: return False, f"Error 422: {post_res.json().get('errors', '???')}", log_buffer
        except: pass
    return False, f"Error HTTP {post_res.status_code}", log_buffer

if __name__ == "__main__":
    completados = set(line.strip() for line in open("completados_img.txt", "r")) if os.path.exists("completados_img.txt") else set()
    ids_pendientes = [tid for tid in get_target_ids() if tid not in completados]
    
    print(f"🚀 Iniciando Mass Resurrector | Pendientes: {len(ids_pendientes)}")
    
    for i, tid in enumerate(ids_pendientes, 1):
        prog = int((i / len(ids_pendientes)) * 100)
        update_status("UNIT3D", "Resurrección de Imágenes", "PROCESSING", progress=prog, details=f"Resucitando ID: {tid} ({i}/{len(ids_pendientes)})")
        print(f"Procesando ID {tid}... ", end="", flush=True)
        exito, mensaje, log_buffer = procesar_total(tid)

        if "Mapping fallido" not in mensaje:
            try:
                with open("mapeo_maestro.json", "r", encoding='utf-8') as f: mapa_temp = json.load(f)
                res_temp = session.get(f"{BASE_URL}/torrents/{tid}/edit", headers=headers)
                soup_temp = BeautifulSoup(res_temp.text, 'html.parser')
                nombre_temp = soup_temp.find('input', {'name': 'name'})['value']
                carpeta_destino = mapa_temp.get(nombre_temp)
                if carpeta_destino:
                    with open(os.path.join(carpeta_destino, f"sync_TOTAL_{datetime.now().strftime('%H_%M')}.log"), "w", encoding="utf-8") as f:
                        f.write("\n".join(log_buffer))
            except: pass

        if exito:
            print(f"✨ {mensaje}")
            with open("completados_img.txt", "a") as f: f.write(f"{tid}\n")
        else:
            print(f"❌ {mensaje}")
            
        if len(ids_pendientes) > 1: time.sleep(2)

    update_status("UNIT3D", "Resurrección de Imágenes", "COMPLETED", progress=100)
