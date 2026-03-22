SCRIPTS_SRC := RawLoadrr/src/trackers
WORK_TRACKERS := work_data/trackers

.PHONY: pull build up down restart logs attach shell install prep

# --- 1. Comandos de Orquestación ---
pull:
	docker compose pull

build:
	docker build -t rawsmoke/singularity-suite:v1.6.0 .
	docker tag rawsmoke/singularity-suite:v1.6.0 rawsmoke/singularity-suite:latest

up: prep
	docker compose up -d

down:
	docker compose down

restart:
	docker compose restart

logs:
	docker compose logs -f

# --- 2. Persistencia y Soberanía ---
prep:
	@echo "🔧 Verificando integridad de archivos de persistencia..."
	@mkdir -p work_data/mass_editor
	@mkdir -p work_data/logs/csi_log
	@mkdir -p $(WORK_TRACKERS)
	@mkdir -p work_data/tmp/qbit_backup
	@mkdir -p work_data/tmp/TEMP_RESCUE
	@if [ -d "$(SCRIPTS_SRC)" ] && [ -n "$$(ls -A $(SCRIPTS_SRC) 2>/dev/null)" ]; then \
		if [ -z "$$(ls -A $(WORK_TRACKERS))" ]; then \
			echo "🧬 Infundiendo trackers desde el source..."; \
			cp -rn $(SCRIPTS_SRC)/* $(WORK_TRACKERS)/; \
		fi; \
	fi
	@touch work_data/mass_editor/completados.txt
	@touch work_data/mass_editor/completados_img.txt
	@touch work_data/mass_editor/ids.txt
	@touch work_data/mass_editor/mapeo_maestro.json
	@mkdir -p config && touch config/.env
	@sudo chown -R $(USER):$(USER) work_data/
	@chmod -R 755 $(WORK_TRACKERS)
	@chmod -R 775 work_data/tmp
	@echo "✅ Estructura y permisos listos. Soberanía confirmada."

# --- 3. Comandos de Acceso ---
attach:
	docker exec -it singularity_core python3 singularity.py

shell:
	docker exec -it singularity_core /bin/bash

# --- 4. Instalación ---
install:
	@chmod +x final-user-install.sh
	@./final-user-install.sh
	@echo "RaW Suite: Estructura y comandos instalados correctamente."
