import requests
from bs4 import BeautifulSoup
import time

# --- CONFIGURACIÓN ---
BASE_URL = "https://milnueve.neklair.es"
COOKIE_NAME = "milnueve_session" 
COOKIE_VALUE = "eyJpdiI6Ik9rV21oSExwR1Vsc29zZ1MyYWJXeUE9PSIsInZhbHVlIjoiOWl4ZWlERXduVUJJR3RBQjdkcjJ5N2dXbGhpQmIxT1pOUnpmUjdNR2pVTmoxWGk1Y1N5enQwVGYrM01nZ0gzbkErWEphQmdZYzFocDN6V1V4eTkycUlVUUtRYzM0U3p2dkcrMkQ2WXNoNFp5TVpITS9nTDdzQmEzc1o4SWIrSVAiLCJtYWMiOiJiNmU3OWZjMWYxM2M1ZjAxNGY4MGM4NDU3MWZmMTRhN2UzNTdjNDc5MjljMzNmMThmZTU0YTBjZTJlODVhZGI2IiwidGFnIjoiIn0%3D"

# Configuración de páginas
USER_UPLOADS_URL = f"{BASE_URL}/users/RawSmoke/uploads"
MAX_PAGES = 80 # Ponemos 80 por si has subido más mientras tanto

session = requests.Session()
session.cookies.set(COOKIE_NAME, COOKIE_VALUE, domain="milnueve.neklair.es")
headers = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

def scrape_my_ids():
    all_ids = []
    print(f"🕵️ Iniciando cosecha de IDs desde {USER_UPLOADS_URL}...")

    for page in range(1, MAX_PAGES + 1):
        url = f"{USER_UPLOADS_URL}?page={page}"
        print(f"📄 Procesando página {page}/{MAX_PAGES}...", end="\r")
        
        try:
            res = session.get(url, headers=headers, timeout=10)
            if res.status_code != 200:
                print(f"\n⚠️ Fin de las páginas o error en pág {page} (Status {res.status_code})")
                break
            
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # Buscamos los enlaces a los torrents
            # En UNIT3D los enlaces suelen estar dentro de celdas <td> o <a> con el ID al final
            links = soup.find_all('a', href=True)
            page_ids = []
            
            for link in links:
                href = link['href']
                # Buscamos el patrón /torrents/ID
                if "/torrents/" in href:
                    parts = href.rstrip('/').split('/')
                    last_part = parts[-1]
                    if last_part.isdigit():
                        if last_part not in all_ids:
                            all_ids.append(last_part)
                            page_ids.append(last_part)
            
            if not page_ids:
                print(f"\nℹ️ No se encontraron más torrents nuevos en la página {page}. Finalizando.")
                break
                
            # Un respiro para no saturar
            time.sleep(1)

        except Exception as e:
            print(f"\n❌ Error en página {page}: {e}")
            break

    print(f"\n\n✅ ¡Cosecha completada!")
    print(f"📦 Total de IDs únicos encontrados: {len(all_ids)}")

    # Guardamos en el archivo para el siguiente script
    with open("ids.txt", "w") as f:
        for tid in all_ids:
            f.write(f"{tid}\n")
    
    print(f"💾 Lista guardada en 'ids.txt'. Ya puedes ejecutar el Auto-Pilot.")

if __name__ == "__main__":
    scrape_my_ids()
