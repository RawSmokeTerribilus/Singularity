import os
import subprocess
import sys
import shlex

sys.path.insert(0, '/app/MKVerything')
from modules.hardware_agent import HardwareAgent

def run_mass_transcode(list_path):
    agent = HardwareAgent()
    raw_hw_args = agent.get_transcode_args()
    hw_args_list = shlex.split(raw_hw_args)
    
    print(f"🚀 RECON: Motor {agent.device.upper()} listo para la batalla.")

    with open(list_path, 'r') as f:
        rutas = [line.strip() for line in f if line.strip()]

    for i, ruta in enumerate(rutas):
        if not os.path.exists(ruta):
            print(f"❌ [SKIP] No encontrada: {ruta}")
            continue

        print(f"🎬 [{i+1}/{len(rutas)}] Iniciando: {os.path.basename(ruta)}")
        output = ruta.replace('.mkv', '_provisional.mkv')
        
        # --- INTENTO 1: AMD VA-API (La Gloria) ---
        cmd_gpu = [
            'ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
            '-vaapi_device', '/dev/dri/renderD128',
            '-i', ruta,
            *hw_args_list,
            '-c:a', 'aac', '-b:a', '128k',
            '-map', '0:v:0', '-map', '0:a?', '-map', '0:s?',
            '-ignore_unknown', '-map_metadata', '-1',
            '-max_interleave_delta', '0',
            output
        ]

        try:
            print(f"   ⚡ Intentando aceleración AMD...")
            subprocess.run(cmd_gpu, check=True)
            os.replace(output, ruta)
            print(f"   ✅ Éxito con AMD.")
        except subprocess.CalledProcessError:
            print(f"   ⚠️ La AMD ha gripado con la pudrición. Saltando a CPU...")
            if os.path.exists(output): os.remove(output)
            
            # --- INTENTO 2: CPU libx264 (El Mazo) ---
            cmd_cpu = [
                'ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
                '-i', ruta,
                '-c:v', 'libx264', '-preset', 'fast', '-crf', '22',
                '-c:a', 'aac', '-b:a', '128k',
                '-map', '0:v:0', '-map', '0:a?', '-map_metadata', '-1',
                '-fflags', '+genpts+igndts+discardcorrupt',
                output
            ]
            
            try:
                subprocess.run(cmd_cpu, check=True)
                os.replace(output, ruta)
                print(f"   🚜 Rescatado por CPU con éxito.")
            except subprocess.CalledProcessError:
                print(f"   💀 FALLO TOTAL: Ni la CPU ha podido con este cadáver.")
                if os.path.exists(output): os.remove(output)

if __name__ == "__main__":
    run_mass_transcode('/app/logs/rutas_host.txt')
