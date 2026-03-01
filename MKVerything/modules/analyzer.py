import subprocess
import re
import logging

class DiscScanner:
    def __init__(self, min_duration=900, block_threshold=2700):
        self.min_duration = min_duration
        self.block_threshold = block_threshold

    def scan_iso(self, iso_path):
        logging.debug(f"Iniciando volcado de info para: {iso_path}")
        
        cmd = ["makemkvcon", "-r", "info", f"iso:{iso_path}"]
        # Ejecutamos con timeout para que no se quede colgado si la ISO está corrupta
        try:
            process = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', timeout=60)
        except Exception as e:
            logging.error(f"Error al ejecutar makemkvcon: {e}")
            return []

        if not process.stdout:
            logging.warning("MakeMKV no devolvió ninguna información. ¿Está instalada la CLI?")
            return []

        return self._parse_output(process.stdout)

    def _parse_output(self, raw_output):
        titles = []
        # Capturamos ID y Duración
        # TINFO:ID,9,0,"H:MM:SS"
        pattern = re.compile(r'TINFO:(\d+),9,0,"(\d+:\d+:\d+)"')
        
        lines = raw_output.splitlines()
        logging.debug(f"Procesando {len(lines)} líneas de output de MakeMKV...")

        for line in lines:
            match = pattern.search(line)
            if match:
                title_id = match.group(1)
                duration_str = match.group(2)
                
                h, m, s = map(int, duration_str.split(':'))
                total_seconds = h * 3600 + m * 60 + s
                
                if total_seconds >= self.min_duration:
                    is_block = total_seconds >= self.block_threshold
                    titles.append({
                        "id": title_id,
                        "duration_sec": total_seconds,
                        "duration_readable": duration_str,
                        "is_block": is_block,
                        "label": "BLOQUE" if is_block else "EPISODIO"
                    })
                    logging.debug(f"Título detectado: ID {title_id} | Duración {duration_str}")

        if not titles:
            logging.info("No se encontraron títulos que superen el tiempo mínimo.")
            
        return sorted(titles, key=lambda x: int(x['id']))
