import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from singularity_config import GOD_PHRASES
from core.status_manager import update_status

import random
import threading
import itertools
import platform
import subprocess
import time
from datetime import datetime

# --- TROLLING SUBSYSTEM INJECTION ---
if GOD_PHRASES:
    import builtins
    if not hasattr(builtins, 'original_print'):
        builtins.original_print = builtins.print

    def troll_print(*args, **kwargs):
        if random.random() < 0.01: # 1% de probabilidad
            phrase = random.choice(GOD_PHRASES)
            builtins.original_print(f"\033[95m« {phrase} »\033[0m")
        builtins.original_print(*args, **kwargs)

    print = troll_print
# ------------------------------------

# --- CONFIGURACIÓN DE RUTAS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BIN_DIR = os.path.join(BASE_DIR, 'bin')
MODULES_DIR = os.path.join(BASE_DIR, 'modules')

# Añadimos modules al path
sys.path.append(MODULES_DIR)

# --- COLORES ---
C_CYAN = "\033[96m"
C_GREEN = "\033[92m"
C_YELLOW = "\033[93m"
C_RED = "\033[91m"
C_MAGENTA = "\033[95m"
C_BOLD = "\033[1m"
C_RESET = "\033[0m"

BANNER = f"""{C_CYAN}

   _____   ____  __.____   ____                     __  .__    .__                
  /     \ |    |/ _|\   \ /   /___________ ___.__._/  |_|  |__ |__| ____    ____  
 /  \ /  \|      <   \   Y   // __ \_  __ <   |  |\   __\  |  \|  |/    \  / ___\ 
/    Y    \    |  \   \     /\  ___/|  | \/\___  | |  | |   Y  \  |   |  \/ /_/  >
\____|__  /____|__ \   \___/  \___  >__|   / ____| |__| |___|  /__|___|  /\___  / 
        \/        \/              \/       \/                \/        \//_____/     

   --- GET YOUR SHIT TOGETHER, WHICH MEANS, FIX AND PASS TO MKV --- {C_RESET}

"""

def limpiar_pantalla():
    os.system('cls' if os.name == 'nt' else 'clear')

def configurar_entorno():
    """Inyecta binarios en el PATH y librerías en LD_LIBRARY_PATH."""
    sistema = platform.system()
    path_binario = ""
    if sistema == "Windows":
        path_binario = os.path.join(BIN_DIR, 'win')
    elif sistema == "Linux":
        path_binario = os.path.join(BIN_DIR, 'linux')
        if not os.path.exists(path_binario): path_binario = BIN_DIR 

    if path_binario and os.path.exists(path_binario):
        os.environ["PATH"] += os.pathsep + path_binario
        
        # En Linux, también configurar LD_LIBRARY_PATH para que los binarios
        # encuentren sus librerías .so (especialmente importantes para ffmpeg, mkvtoolnix)
        if sistema == "Linux":
            ld_lib_path = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = path_binario + (os.pathsep + ld_lib_path if ld_lib_path else "")
            subprocess.run(f"chmod +x {path_binario}/* 2>/dev/null", shell=True)
    return sistema

def scan_files(folder, extensions):
    """Escáner recursivo para encontrar archivos por extensión."""
    found = []
    for root, _, files in os.walk(folder):
        for f in files:
            if f.lower().endswith(tuple(extensions)):
                found.append(os.path.join(root, f))
    return found

def typewriter(text, delay=0.01):
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()

class FakeProgress(threading.Thread):
    def __init__(self, task):
        super().__init__()
        self.task = task
        self._stop_event = threading.Event()
    def run(self):
        for c in itertools.cycle(['|', '/', '-', '\\']):
            if self._stop_event.is_set(): break
            sys.stdout.write(f"\r   ⏳ {self.task} {c}")
            sys.stdout.flush()
            time.sleep(0.1)
    def stop(self):
        self._stop_event.set()
        sys.stdout.write("\r" + " "*50 + "\r")

def main():
    sistema = configurar_entorno()
    
    while True:
        limpiar_pantalla()
        print(BANNER)
        print(f"   🖥️  Sistema: {sistema}")
        
        print(f"\n   {C_YELLOW}--- HERRAMIENTAS INDIVIDUALES ---{C_RESET}")
        print("   [1] ⚖️  AUDITORÍA DE CAMPO (Recursivo + Informe de Bajas)")
        print("   [2] 🚑 Rescatar MKVs Rotos (Lista/Ruta)")
        print("   [3] 🎞️  Convertir Legacy (AVI/MP4 -> MKV)")
        print("   [4] 📦 Extraer ISOs (MakeMKV)")
        
        print(f"\n   {C_RED}--- ZONA PELIGROSA ---{C_RESET}")
        print(f"   [5] ⚡ {C_RED}GOD MODE (Extracción + Conversión + Rescate Desatendido){C_RESET}")
        print(f"   [6] 🌸 {C_MAGENTA}GODDESS MODE (Fast Scan: Check Estructural sin Decodificación){C_RESET}")
        
        print("\n   [0] 🚪 SALIR")
        
        opcion = input(f"\n   {C_GREEN}👉 Selecciona: {C_RESET}")

        try:
            if opcion == "0":
                sys.exit()

            elif opcion == "1":
                from modules import verifier
                v = verifier.Verifier()
                
                path_target = input("\n📂 Carpeta o Punto de Montaje a auditar: ").strip().replace("'","").replace('"','')
                if not os.path.exists(path_target):
                    print("❌ La ruta no existe.")
                    time.sleep(2)
                    continue

                # Preparar Informe de Bajas
                fecha_str = datetime.now().strftime("%d-%m-%y")
                archivo_bajas = os.path.join(BASE_DIR, "logs", f"videos-rotos-{fecha_str}.txt")
                os.makedirs(os.path.join(BASE_DIR, "logs"), exist_ok=True)

                print(f"\n🔍 {C_CYAN}Iniciando inventario...{C_RESET}")
                archivos = scan_files(path_target, ['.mkv', '.avi', '.mp4', '.mov', '.wmv'])
                total = len(archivos)
                
                print(f"📊 {total} archivos detectados. Iniciando escaneo de integridad...")
                print(f"📄 Informe de bajas: {archivo_bajas}\n")

                rotos = 0
                sanos = 0
                spam = 0

                for i, f in enumerate(archivos):
                    prog = int((i / total) * 100)
                    print(f"[{i+1}/{total}] {os.path.basename(f)[:50]}...", end="\r")
                    update_status("MKVERYTHING", "Auditoría", "PROCESSING", progress=prog, details=f"Escaneando: {os.path.basename(f)}")
                    
                    # Chequeo de Salud (El test real de FFmpeg)
                    es_sano = v.check_health(f)
                    # Chequeo de Spam
                    spam_info = v.audit_file_metadata(f)

                    if not es_sano:
                        rotos += 1
                        with open(archivo_bajas, "a", encoding="utf-8") as out:
                            out.write(f + "\n")
                    else:
                        sanos += 1
                    
                    if not spam_info['clean']:
                        spam += 1

                print(f"\n\n{C_YELLOW}--- RESUMEN DE AUDITORÍA ---{C_RESET}")
                print(f"✅ Sanos: {sanos}")
                print(f"❌ Rotos: {C_RED}{rotos}{C_RESET}")
                print(f"🏷️  Spam:  {spam}")
                print(f"----------------------------")
                update_status("MKVERYTHING", "Auditoría", "COMPLETED", progress=100, details=f"Sanos: {sanos}, Rotos: {rotos}")
                
                if rotos > 0:
                    print(f"\n📢 Se ha generado la lista de bajas en: {C_CYAN}{archivo_bajas}{C_RESET}")
                    lanzar = input(f"\n🚑 ¿Deseas enviar los {rotos} archivos al Rescatador ahora? (s/n): ")
                    if lanzar.lower() == 's':
                        from modules import universal_rescuer
                        rescuer = universal_rescuer.UniversalRescuer()
                        rescuer.procesar_lista(archivo_bajas, modo_estricto=True)
                else:
                    print(f"\n{C_GREEN}💎 Librería impecable. No se han detectado errores.{C_RESET}")
                
                input("\n✅ Pulsa Enter para volver...")
                continue

            elif opcion == "2":
                from modules import universal_rescuer
                print("\n📂 Arrastra Video, Carpeta o TXT (Solo se procesarán MKVs ROTOS):")
                path = input("👉 Ruta: ").strip().replace("'","").replace('"','')
                update_status("MKVERYTHING", "Rescate MKV", "PROCESSING", details=f"Analizando: {os.path.basename(path)}")
                rescuer = universal_rescuer.UniversalRescuer()
                rescuer.procesar_lista(path, modo_estricto=True)
                update_status("MKVERYTHING", "Rescate MKV", "COMPLETED")
                input("\n✅ Pulsa Enter para volver...")
                continue

            elif opcion == "3":
                from modules import universal_rescuer
                folder = input("\n📂 Carpeta a escanear (Recursiva): ").strip().replace("'","").replace('"','')
                legacy_files = scan_files(folder, ['.avi', '.mp4', '.m4v', '.divx', '.wmv', '.mov'])
                
                if legacy_files:
                    print(f"\n🦕 Encontrados {len(legacy_files)} archivos antiguos.")
                    confirm = input("¿Convertirlos a MKV H.264 Verificados? (s/n): ")
                    if confirm.lower() == 's':
                        update_status("MKVERYTHING", "Conversión Legacy", "PROCESSING", details=f"Encontrados: {len(legacy_files)} archivos")
                        rescuer = universal_rescuer.UniversalRescuer()
                        rescuer.procesar_lista(legacy_files, modo_estricto=False)
                        update_status("MKVERYTHING", "Conversión Legacy", "COMPLETED")
                input("\n✅ Pulsa Enter para volver...")
                continue

            elif opcion == "4":
                from modules import extract
                in_path = input("\n📂 Carpeta o ISO Origen: ").strip().replace("'","").replace('"','')
                out_path = input("📂 Carpeta Destino (Enter para misma): ").strip().replace("'","").replace('"','')
                if not out_path: out_path = in_path if os.path.isdir(in_path) else os.path.dirname(in_path)
                
                update_status("MKVERYTHING", "Extracción ISO", "PROCESSING", details=f"Origen: {os.path.basename(in_path)}")
                ext = extract.IsoExtractor()
                if os.path.isfile(in_path):
                    ext.extraer_iso(in_path, out_path)
                elif os.path.isdir(in_path):
                    isos = scan_files(in_path, ['.iso'])
                    print(f"   💿 Encontradas {len(isos)} ISOs.")
                    for i, iso in enumerate(isos): 
                        prog = int((i / len(isos)) * 100)
                        update_status("MKVERYTHING", "Extracción ISO", "PROCESSING", progress=prog, details=f"Extrayendo: {os.path.basename(iso)}")
                        ext.extraer_iso(iso, out_path)
                
                update_status("MKVERYTHING", "Extracción ISO", "COMPLETED", progress=100)
                input("\n✅ Pulsa Enter para volver...")
                continue

            elif opcion in ["5", "6"]:
                from modules import extract, universal_rescuer, verifier
                from datetime import datetime
                
                is_goddess = (opcion == "6")
                COLOR_MODE = C_MAGENTA if is_goddess else C_RED
                MODE_NAME = "GODDESS MODE" if is_goddess else "GODS MODE"
                PURGE_TXT = "--- THE FAST PURGE (GODDESS) IS READY ---" if is_goddess else "--- THE PURGE HAS BEGUN ---"

                limpiar_pantalla()
                
                # --- BANNER SELECTION ---
                if is_goddess:
                    BANNER_STR = f"""{COLOR_MODE}{C_BOLD}
 ██████   ██████  ██████  ██████  ███████  ██████  ██████      ███    ███  ██████  ██████  ███████
██       ██    ██ ██   ██ ██   ██ ██      ██      ██          ████  ████ ██    ██ ██    ██ ██     
██   ███ ██    ██ ██   ██ ██   ██ █████    ██████  ██████     ██ ████ ██ ██    ██ ██    ██ █████  
██    ██ ██    ██ ██   ██ ██   ██ ██            ██      ██    ██  ██  ██ ██    ██ ██    ██ ██     
 ██████   ██████  ██████  ██████  ███████  ██████  ██████     ██      ██  ██████  ██████  ███████
                    {C_RESET}"""
                else:
                    BANNER_STR = f"""{COLOR_MODE}{C_BOLD}
 ██████   ██████  █████   ██████      ███    ███  ██████  ██████  ███████
██       ██    ██ ██   ██ ██          ████  ████ ██    ██ ██    ██ ██     
██   ███ ██    ██ ██   ██  ██████     ██ ████ ██ ██    ██ ██    ██ █████  
██    ██ ██    ██ ██   ██       ██    ██  ██  ██ ██    ██ ██    ██ ██     
 ██████   ██████  ██████   ██████     ██      ██  ██████  ██████  ███████
                    {C_RESET}"""

                print(BANNER_STR)
                print(f"        {COLOR_MODE}{PURGE_TXT}{C_RESET}")

                root_path = input(f"\n{C_BOLD}📂 Ruta Raíz para el escaneo:{C_RESET} ").strip().replace("'","").replace('"','')
                out_iso_path = input(f"{C_BOLD}📂 Salida ISOs (Enter = origen):{C_RESET} ").strip().replace("'","").replace('"','')
                if not out_iso_path: out_iso_path = root_path

                # --- FASE 1: EXTRACCIÓN DE ISOs ---
                print(f"\n{COLOR_MODE}--- FASE 1: EXTRACCIÓN DE ISOs (MakeMKV) ---{C_RESET}")
                extractor = extract.IsoExtractor()
                isos = scan_files(root_path, ['.iso'])
                if isos:
                    print(f"   💿 Encontradas {len(isos)} ISOs para procesar.")
                    for iso in isos:
                        anim = FakeProgress(f"Destripando {os.path.basename(iso)}")
                        anim.start()
                        extractor.extraer_iso(iso, out_iso_path)
                        anim.stop(); anim.join()
                        print(f"    ✅ {os.path.basename(iso)} procesada.")
                else:
                    print("   (Librería limpia de ISOs)")

                # --- FASE 2: EL PIPELINE (CONVERSIÓN + RESCATE) ---
                print(f"\n{COLOR_MODE}--- FASE 2: PIPELINE DE RESCATE ({'FAST' if is_goddess else 'FULL'}) ---{C_RESET}")
                rescuer = universal_rescuer.UniversalRescuer()
                
                # Aquí está la clave: pasamos fast_scan=is_goddess
                # Si es 6, fast_scan=True y el verifier usará el check_health rápido.
                stats = rescuer.procesar_lista(root_path, modo_estricto=True, fast_scan=is_goddess)

                print(f"\n{C_GREEN}✅ Purga finalizada.{C_RESET}")
                if stats:
                    print(f"   📊 Procesados: {stats['processed']} | Omitidos: {len(stats['skipped'])}")
                
                input(f"\n{C_YELLOW}Presiona Enter para volver...{C_RESET}")
                continue

        except Exception as e:
            print(f"❌ Error inesperado: {e}")
            input()

if __name__ == "__main__":
    main()
