import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from singularity_config import GOD_PHRASES

import random
import threading
import itertools
import platform
import subprocess
import time
from datetime import datetime

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
        
        print("\n   [0] 🚪 SALIR")
        
        opcion = input(f"\n   {C_GREEN}👉 Selecciona: {C_RESET}")

        try:
            if opcion == "4":
                from modules import extract
                in_path = input("\n📂 Carpeta o ISO Origen: ").strip().replace("'","").replace('"','')
                out_path = input("📂 Carpeta Destino (Enter para misma): ").strip().replace("'","").replace('"','')
                if not out_path: out_path = in_path if os.path.isdir(in_path) else os.path.dirname(in_path)
                
                ext = extract.IsoExtractor()
                if os.path.isfile(in_path):
                    ext.extraer_iso(in_path, out_path)
                elif os.path.isdir(in_path):
                    isos = scan_files(in_path, ['.iso'])
                    print(f"   💿 Encontradas {len(isos)} ISOs.")
                    for iso in isos: ext.extraer_iso(iso, out_path)
                input("\n✅ Pulsa Enter para volver...")

            elif opcion == "2":
                from modules import universal_rescuer
                print("\n📂 Arrastra Video, Carpeta o TXT (Solo se procesarán MKVs ROTOS):")
                path = input("👉 Ruta: ").strip().replace("'","").replace('"','')
                rescuer = universal_rescuer.UniversalRescuer()
                rescuer.procesar_lista(path, modo_estricto=True)
                input("\n✅ Pulsa Enter para volver...")

            # =================================================================
            # OPCIÓN 1: AUDITORÍA DE CAMPO (EL NUEVO MOTOR)
            # =================================================================
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
                    print(f"[{i+1}/{total}] {os.path.basename(f)[:50]}...", end="\r")
                    
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

            elif opcion == "3":
                from modules import universal_rescuer
                folder = input("\n📂 Carpeta a escanear (Recursiva): ").strip().replace("'","").replace('"','')
                legacy_files = scan_files(folder, ['.avi', '.mp4', '.m4v', '.divx', '.wmv', '.mov'])
                
                if legacy_files:
                    print(f"\n🦕 Encontrados {len(legacy_files)} archivos antiguos.")
                    confirm = input("¿Convertirlos a MKV H.264 Verificados? (s/n): ")
                    if confirm.lower() == 's':
                        rescuer = universal_rescuer.UniversalRescuer()
                        rescuer.procesar_lista(legacy_files, modo_estricto=False)
                input("\n✅ Pulsa Enter para volver...")

            elif opcion == "5":
                from modules import extract, universal_rescuer, verifier
                
                limpiar_pantalla()
                # Aquí puedes pegar tu diseño de BANNER agresivo
                # --- BANNER CUSTOM (Aquí va tu diseño agresivo) ---
                GOD_BANNER = f"""{C_RED}{C_BOLD}
 ██████   ██████  █████       ███    ███  ██████  ██████  ███████ 
██       ██    ██ ██   ██     ████  ████ ██    ██ ██   ██ ██      
██   ███ ██    ██ ██   ██     ██ ████ ██ ██    ██ ██   ██ █████   
██    ██ ██    ██ ██   ██     ██  ██  ██ ██    ██ ██   ██ ██      
 ██████   ██████  ██████      ██      ██  ██████  ██████  ███████ 
                                                                  
     --- THE PURGE HAS BEGUN - DON'T TOUCH THE TERMINAL --- {C_RESET}
"""
                print(GOD_BANNER)

                print(f"{C_RED}{C_BOLD}⚡ MODO DIOS ACTIVADO - PREPARANDO PURGA ⚡{C_RESET}")
                typewriter(f"{C_RED}ADVERTENCIA: Iniciando juicio final. No toques nada.{C_RESET}")
                
                root_path = input(f"\n{C_BOLD}📂 Ruta Raíz para el escaneo:{C_RESET} ").strip().replace("'","").replace('"','')
                out_iso_path = input("📂 Salida ISOs (Enter = origen): ").strip().replace("'","").replace('"','')
                if not out_iso_path: out_iso_path = root_path

                rescuer = universal_rescuer.UniversalRescuer()
                v = verifier.Verifier()
                fecha_str = datetime.now().strftime("%d-%m-%y")
                os.makedirs(os.path.join(BASE_DIR, "docs"), exist_ok=True)
                audit_txt = os.path.join(BASE_DIR, "docs", f"god-audit-{fecha_str}.txt")

                # --- FASE 1: AUDITORÍA INICIAL ---
                print(f"\n{C_CYAN}--- FASE 1: AUDITORÍA INICIAL ---{C_RESET}")
                archivos = scan_files(root_path, ['.mkv', '.avi', '.mp4', '.mov', '.wmv'])
                total = len(archivos)
                print(f"📊 {total} archivos detectados. Iniciando escaneo de integridad...")
                print(f"📄 Informe de bajas: {audit_txt}\n")
                rotos = 0
                sanos = 0
                spam = 0
                for i, f in enumerate(archivos):
                    print(f"[{i+1}/{total}] {os.path.basename(f)[:50]}...", end="\r")
                    es_sano = v.check_health(f)
                    spam_info = v.audit_file_metadata(f)
                    if not es_sano:
                        rotos += 1
                        with open(audit_txt, "a", encoding="utf-8") as out:
                            out.write(f + "\n")
                    else:
                        sanos += 1
                    if not spam_info['clean']:
                        spam += 1
                print(f"\n\n{C_YELLOW}--- RESUMEN AUDITORÍA INICIAL ---{C_RESET}")
                print(f"✅ Sanos: {sanos}")
                print(f"❌ Rotos: {C_RED}{rotos}{C_RESET}")
                print(f"🏷️  Spam:  {spam}")

                # --- FASE 2: RESCATE ---
                print(f"\n{C_CYAN}--- FASE 2: RESCATE DE MKVs ROTOS ---{C_RESET}")
                if rotos > 0:
                    rescuer.procesar_lista(audit_txt, modo_estricto=True)
                else:
                    print("   (No hay archivos rotos que rescatar)")

                # --- FASE 3: LEGACY TRANSCODE ---
                print(f"\n{C_CYAN}--- FASE 3: CONVERSIÓN LEGACY ---{C_RESET}")
                legacy_files = scan_files(root_path, ['.avi', '.mp4', '.m4v', '.divx', '.wmv', '.mov'])
                if legacy_files:
                    print(f"🦕 Encontrados {len(legacy_files)} archivos legacy.")
                    rescuer.procesar_lista(legacy_files, modo_estricto=False)
                else:
                    print("   (No hay archivos legacy que convertir)")

                # --- FASE 4: EXTRACCIÓN DE ISOs ---
                print(f"\n{C_CYAN}--- FASE 4: EXTRACCIÓN DE ISOs ---{C_RESET}")
                isos = scan_files(root_path, ['.iso'])
                if isos:
                    ext = extract.IsoExtractor()
                    for iso in isos:
                        anim = FakeProgress(f"Destripando {os.path.basename(iso)}")
                        anim.start()
                        ext.extraer_iso(iso, out_iso_path)
                        anim.stop(); anim.join()
                        print(f"    ✅ ISO Procesada.")
                else:
                    print("   (Librería limpia de ISOs)")

                # --- FASE 5: AUDITORÍA FINAL ---
                print(f"\n{C_CYAN}--- FASE 5: AUDITORÍA FINAL ---{C_RESET}")
                os.makedirs(os.path.join(BASE_DIR, "docs"), exist_ok=True)
                audit_final_txt = os.path.join(BASE_DIR, "docs", f"god-audit-final-{fecha_str}.txt")
                archivos_final = scan_files(root_path, ['.mkv', '.avi', '.mp4', '.mov', '.wmv'])
                total_final = len(archivos_final)
                print(f"📊 {total_final} archivos detectados. Verificando estado final...")
                print(f"📄 Informe final: {audit_final_txt}\n")
                rotos_final = 0
                sanos_final = 0
                spam_final = 0
                for i, f in enumerate(archivos_final):
                    print(f"[{i+1}/{total_final}] {os.path.basename(f)[:50]}...", end="\r")
                    es_sano = v.check_health(f)
                    spam_info = v.audit_file_metadata(f)
                    if not es_sano:
                        rotos_final += 1
                        with open(audit_final_txt, "a", encoding="utf-8") as out:
                            out.write(f + "\n")
                    else:
                        sanos_final += 1
                    if not spam_info['clean']:
                        spam_final += 1
                print(f"\n\n{C_YELLOW}--- RESUMEN AUDITORÍA FINAL ---{C_RESET}")
                print(f"✅ Sanos: {sanos_final}")
                print(f"❌ Rotos: {C_RED}{rotos_final}{C_RESET}")
                print(f"🏷️  Spam:  {spam_final}")
                print(f"\n📄 Informe final guardado en: {C_CYAN}{audit_final_txt}{C_RESET}")

                # --- GENERAR LOG FINAL ---
                os.makedirs(os.path.join(BASE_DIR, 'logs'), exist_ok=True)
                log_path = os.path.join(BASE_DIR, 'logs', 'GOD_MODE_log.txt')
                report = f"""========================================
   ⚡ GOD MODE REPORT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
========================================
Sanos:  {sanos_final}
Rotos:  {rotos_final}
Spam:   {spam_final}
========================================"""
                with open(log_path, "w", encoding="utf-8") as lf:
                    lf.write(report)
                print(f"\n📄 Informe de batalla guardado en: {log_path}")

                print(f"\n{C_GREEN}✨ PURGA COMPLETADA. El mundo es un lugar mejor.{C_RESET}")
                input("\n✅ Pulsa Enter para volver a la realidad...")

            elif opcion == "0":
                sys.exit()

        except Exception as e:
            print(f"❌ Error inesperado: {e}")
            input()

if __name__ == "__main__":
    main()
