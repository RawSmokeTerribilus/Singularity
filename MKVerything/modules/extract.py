import os
import subprocess
import shutil
import time
import argparse
from .verifier import Verifier

_MKVE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LOGS_DIR = os.path.join(_MKVE_ROOT, "logs")


class IsoExtractor:
    def __init__(self):
        self.verifier = Verifier()
        os.makedirs(_LOGS_DIR, exist_ok=True)
        self.log_file = os.path.join(_LOGS_DIR, "extraction_process.log")

    def _log(self, msg):
        print(msg)
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")

    def extraer_iso(self, ruta_iso, carpeta_destino):
        """
        Usa makemkvcon para extraer TODOS los títulos de una ISO a una carpeta temporal.
        Luego filtra y renombra.
        """
        nombre_iso = os.path.splitext(os.path.basename(ruta_iso))[0]
        temp_dir = os.path.join(carpeta_destino, "TEMP_EXTRACT", nombre_iso)
        os.makedirs(temp_dir, exist_ok=True)

        print(f"💿 Analizando ISO: {nombre_iso}...")
        
        # 1. EJECUTAR MAKEMKV (Extraer todo: 'all')
        # makemkvcon mkv iso:<ruta> all <destino>
        cmd = ["makemkvcon", "mkv", f"iso:{ruta_iso}", "all", temp_dir]
        
        print("   ⏳ Extrayendo contenido (esto puede tardar)...")
        try:
            # Ejecutamos y esperamos. MakeMKV es verboso, capturamos output.
            proc = subprocess.run(cmd, capture_output=True, text=True)
            if proc.returncode != 0:
                self._log(f"❌ Error MakeMKV en {nombre_iso}: {proc.stderr}")
                return False
        except FileNotFoundError:
            self._log("❌ Error: No se encuentra 'makemkvcon'. ¿Has lanzado desde launcher.py?")
            return False

        # 2. PROCESAR RESULTADOS
        archivos_extraidos = [f for f in os.listdir(temp_dir) if f.endswith(".mkv")]
        if not archivos_extraidos:
            self._log(f"⚠️ Alerta: MakeMKV terminó pero no generó MKVs para {nombre_iso}")
            shutil.rmtree(temp_dir)
            return False

        print(f"   📂 Se han extraído {len(archivos_extraidos)} archivos.")

        # 3. SELECCIÓN DEL MAIN FEATURE (El más grande)
        # En el futuro podemos usar lógica de series, por ahora priorizamos Peli/Episodio largo
        main_mkv = max([os.path.join(temp_dir, f) for f in archivos_extraidos], key=os.path.getsize)
        
        print(f"   🎥 Archivo principal candidato: {os.path.basename(main_mkv)}")

        # 4. VERIFICACIÓN (ISO vs MKV)
        print("   ⚖️  Verificando integridad (Pistas Audio/Subs)...")
        veredicto = self.verifier.check_iso_extraction(ruta_iso, main_mkv)

        if veredicto["valid"]:
            # Mover a destino final
            destino_final_archivo = os.path.join(carpeta_destino, f"{nombre_iso}.mkv")
            shutil.move(main_mkv, destino_final_archivo)
            self._log(f"✅ ÉXITO: {nombre_iso}.mkv creado.")
            
            # Limpieza
            shutil.rmtree(os.path.dirname(temp_dir)) # Borrar TEMP_EXTRACT
            
            # ¿Borrar ISO original? (Solo si estás muy seguro, aquí lo dejo comentado por seguridad)
            # os.remove(ruta_iso) 
            return True
        else:
            self._log(f"🛑 Error de Verificación en {nombre_iso}: {veredicto['errors']}")
            # No borramos nada para que puedas revisar la extracción manual en TEMP
            print(f"   ⚠️ Los archivos extraídos se han dejado en: {temp_dir} para revisión.")
            return False

# Wrapper para llamar desde Launcher
def main():
    parser = argparse.ArgumentParser(description="Extractor de ISOs MKVerything")
    parser.add_argument("-i", "--input", required=True, help="Carpeta o archivo ISO de entrada")
    parser.add_argument("-o", "--output", required=True, help="Carpeta de destino")
    args = parser.parse_args()

    extractor = IsoExtractor()

    if os.path.isfile(args.input):
        extractor.extraer_iso(args.input, args.output)
    elif os.path.isdir(args.input):
        for f in os.listdir(args.input):
            if f.lower().endswith(".iso"):
                extractor.extraer_iso(os.path.join(args.input, f), args.output)

if __name__ == "__main__":
    main()
