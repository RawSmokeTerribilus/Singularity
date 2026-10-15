SCRIPTS_SRC := RawLoadrr/src/trackers
WORK_TRACKERS := work_data/trackers

.PHONY: pull build up down restart logs attach shell install prep

# --- 1. Comandos de Orquestación ---
pull:
	docker compose pull

# El kit no trae Dockerfile: la imagen se baja de Docker Hub con `make pull`.
# (Aquí había un build con la v3.0.9 a fuego que no podía funcionar.)
build:
	@echo "El kit usa la imagen publicada: make pull && make up. Construir la imagen es cosa del repo completo."

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
	@mkdir -p work_data/logs/rawloadrr
	@mkdir -p work_data/logs/mkverything
	@mkdir -p $(WORK_TRACKERS)
	@mkdir -p work_data/tmp/qbit_backup
	@mkdir -p work_data/tmp/TEMP_RESCUE
	@# Antes solo sembraba si estaba vacío y los arreglos de los módulos no
	@# llegaban nunca; la lógica (refrescar + fusionar registro) vive en el instalador.
	@bash final-user-install.sh --solo-trackers
	@mkdir -p config
	@if [ ! -f config/.env ] && [ -f config/.env.example ]; then cp config/.env.example config/.env; echo "🧩 Creado config/.env desde plantilla NOBS"; fi
	@if [ ! -f config/.env ] && [ -f .env.example ]; then cp .env.example config/.env; echo "🧩 Creado config/.env desde .env.example"; fi
	@if [ ! -f config/singularity_config.py ] && [ -f config/singularity_config.py.example ]; then cp config/singularity_config.py.example config/singularity_config.py; echo "🧩 Creado config/singularity_config.py desde plantilla"; fi
	@if [ ! -f config/config.py ] && [ -f config/config.py.example ]; then cp config/config.py.example config/config.py; echo "🧩 Creado config/config.py desde plantilla con bloque NOBS"; fi
	@if [ ! -f config/mass_config.py ] && [ -f config/mass_config.py.example ]; then cp config/mass_config.py.example config/mass_config.py; echo "🧩 Creado config/mass_config.py desde plantilla NOBS"; fi
	@touch work_data/mass_editor/completados.txt
	@touch work_data/mass_editor/completados_img.txt
	@touch work_data/mass_editor/ids.txt
	@touch work_data/mass_editor/mapeo_maestro.json
	@touch work_data/mass_editor/titulos_mapa.json
	@touch work_data/mass_editor/mapeo_por_titulo.json
	@if [ ! -f config/.env ] || [ ! -f config/singularity_config.py ] || [ ! -f config/config.py ] || [ ! -f config/mass_config.py ]; then \
		echo "❌ Faltan archivos de config obligatorios en ./config"; \
		echo "   Esperados: .env, singularity_config.py, config.py, mass_config.py"; \
		echo "   Ejecuta: make install"; \
		exit 1; \
	fi
	@sudo chown -R $(USER):$(USER) work_data/
	@chmod -R 755 $(WORK_TRACKERS)
	@chmod -R 775 work_data/tmp
	@echo "✅ Estructura, plantillas y permisos listos. Soberanía confirmada."

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
