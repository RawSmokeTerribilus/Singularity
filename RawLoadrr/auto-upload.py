import argparse
import subprocess
import os

parser = argparse.ArgumentParser(description="Subida masiva automática de torrents")
parser.add_argument("--list", dest="lista", default=None, metavar="RUTA", help="Ruta al fichero de lista de tareas")
parser.add_argument("--tracker", dest="tracker", default="MILNU", metavar="NOMBRE", help="Nombre del tracker a usar")
# Capturar cualquier argumento extra para pasarlo a upload.py
args, unknown_args = parser.parse_known_args()

LISTA_TAREAS = args.lista or "todo-hevc-22-02-26.txt"
TRACKER_NAME = args.tracker
SCRIPT_UPLOAD = "upload.py"

def main():
    if not os.path.exists(LISTA_TAREAS):
        print(f"❌ Error: No encuentro el archivo {LISTA_TAREAS}")
        return

    with open(LISTA_TAREAS, "r", encoding="utf-8") as f:
        # Filtramos líneas vacías y quitamos saltos de línea
        rutas = [linea.strip() for linea in f if linea.strip()]

    total = len(rutas)
    print(f"🚀 Iniciando subida masiva: {total} series en cola.\n")

    for i, ruta in enumerate(rutas, 1):
        print(f"📦 [{i}/{total}] Procesando: {ruta}")
        
        # Ejecutamos el comando tal cual lo lanzas tú
        # subprocess.run sin capturar salida para que veas los colores y logs del script original
        comando = [
            "python3", SCRIPT_UPLOAD,
            "--tracker", TRACKER_NAME,
            "--input", ruta
        ] + unknown_args # Añadimos los argumentos extra
        
        # 'palante como los de alicante': si falla, sigue con el siguiente
        subprocess.run(comando)
        
    print("\n✅ ¡Fin de la lista! Todo procesado.")

if __name__ == "__main__":
    main()
