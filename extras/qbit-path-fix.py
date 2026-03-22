import requests
import os
import re

BASE_URL = "http://localhost:8888"
AUTH = ("YOUR_USER", "YOUR_PASS")

def get_all_torrents():
    return requests.get(f"{BASE_URL}/api/v2/torrents/info", auth=AUTH).json()

def run_fix():
    all_t = get_all_torrents()
    missing = [t for t in all_t if t['state'] == 'missingFiles']
    
    # RECON: Aprender rutas de tus discos basándonos en los 4000 que SÍ funcionan
    known_roots = set()
    for t in all_t:
        path_parts = t['save_path'].split('/')
        if len(path_parts) > 5: # /run/media/rawserver/DISCO/CATEGORIA/
            known_roots.add("/".join(path_parts[:6]))
    
    print(f"--- Escaneando en {len(known_roots)} puntos de montaje ---")
    print(f"--- Intentando liquidar los últimos {len(missing)} rebeldes ---\n")

    for t in missing:
        old_path = t['save_path'].rstrip('/')
        # Extraer ID (el número largo del path actual)
        ids = re.findall(r'\d{5,8}', old_path)
        if not ids: 
            # Si no hay ID en el path, lo buscamos en el nombre del torrent
            ids = re.findall(r'\d{5,8}', t['name'])
        
        if not ids:
            print(f"[MISS] {t['name']} no tiene ID detectable.")
            continue
            
        show_id = ids[0]
        found = False

        # Búsqueda Global en todos los discos conocidos
        for root in known_roots:
            if found: break
            if not os.path.exists(root): continue
            
            try:
                candidates = os.listdir(root)
                for c in candidates:
                    if show_id in c:
                        # Hemos encontrado la carpeta de la serie en algún disco
                        # Ahora vemos si el torrent pedía una subcarpeta de temporada
                        new_base = os.path.join(root, c)
                        
                        # Si el torrent tiene nombre de temporada, buscamos si existe esa subcarpeta
                        season_match = re.search(r'(Season\s?\d+|Temporada\s?\d+)', t['name'], re.I)
                        target_path = new_base
                        
                        if season_match:
                            # Buscamos la subcarpeta de temporada dentro de la serie
                            s_name = season_match.group(1)
                            # Listar subcarpetas para un match flexible (Season 01 vs Season 1)
                            try:
                                subs = os.listdir(new_base)
                                for s in subs:
                                    if s_name.replace(" ", "") in s.replace(" ", ""):
                                        target_path = os.path.join(new_base, s)
                                        break
                            except: pass

                        print(f"[KILL] {t['name']}")
                        print(f"  ID: {show_id} | Nuevo Path: {target_path}")
                        
                        requests.post(f"{BASE_URL}/api/v2/torrents/setLocation", 
                                      auth=AUTH, 
                                      data={'hashes': t['hash'], 'location': target_path})
                        found = True
                        break
            except Exception as e:
                continue

if __name__ == "__main__":
    run_fix()
