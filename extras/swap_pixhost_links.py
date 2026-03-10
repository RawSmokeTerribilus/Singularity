import os
import json
import re
from pathlib import Path

# Configuración
# Obtener la raíz del proyecto (padre de 'extras')
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Ruta relativa a la raíz del proyecto
TMP_DIR = PROJECT_ROOT / "RawLoadrr" / "tmp"

def update_meta_json(folder_path):
    folder = Path(folder_path)
    meta_file = folder / "meta.json"
    
    if not meta_file.exists():
        return False, "meta.json not found"
        
    try:
        with open(meta_file, 'r', encoding='utf-8') as f:
            meta_data = json.load(f)
    except Exception as e:
        return False, f"Error loading meta.json: {e}"
        
    # Verificar si tiene links de pixhost
    has_pixhost = False
    if "image_list" in meta_data:
        for item in meta_data["image_list"]:
            if any("pixhost.to" in str(v) for v in item.values()):
                has_pixhost = True
                break
    
    if not has_pixhost:
        return False, "No pixhost links found"
        
    # Buscar el log de sincronización más reciente con PtScreens
    log_files = sorted(list(folder.glob("sync_*.log")), key=os.path.getmtime, reverse=True)
    if not log_files:
        return False, "No sync_*.log found"
        
    pt_screens_urls = []
    
    # Intentar encontrar URLs de PtScreens o ImgBB en el log más reciente
    for log_file in log_files:
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # Buscar patrones más flexibles:
                # [>] Subiendo a PtScreens: ... [OK] URL: (https://...)
                # [>] Subiendo a PtScreens: ... [OK] URL Directa: (https://...)
                # [>] Subiendo a ImgBB: ... [OK] URL Directa: (https://...)
                matches = re.findall(r'\[>\] Subiendo a (?:PtScreens|ImgBB):.*?\n\s+\[OK\] URL(?: Directa)?: (https?://\S+)', content)
                if matches:
                    pt_screens_urls.extend(matches)
                    break # Usar el primer log que tenga URLs
        except Exception as e:
            print(f"Error reading log {log_file}: {e}")
            
    if not pt_screens_urls:
        return False, "No PtScreens URLs found in logs"
        
    # Actualizar image_list
    updated = False
    if "image_list" in meta_data:
        # Se asume que el orden en image_list coincide con el orden de subida en el log
        for i, item in enumerate(meta_data["image_list"]):
            if i < len(pt_screens_urls):
                new_url = pt_screens_urls[i]
                # Reemplazamos todos los campos con la nueva URL (raw/img/web)
                item["web_url"] = new_url
                item["img_url"] = new_url
                item["raw_url"] = new_url
                updated = True
        
    if updated:
        # Hacer backup del original si no existe ya
        backup_file = meta_file.with_suffix(".json.bak")
        if not backup_file.exists():
            try:
                import shutil
                shutil.copy2(meta_file, backup_file)
            except Exception as e:
                return False, f"Error creating backup: {e}"
            
        # Guardar nuevo meta.json
        try:
            with open(meta_file, 'w', encoding='utf-8') as f:
                json.dump(meta_data, f, indent=4, ensure_ascii=False)
            return True, f"Updated {len(pt_screens_urls)} links"
        except Exception as e:
            return False, f"Error saving meta.json: {e}"
            
    return False, "No links updated despite finding PtScreens URLs"

def main():
    if not os.path.exists(TMP_DIR):
        print(f"Error: Directory {TMP_DIR} does not exist.")
        return

    print(f"Searching for meta.json in {TMP_DIR}...")
    
    # Obtener todas las subcarpetas
    try:
        subfolders = [os.path.join(TMP_DIR, f) for f in os.listdir(TMP_DIR) if os.path.isdir(os.path.join(TMP_DIR, f))]
    except Exception as e:
        print(f"Error listing directory: {e}")
        return
        
    success_count = 0
    fail_count = 0
    skipped_count = 0
    
    for folder in subfolders:
        try:
            success, message = update_meta_json(folder)
            if success:
                print(f"[OK] {os.path.basename(folder)}: {message}")
                success_count += 1
            elif message in ["meta.json not found", "No pixhost links found", "No sync_*.log found"]:
                skipped_count += 1
            else:
                # No PtScreens URLs found in logs es un "fail" relativo si el usuario dice que ya los subió
                print(f"[INFO] {os.path.basename(folder)}: {message}")
                fail_count += 1
        except Exception as e:
            print(f"[ERROR] {os.path.basename(folder)}: {e}")
            fail_count += 1
            
    print(f"\nSummary:")
    print(f"Success: {success_count}")
    print(f"Failed/No Log: {fail_count}")
    print(f"Skipped (No action needed): {skipped_count}")

if __name__ == "__main__":
    main()
