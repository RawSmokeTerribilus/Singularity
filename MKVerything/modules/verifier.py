import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from singularity_config import SPAM_KEYWORDS

import json
import subprocess
import hashlib
import re
import difflib
from datetime import datetime

class Verifier:
    def __init__(self, log_file="../logs/security_audit.log"):
        # Aseguramos que el log vaya a la carpeta logs/ correcta
        self.log_file = os.path.abspath(os.path.join(os.path.dirname(__file__), log_file))
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

    def _log(self, message, level="INFO"):
        """Registra eventos en archivo."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] [{level}] {message}\n")

    # =========================================================================
    # HERRAMIENTAS INTERNAS
    # =========================================================================

    def _run_mediainfo(self, filepath):
        cmd = ["mediainfo", "--Output=JSON", filepath]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            if result.returncode == 0: return json.loads(result.stdout)
        except: pass
        return None

    def _run_ffprobe(self, filepath):
        cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", filepath]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            if result.returncode == 0: return json.loads(result.stdout)
        except: return None
        return None

    def _get_mkv_title_tag(self, filepath):
        try:
            cmd = ["mkvmerge", "-J", filepath]
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return data.get("container", {}).get("properties", {}).get("title", "")
        except: pass
        return ""

    # =========================================================================
    # DIAGNÓSTICO DE SALUD (ESCRUPULOSO)
    # =========================================================================

    def check_health(self, filepath):
        """
        AUDITORÍA COMPLETA DE INTEGRIDAD:
        1. Estructural (mkvmerge -J).
        2. Metadatos (ffprobe).
        3. Decodificación FULL (ffmpeg null scan).
        """
        # 1. Prueba Estructural MKV
        if filepath.lower().endswith(".mkv"):
            try:
                subprocess.run(["mkvmerge", "-J", filepath], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except subprocess.CalledProcessError:
                self._log(f"Fallo Estructural: {os.path.basename(filepath)}", "FAIL")
                return False

        # 2. Prueba de Metadatos
        meta = self._run_ffprobe(filepath)
        if not meta:
            self._log(f"FFprobe ilegible: {os.path.basename(filepath)}", "FAIL")
            return False
        
        try:
            dur = float(meta['format'].get('duration', 0))
            if dur <= 0: return False
            tracks = self._count_tracks_ffprobe(meta)
            if tracks['video'] == 0: return False
        except: return False

        # 3. PRUEBA DE FUEGO: Decodificación Completa (Sin límite de tiempo)
        try:
            # -xerror: detiene el proceso al primer error de decodificación
            # -f null -: no genera salida, solo procesa el chorro de datos
            cmd_decode = ["ffmpeg", "-v", "error", "-xerror", "-i", filepath, "-f", "null", "-"]
            subprocess.run(cmd_decode, check=True, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError:
            self._log(f"Integridad Comprometida (Full Scan): {os.path.basename(filepath)}", "FAIL")
            return False

        return True
        
    def check_iso_extraction(self, iso_path, mkv_path):
        """
        Versión de compatibilidad para el extract viejo.
        Verifica que el remux de la ISO sea válido.
        """
        report = {"valid": False, "errors": []}
        
        if not os.path.exists(mkv_path):
            report["errors"].append("FILE_NOT_FOUND")
            return report

        # Si el archivo existe, le pasamos el test de salud rápido
        # (ffprobe + estructura mkv)
        try:
            # Chequeo rápido de integridad
            is_healthy = self.check_health(mkv_path)
            if is_healthy:
                report["valid"] = True
                report["level"] = "SUCCESS"
            else:
                report["errors"].append("CORRUPT_STRUCTURE")
        except Exception as e:
            report["errors"].append(f"VERIFICATION_ERROR: {str(e)}")
            
        return report

    # =========================================================================
    # COMPARATIVA RESCUE
    # =========================================================================

    def check_rescue(self, file_orig, file_new):
        report = {"valid": False, "level": "FAIL", "errors": [], "details": {}}

        if not os.path.exists(file_new) or os.path.getsize(file_new) < 1024:
            report["errors"].append("FILE_EMPTY_OR_MISSING")
            return report

        meta_orig = self._run_ffprobe(file_orig)
        meta_new = self._run_ffprobe(file_new)
        
        if not meta_new:
            mi_data = self._run_mediainfo(file_new)
            if mi_data and "media" in mi_data: meta_new_mi = mi_data
            else:
                report["errors"].append("METADATA_UNREADABLE")
                return report

        t_orig = self._count_tracks_ffprobe(meta_orig)
        t_new = self._count_tracks_ffprobe(meta_new)
        
        if t_new['video'] < t_orig['video']: report["errors"].append("VIDEO_TRACK_LOST")
        if t_new['audio'] < t_orig['audio']: report["errors"].append("AUDIO_TRACK_LOST")
        if t_new['subtitle'] < t_orig['subtitle']: report["errors"].append("SUBTITLE_TRACK_LOST")

        dur_orig = float(meta_orig['format'].get('duration', 0)) if meta_orig else 0
        dur_new = float(meta_new['format'].get('duration', 0)) if meta_new else 0
        
        if dur_orig < 10 and dur_new > 60:
            report["details"]["note"] = "RECOVERED_FROM_CORRUPT"
        elif abs(dur_orig - dur_new) > (dur_orig * 0.10):
            report["errors"].append(f"DUR_DIFF ({dur_orig:.0f}s vs {dur_new:.0f}s)")

        w_orig = self._get_width(meta_orig)
        w_new = self._get_width(meta_new)
        if w_new < (w_orig * 0.98): report["errors"].append("RESOLUTION_DROP")

        if not report["errors"]:
            report["valid"] = True
            report["level"] = "SUCCESS"
        else:
            self._log(f"Fallo Rescue: {os.path.basename(file_orig)} -> {report['errors']}", "FAIL")

        return report

    def audit_file_metadata(self, filepath):
        embedded_title = self._get_mkv_title_tag(filepath)
        filename = os.path.basename(filepath)
        report = {"clean": True, "spam_detected": False, "title_mismatch": False}
        if not embedded_title: return report

        lower_title = embedded_title.lower()
        for word in SPAM_KEYWORDS:
            if word in lower_title:
                report["spam_detected"] = True; report["clean"] = False; report["spam_word"] = word; break

        ratio = difflib.SequenceMatcher(None, filename.lower(), lower_title).ratio()
        if ratio < 0.4 and len(embedded_title) > 5:
            report["title_mismatch"] = True; report["clean"] = False
        return report

    def _count_tracks_ffprobe(self, meta):
        tracks = {'video': 0, 'audio': 0, 'subtitle': 0}
        if meta:
            for s in meta.get('streams', []):
                ctype = s.get('codec_type')
                if ctype in tracks: tracks[ctype] += 1
        return tracks

    def _get_width(self, meta):
        if not meta: return 0
        for s in meta.get('streams', []):
            if s.get('codec_type') == 'video': return int(s.get('width', 0))
        return 0
