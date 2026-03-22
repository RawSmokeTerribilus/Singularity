import os
import subprocess
import sys
import shutil
import time
from pathlib import Path
try:
    import vapoursynth as vs
    core = vs.core
    _VS_AVAILABLE = True
except ImportError:
    _VS_AVAILABLE = False

from .verifier import Verifier
from .hardware_agent import HardwareAgent

_MKVE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LOGS_DIR = os.path.join(_MKVE_ROOT, "logs")
FAST_WORK_DIR = "/app/RawLoadrr/tmp/TEMP_RESCUE"
_LWI_CACHE_DIR = Path("/app/work_data/tmp")
_VSPIPE_BIN = shutil.which('vspipe')


class UniversalRescuer:
    def __init__(self):
        self.verifier = Verifier()
        self.agent = HardwareAgent()
        os.makedirs(FAST_WORK_DIR, exist_ok=True)
        _LWI_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        os.makedirs(_LOGS_DIR, exist_ok=True)
        self.log_file = os.path.join(_LOGS_DIR, "rescue_process.log")
        self._log("🦾 Hardware Agent inicializado.")

    def _log(self, msg):
        print(msg)
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")

    def _get_vs_script(self, source_path):
        """Genera un script VapourSynth con un nombre de archivo fijo para el pipe."""
        source_repr = repr(str(source_path))
        script = f"""import vapoursynth as vs
core = vs.core
clip = core.lsmas.LWLibavSource(source={source_repr})
clip = core.std.Transpose(clip) if clip.width < clip.height else clip
clip.set_output()
"""
        # Usamos un nombre de script fijo en el directorio de trabajo rápido.
        script_path = Path(FAST_WORK_DIR) / "script.vpy"
        script_path.write_text(script, encoding="utf-8")
        return str(script_path)

    def _run_command(self, cmd, level_name, fallback_trigger=None):
        """Ejecuta un comando. Si falla y `fallback_trigger` está en stderr, devuelve un código especial."""
        try:
            if "ffmpeg" in cmd and "-hide_banner" not in cmd:
                cmd = cmd.replace("ffmpeg", "ffmpeg -hide_banner", 1)

            process = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, errors='ignore'
            )
            
            if process.returncode != 0:
                self._log(f"   ⚠️  Fallo técnico en {level_name} (Código {process.returncode}). Detalles a continuación.")
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(f"\n--- ERROR DETALLADO {level_name} ---\n")
                    f.write(f"Comando: {cmd}\n")
                    f.write(process.stderr)
                    f.write("\n--------------------------------------------\n")
                
                print(f"   ⚠️  Fallo técnico en {level_name} (Código {process.returncode}). Detalles en el log.")

                if fallback_trigger and fallback_trigger in process.stderr:
                    return "FALLBACK_TRIGGERED"
                
                return False
            return True
        except Exception as e:
            self._log(f"   💥 EXCEPCIÓN CRÍTICA EN {level_name}: {e}")
            return False

    def execute_strategy(self, level, input_file, output_file):
        """Construye y ejecuta el comando FFmpeg según el nivel y la estrategia del HardwareAgent."""
        if level == 3:
            level_name = "Nivel 3 (VapourSynth + HW)"
            if not (Path(FAST_WORK_DIR) / "script.vpy").exists():
                self._log(f"   💥 No se encontró script.vpy para Nivel 3.")
                return False
            hw_args = self.agent.get_transcode_args(target_codec="h264")
            vpy_path = str(Path(FAST_WORK_DIR) / "script.vpy")
            cmd = f"{_VSPIPE_BIN} -c y4m \"{vpy_path}\" - | ffmpeg -hide_banner -y -i - -i \"{input_file}\" -map 0:v -map 1:a? -map 1:s? {hw_args} \"{output_file}\""
            return self._run_command(cmd, level_name)

        elif level == 2:
            level_name = "Nivel 2 (Remux Médico)"
            cmd = f"ffmpeg -hide_banner -y -fflags +genpts -i \"{input_file}\" -map 0 -c:v copy -c:a aac -af aresample=async=1 -c:s srt \"{output_file}\""
            return self._run_command(cmd, level_name)

        elif level == 1:
            # --- Intento 1.1: El Rápido (GPU via Agente) ---
            level_name_hw = "Nivel 1 (HW)"
            self._log(f"   🪜 {level_name_hw}: Intentando recodificación acelerada por hardware...")
            hw_args = self.agent.get_transcode_args(target_codec="h264")
            
            # Comando HW estándar
            hw_cmd = f"ffmpeg -hide_banner -y -i \"{input_file}\" -map 0 {hw_args} \"{output_file}\""
            
            # Usamos tu nueva lógica de detección de fallback
            result = self._run_command(hw_cmd, level_name_hw, fallback_trigger="Could not write header")

            if result is True:
                return True
            
            # Si la AMD escupe el error de cabeceras (o falla por cualquier otra cosa), 
            # sacamos el "Tanque" de la CPU.
            if result == "FALLBACK_TRIGGERED" or result is False:
                level_name_cpu = "Nivel 1 (CPU Tank)"
                reason = "Fallo de cabecera" if result == "FALLBACK_TRIGGERED" else "Error crítico en HW"
                self._log(f"   ↪️ {reason}. Activando fallback a {level_name_cpu}...")
                
                # El comando "Invencible": libx264 + limpieza profunda
                cpu_cmd = (
                    f"ffmpeg -hide_banner -y -i \"{input_file}\" "
                    f"-c:v libx264 -preset fast -crf 22 "
                    f"-c:a aac -b:a 128k -c:s srt " # Pasamos subs a SRT para evitar errores de muxing
                    f"-map 0:v:0 -map 0:a? -map 0:s? "
                    f"-ignore_unknown -map_metadata -1 "
                    f"-metadata:s:v:0 sar=1/1 " # Enderezamos el aspecto rancio de WinX
                    f"-fflags +genpts+igndts+discardcorrupt "
                    f"\"{output_file}\""
                )
                return self._run_command(cpu_cmd, level_name_cpu)
            
            return False
        
        self._log(f"   💥 Nivel de estrategia desconocido: {level}")
        return False

    def transcodificar_archivo(self, ruta_origen):
        """
        Implementa la "Escalera de Resiliencia" para procesar un archivo de vídeo.
        Prueba secuencialmente desde el método más sofisticado al más robusto.
        """
        nombre_archivo = os.path.basename(ruta_origen)
        nombre_mkv = os.path.splitext(nombre_archivo)[0] + ".mkv"
        ruta_destino_temp = os.path.join(FAST_WORK_DIR, nombre_mkv)

        if os.path.exists(ruta_destino_temp):
            os.remove(ruta_destino_temp)

        self._log(f"   💉 Procesando en NVMe: {nombre_mkv}")
        
        # --- NIVEL 3: VAPOURSYNTH + HW ---
        self._log(f"   🪜 Intentando Nivel 3 (VapourSynth + HW)...")
        if _VS_AVAILABLE and _VSPIPE_BIN:
            vpy_script_path = self._get_vs_script(ruta_origen)
            if self.execute_strategy(level=3, input_file=ruta_origen, output_file=ruta_destino_temp):
                self._log(f"   ✅ ÉXITO en Nivel 3 para '{nombre_archivo}'.")
                if os.path.exists(vpy_script_path): os.remove(vpy_script_path)
                lwi_file = Path(ruta_origen).with_suffix('.lwi')
                if lwi_file.exists(): 
                    try:
                        os.remove(lwi_file)
                    except OSError: pass
                return ruta_destino_temp, True
            
            # Cleanup en caso de fallo
            if os.path.exists(vpy_script_path): os.remove(vpy_script_path)
            lwi_file = Path(ruta_origen).with_suffix('.lwi')
            if lwi_file.exists(): 
                try:
                    os.remove(lwi_file)
                except OSError: pass
        else:
            self._log("   ⚠️ VapourSynth o vspipe no están disponibles. Saltando Nivel 3.")

        # --- NIVEL 2: REMUX MÉDICO (CPU) ---
        self._log(f"   ↪️ Fallback a Nivel 2 (Remux Médico)...")
        if self.execute_strategy(level=2, input_file=ruta_origen, output_file=ruta_destino_temp):
            self._log(f"   ✅ ÉXITO en Nivel 2 para '{nombre_archivo}'.")
            return ruta_destino_temp, True
            
        # --- NIVEL 1: RECODIFICACIÓN BRUTA + HW ---
        self._log(f"   ↪️ Fallback a Nivel 1 (Recodificación Bruta + HW)...")
        if self.execute_strategy(level=1, input_file=ruta_origen, output_file=ruta_destino_temp):
            self._log(f"   ✅ ÉXITO en Nivel 1 para '{nombre_archivo}'.")
            return ruta_destino_temp, True

        # --- NIVEL 0: SALVAGUARDA ---
        self._log(f"   🪜 Nivel 0 (Salvaguarda): Todos los métodos fallaron para '{nombre_archivo}'.")
        self._log(f"   🛑 REQUIRES_MANUAL_REVIEW: {ruta_origen}")
        
        if os.path.exists(ruta_destino_temp):
            os.remove(ruta_destino_temp)
            
        return None, False

    def procesar_lista(self, entrada, modo_estricto=False, fast_scan=False): # <--- Adición
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
                print(f"    🩺 Chequeando salud ({'GODDESS' if fast_scan else 'GOD'} MODE)...", end=" ")
                if self.verifier.check_health(ruta_origen, fast_mode=fast_scan): # <--- Pasamos el flag
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

