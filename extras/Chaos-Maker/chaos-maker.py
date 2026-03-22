import os
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
try:
    from core.status_manager import update_status
except ImportError:
    def update_status(*args, **kwargs): pass

def apply_chaos(target_dir="."):
    """
    Inyecta ruido binario en archivos MKV para testear validadores de integridad.
    Mantiene los headers intactos para engañar a comprobaciones superficiales.
    """
    update_status("EXTRA", "Chaos Maker", "ONLINE", details="Iniciando inyección de ruido binario...")

    # Normalizar ruta para evitar problemas de ejecución
    abs_path = os.path.abspath(target_dir)
    
    # 1. Identificar archivos MKV (ignorando mayúsculas/minúsculas)
    try:
        all_files = os.listdir(abs_path)
    except OSError as e:
        print(f"❌ Error accediendo a la carpeta: {e}")
        update_status("EXTRA", "Chaos Maker", "ERROR", details=f"Error accediendo a carpeta: {e}")
        return

    mkv_files = [f for f in all_files if f.lower().endswith('.mkv')]
    
    if not mkv_files:
        print(f"📁 Directorio: {abs_path}")
        print("❓ No se han encontrado archivos .mkv. ¿Estás en la carpeta correcta?")
        update_status("EXTRA", "Chaos Maker", "FINISHED", details="Sin archivos MKV encontrados.")
        return

    print(f"☣️  Chaos Maker: Procesando {len(mkv_files)} archivos en {abs_path}\n" + "-"*50)
    update_status("EXTRA", "Chaos Maker", "ONLINE", details=f"Corrompiendo {len(mkv_files)} archivos en {abs_path}")

    for filename in mkv_files:
        full_path = os.path.join(abs_path, filename)
        try:
            size = os.path.getsize(full_path)
            
            # Ajuste de Offset: Si el archivo es pequeño, bajamos el margen
            # Si es grande, saltamos los primeros 10MB para no romper la cabecera EBML
            if size < 20 * 1024 * 1024:
                offset = size // 4 # Rompemos en el primer cuarto
            else:
                # Saltamos los primeros 10MB (seguridad para headers)
                offset = random.randint(5, 10) * 1024 * 1024
            
            # Inyectamos 128KB de ruido (más agresivo que 64KB para asegurar que el Verifier falle)
            damage_size = 128 * 1024
            noise = os.urandom(damage_size)

            with open(full_path, "r+b") as f:
                f.seek(offset)
                f.write(noise)
                f.flush()
                os.fsync(f.fileno()) # Forzamos la escritura física en disco
            
            print(f"✅ CORRUPTO: {filename} | Offset: {offset // (1024**2)}MB")
            
        except Exception as e:
            print(f"⚠️ Error en {filename}: {e}")

    print("\n🔥 Caos completado. Los MKV tienen metadatos válidos pero streams corruptos.")
    update_status("EXTRA", "Chaos Maker", "FINISHED",
                  details=f"Proceso completado. {len(mkv_files)} archivos procesados en {abs_path}")

if __name__ == "__main__":
    # Permite pasar la ruta como argumento: python3 chaos-maker.py /ruta/videos
    path = sys.argv[1] if len(sys.argv) > 1 else "."
    apply_chaos(path)
