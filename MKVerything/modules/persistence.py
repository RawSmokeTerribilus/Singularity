import json
import os
import shutil
from datetime import datetime

class StateManager:
    def __init__(self, project_name, state_dir="states"):
        self.state_dir = state_dir
        # Limpiamos el nombre para que sea un nombre de archivo válido
        self.project_id = project_name.lower().replace(" ", "_")
        self.state_file = os.path.join(self.state_dir, f"{self.project_id}.json")
        self.data = self._load_state()

    def _load_state(self):
        """Carga el estado desde el JSON centralizado o crea uno nuevo."""
        if not os.path.exists(self.state_dir):
            os.makedirs(self.state_dir)

        if os.path.exists(self.state_file):
            with open(self.state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # Estado inicial para proyectos nuevos
        return {
            "project_info": {
                "name": self.project_id,
                "created_at": datetime.now().isoformat()
            },
            "last_global_number": 0,
            "processed_isos": {}, # { "hash_o_nombre": ["T01", "T02"] }
            "file_registry": []    # Lista de nombres de archivos generados
        }

    def save(self):
        """Guarda el estado de forma atómica (vía archivo temporal)."""
        temp_file = f"{self.state_file}.tmp"
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)
        
        # El truco del almendruco: reemplazo atómico
        os.replace(temp_file, self.state_file)

    def get_next_number(self):
        """Devuelve el siguiente número disponible (01, 02...)."""
        self.data["last_global_number"] += 1
        return f"{self.data['last_global_number']:02d}"

    def is_title_processed(self, iso_id, title_id):
        """Comprueba si un título específico de una ISO ya fue extraído."""
        titles = self.data["processed_isos"].get(iso_id, [])
        return title_id in titles

    def register_extraction(self, iso_id, title_id, filename):
        """Registra una extracción exitosa en el historial."""
        if iso_id not in self.data["processed_isos"]:
            self.data["processed_isos"][iso_id] = []
        
        self.data["processed_isos"][iso_id].append(title_id)
        self.data["file_registry"].append(filename)
        self.save()
