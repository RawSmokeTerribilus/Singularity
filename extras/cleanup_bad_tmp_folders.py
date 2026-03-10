import os
import shutil
from pathlib import Path

# Configuración
# Obtener la raíz del proyecto (padre de 'extras')
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Rutas relativas a la raíz del proyecto
TMP_DIR = PROJECT_ROOT / "RawLoadrr" / "tmp"
LEFTOVER_FILE = PROJECT_ROOT / "leftover_pixhost_dirs.txt"
CLEAN_VS_BAD_FILE = PROJECT_ROOT / "clean_vs_bad_descriptions.txt"

def cleanup_folder(folder_path):
    folder = Path(folder_path)
    if not folder.exists():
        return False, "Folder not found"

    # Archivos a preservar
    # BASE.torrent, *.png (imágenes), MediaInfo.json, MEDIAINFO.txt, MEDIAINFO_CLEANPATH.txt
    # (El usuario mencionó dejar torrent, imágenes y quizás mediainfo)
    
    files_to_keep_patterns = ["BASE.torrent", "*.png", "MediaInfo.json", "MEDIAINFO.txt", "MEDIAINFO_CLEANPATH.txt"]
    
    files_in_folder = list(folder.iterdir())
    deleted_count = 0
    kept_files = []

    for item in files_in_folder:
        if item.is_dir():
            # No esperamos subdirectorios, pero si hay, los borramos si no son esenciales
            shutil.rmtree(item)
            deleted_count += 1
            continue

        keep = False
        for pattern in files_to_keep_patterns:
            if item.match(pattern):
                keep = True
                break
        
        if not keep:
            try:
                item.unlink()
                deleted_count += 1
            except Exception as e:
                print(f"Error deleting {item}: {e}")
        else:
            kept_files.append(item.name)

    return True, f"Deleted {deleted_count} files. Kept: {', '.join(kept_files)}"

def main():
    if not os.path.exists(CLEAN_VS_BAD_FILE):
        print(f"Error: {CLEAN_VS_BAD_FILE} not found. Run the categorization script first.")
        return

    bad_folders = []
    with open(CLEAN_VS_BAD_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith("[BAD]"):
                bad_folders.append(line.replace("[BAD] ", "").strip())

    print(f"Starting cleanup for {len(bad_folders)} folders with bad links...")
    
    success_count = 0
    fail_count = 0

    for folder in bad_folders:
        success, message = cleanup_folder(folder)
        if success:
            print(f"[CLEANED] {os.path.basename(folder)}: {message}")
            success_count += 1
        else:
            print(f"[ERROR] {os.path.basename(folder)}: {message}")
            fail_count += 1

    print(f"\nSummary:")
    print(f"Successfully cleaned: {success_count}")
    print(f"Failed: {fail_count}")
    print("\nNote: meta.json and [MILNU]* files have been removed. BASE.torrent and images preserved.")

if __name__ == "__main__":
    main()
