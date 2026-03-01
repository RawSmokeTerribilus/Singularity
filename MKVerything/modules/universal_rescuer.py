import os
import subprocess
import sys
import shutil
import time
try:
    import vapoursynth as vs
    core = vs.core
    _VS_AVAILABLE = True
except ImportError:
    _VS_AVAILABLE = False

from .verifier import Verifier

_MKVE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LOGS_DIR = os.path.join(_MKVE_ROOT, "logs")
FAST_WORK_DIR = os.path.join(_MKVE_ROOT, "TEMP_WORK_AREA")


class UniversalRescuer:
    def __init__(self):
        self.verifier = Verifier()
        os.makedirs(FAST_WORK_DIR, exist_ok=True)
        os.makedirs(_LOGS_DIR, exist_ok=True)
        self.log_file = os.path.join(_LOGS_DIR, "rescue_process.log")

    def _log(self, msg):
        print(msg)
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")

    def _get_vs_script(self, source_path):
        """Genera un script simple de VapourSynth para pre-procesado."""
        script = f"""
import vapoursynth as vs
core = vs.core
# Cargamos el video (preferimos ffms2 por ser estándar en la suite)
clip = core.ffms2.Source(source='{source_path}')
# Filtro básico de limpieza (puedes añadir más awsmfunc aquí en el futuro)
clip = core.std.Transpose(clip) if clip.width < clip.height else clip
# Desentrelazado si fuera necesario o limpieza de ruido básica
clip = core.std.SetFrameProp(clip, prop='_Matrix', intval=1)
clip.set_output()
"""
        script_path = os.path.join(FAST_WORK_DIR, "temp_rescue.vpy")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script)
        return script_path

    def transcodificar_archivo(self, ruta_origen):
        """Convierte a H.264 monitorizando errores de integridad."""
        nombre_archivo = os.path.basename(ruta_origen)
        nombre_mkv = os.path.splitext(nombre_archivo)[0] + ".mkv"
        ruta_destino_temp = os.path.join(FAST_WORK_DIR, nombre_mkv)

        if os.path.exists(ruta_destino_temp):
            os.remove(ruta_destino_temp)

        print(f"   💉 Procesando en NVMe: {nombre_mkv}")
        
        # --- NUEVA LÓGICA VAPOURSYNTH (Punto 4) ---
        if _VS_AVAILABLE:
            print("   🎥 Usando VapourSynth para filtrado pre-encode...")
            vpy_script = self._get_vs_script(ruta_origen)
            # Pipe vspipe -> ffmpeg
            cmd = f"vspipe {vpy_script} - --y4m | ffmpeg -y -i - -i \"{ruta_origen}\" -map 0:v -map 1:a? -map 1:s? -c:v libx264 -preset medium -crf 23 -c:a aac -b:a 192k -ac 2 -c:s copy \"{ruta_destino_temp}\""
            process = subprocess.run(cmd, shell=True, capture_output=True, text=True, errors='ignore')
        else:
            # Monitorizamos stderr para detectar fallos de origen sin detener la codificación
            cmd = [
                "ffmpeg", "-y", "-v", "error", "-stats",
                "-i", ruta_origen,
                "-map", "0",
                "-c:v", "libx264", "-preset", "medium", "-crf", "23",
                "-c:a", "aac", "-b:a", "192k", "-ac", "2",
                "-c:s", "copy",
                ruta_destino_temp
            ]
            process = subprocess.run(cmd, capture_output=True, text=True, errors='ignore')
        
        # Buscamos trazas de corrupción en el log de ffmpeg
        errores_integrity = ["corrupt", "invalid", "error while decoding", "mis-match", "header missing"]
        sospecha_podrido = any(word in process.stderr.lower() for word in errores_integrity)

        if process.returncode != 0:
            self._log(f"   💥 FALLO CRÍTICO FFmpeg: {nombre_archivo}")
            return None, False

        return ruta_destino_temp, sospecha_podrido

    def procesar_lista(self, entrada, modo_estricto=False):
        """
        :param modo_estricto: Si True, solo procesa MKVs que fallen el check_health (Rescate).
                              Si False, procesa todo lo que encuentre (Legacy/God Mode).
        """
        stats = {"processed": 0, "saved_bytes": 0, "skipped": [], "failed": []}
        rutas = []
        if isinstance(entrada, list):
            rutas = entrada
        elif isinstance(entrada, str):
            entrada = entrada.strip().replace('"', '').replace("'", "")
            if not os.path.exists(entrada): return
            
            if os.path.isdir(entrada):
                # Si es modo estricto, nos centramos en rescatar MKVs
                if modo_estricto:
                    exts = ('.mkv',)
                else:
                    exts = ('.avi', '.mp4', '.m4v', '.divx', '.wmv', '.mov', '.mkv')
                
                for root, _, files in os.walk(entrada):
                    for f in files:
                        if f.lower().endswith(exts):
                            rutas.append(os.path.join(root, f))
            elif os.path.isfile(entrada):
                if entrada.lower().endswith('.txt'):
                    with open(entrada, 'r', encoding='utf-8') as f:
                        rutas = [l.strip().replace('"', '').replace("'", "") for l in f if l.strip()]
                else:
                    rutas = [entrada]
        
        if not rutas:
            print("⚠️ Nada que procesar.")
            return stats

        total = len(rutas)
        print(f"🚀 Iniciando cola de {total} archivos... (Modo Estricto: {modo_estricto})")

        for i, ruta_origen in enumerate(rutas):
            print(f"\n[{i+1}/{total}] 🔎 {os.path.basename(ruta_origen)}")
            
            if not os.path.exists(ruta_origen): continue
            org_size = os.path.getsize(ruta_origen)

            # --- TRIAGE MÉDICO ---
            if modo_estricto and ruta_origen.lower().endswith('.mkv'):
                print("   🩺 Chequeando salud...", end=" ")
                if self.verifier.check_health(ruta_origen):
                    print("✅ SANO. Saltando.")
                    stats["skipped"].append(ruta_origen)
                    continue
                else:
                    print("❌ ENFERMO/ROTO. Iniciando rescate...")

            # --- PROCESO ---
            start_time = time.time()
            ruta_nuevo, sospecha_podrido = self.transcodificar_archivo(ruta_origen)
            
            if not ruta_nuevo:
                stats["failed"].append(ruta_origen)
                continue 

            # --- VALIDACIÓN HÍBRIDA ---
            print("   ⚖️  Validando resultado...", end=" ")
            veredicto = self.verifier.check_rescue(ruta_origen, ruta_nuevo)

            if veredicto["valid"]:
                # Si hubo sospecha de corrupción durante el transcode, escaneamos a fondo el resultado
                if sospecha_podrido:
                    print("\n   ⚠️  Errores detectados en origen. Verificando integridad final...")
                    if not self.verifier.check_health(ruta_nuevo):
                        print("      💀 RECHAZADO: El archivo resultante sigue corrupto.")
                        veredicto["valid"] = False
                    else:
                        print("      ✅ ESTABLE: Cirugía exitosa pese a daños en origen.")

                if veredicto["valid"]:
                    try:
                        # El destino final siempre será .mkv con el mismo nombre base
                        nuevo_nombre_final = os.path.splitext(ruta_origen)[0] + ".mkv"
                        
                        # Si el origen es distinto al destino final (ej: era un .avi), borramos origen
                        # Si es el mismo (.mkv roto), os.remove lo limpia antes del move
                        if os.path.exists(ruta_origen):
                            os.remove(ruta_origen)
                        
                        shutil.move(ruta_nuevo, nuevo_nombre_final)
                        print(f"🎉 ÉXITO: {os.path.basename(nuevo_nombre_final)}")
                        
                        stats["processed"] += 1
                        stats["saved_bytes"] += (org_size - os.path.getsize(nuevo_nombre_final))
                        self._log(f"PROCESSED: {os.path.basename(ruta_origen)} -> {os.path.basename(nuevo_nombre_final)}")
                    except Exception as e:
                        self._log(f"   🚨 ERROR CRÍTICO AL MOVER: {e}")
                        stats["failed"].append(ruta_origen)
                else:
                    stats["failed"].append(ruta_origen)
                    if os.path.exists(ruta_nuevo): os.remove(ruta_nuevo)
            else:
                print(f"   💀 FALLO DE VALIDACIÓN: {veredicto.get('errors')}")
                stats["failed"].append(ruta_origen)
                if os.path.exists(ruta_nuevo): os.remove(ruta_nuevo)

            print(f"   ⏱️  {time.time() - start_time:.1f}s")
        
        if stats["skipped"]:
            print(f"\n✨ Se omitieron {len(stats['skipped'])} archivos sanos.")
        return stats
