import requests
from bs4 import BeautifulSoup
import time
import random
import os
import sys
import json
import shutil

# Add project root to path to import core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.status_manager import update_status
from config import BASE_URL, COOKIE_NAME, COOKIE_VALUE, USERNAME, CUSTOM_USER_AGENT

# Configuración de sesión
USER_UPLOADS_URL = f"{BASE_URL}/users/{USERNAME}/uploads"
RATE_LIMIT_PAUSE = 30
MAX_RATE_RETRIES = 3

session = requests.Session()
session.cookies.set(COOKIE_NAME, COOKIE_VALUE)

headers = {
    "User-Agent": CUSTOM_USER_AGENT,
}


def _guardar_estado(all_ids, titulos_mapa):
    """Volcado seguro en bind-mount Docker: escribe en .tmp, copia sobre el
    destino (preserva inodo) y elimina el temporal. Evita EBUSY (Errno 16)."""
    tmp_ids = "ids.tmp.txt"
    with open(tmp_ids, "w") as f:
        for tid in all_ids:
            f.write(f"{tid}\n")
    shutil.copy(tmp_ids, "ids.txt")
    os.remove(tmp_ids)

    tmp_json = "titulos_mapa.tmp.json"
    with open(tmp_json, "w", encoding="utf-8") as f:
        json.dump(titulos_mapa, f, ensure_ascii=False, indent=2)
    shutil.copy(tmp_json, "titulos_mapa.json")
    os.remove(tmp_json)


def scrape_my_ids():
    # --- MODO RESUME ---
    seen_ids = set()
    all_ids = []
    titulos_mapa = {}

    if os.path.exists("ids.txt"):
        with open("ids.txt", "r") as f:
            for line in f:
                tid = line.strip()
                if tid:
                    seen_ids.add(tid)
                    all_ids.append(tid)
        print(f"♻️  Resume: {len(seen_ids)} IDs previos cargados.")

    if os.path.exists("titulos_mapa.json"):
        try:
            with open("titulos_mapa.json", "r", encoding="utf-8") as f:
                raw = f.read().strip()
            if raw:
                titulos_mapa = json.loads(raw)
                print(f"♻️  Resume: {len(titulos_mapa)} títulos previos cargados.")
            else:
                print(f"⚠️  titulos_mapa.json vacío o corrupto, arrancando desde cero.")
        except json.JSONDecodeError as e:
            print(f"⚠️  titulos_mapa.json ilegible ({e}), arrancando desde cero.")

    print(f"🕵️ Iniciando cosecha de IDs desde {USER_UPLOADS_URL}...")

    page = 1
    while True:
        url = f"{USER_UPLOADS_URL}?page={page}"
        print(f"📄 Procesando página {page}...", end="\r")
        update_status("UNIT3D", "Scraping IDs", "PROCESSING", details=f"Página {page}")

        # --- FETCH CON CONTROL DE BOMBARDEO ---
        res = None
        rate_retries = 0
        while rate_retries < MAX_RATE_RETRIES:
            try:
                res = session.get(url, headers=headers, timeout=10)
            except Exception as e:
                print(f"\n❌ Error de red en página {page}: {e}")
                sys.exit(1)

            if res.status_code in (429, 403):
                rate_retries += 1
                print(f"\n🛑 [{res.status_code}] Rate limit en pág {page}. "
                      f"Pausa {RATE_LIMIT_PAUSE}s... (intento {rate_retries}/{MAX_RATE_RETRIES})")
                time.sleep(RATE_LIMIT_PAUSE)
            else:
                break

        if rate_retries >= MAX_RATE_RETRIES:
            print(f"\n💀 {MAX_RATE_RETRIES} fallos consecutivos por rate limit. Abortando.")
            sys.exit(1)

        if res.status_code != 200:
            print(f"\n⚠️ Fin de las páginas o error en pág {page} (Status {res.status_code})")
            break

        soup = BeautifulSoup(res.text, 'html.parser')
        page_ids = []    # IDs nuevos (no vistos antes)
        page_total = 0   # todos los torrents encontrados en el DOM de esta página

        for link in soup.find_all('a', href=True):
            href = link['href']
            if "/torrents/" in href:
                parts = href.rstrip('/').split('/')
                last_part = parts[-1]
                if last_part.isdigit():
                    page_total += 1
                    if last_part not in seen_ids:
                        titulo = link.get_text(strip=True)
                        seen_ids.add(last_part)
                        all_ids.append(last_part)
                        page_ids.append(last_part)
                        # Solo guardar títulos con texto real (evitar links vacíos o iconos)
                        if titulo and len(titulo) > 3:
                            titulos_mapa[last_part] = titulo

        # --- CONDICIÓN DE SALIDA: página realmente vacía en el DOM ---
        if page_total == 0:
            print(f"\nℹ️ Página {page} sin torrents en el DOM. Fin del catálogo.")
            break

        if page_ids:
            print(f"\n   ✚ {len(page_ids)} nuevos IDs en pág {page} (DOM: {page_total} torrents)")
            _guardar_estado(all_ids, titulos_mapa)
        else:
            print(f"\n   ⏭️  Pág {page}: {page_total} torrents ya conocidos, saltando...")

        page += 1
        time.sleep(random.uniform(1.5, 3.5))

    # Volcado final (garantiza estado coherente al salir)
    _guardar_estado(all_ids, titulos_mapa)

    print(f"\n\n✅ ¡Cosecha completada!")
    print(f"📦 Total de IDs únicos encontrados: {len(all_ids)}")
    print(f"🏷️  Títulos mapeados: {len(titulos_mapa)}")
    update_status("UNIT3D", "Scraping IDs", "COMPLETED", progress=100, details=f"Total: {len(all_ids)} IDs")

    print(f"💾 Lista guardada en 'ids.txt' y 'titulos_mapa.json'.")

if __name__ == "__main__":
    scrape_my_ids()
