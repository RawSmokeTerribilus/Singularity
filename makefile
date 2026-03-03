.PHONY: pull up down attach shell install restart logs
# --- RaW Suite: Singularity Core ---

# 1. Comandos de Orquestación Docker Compose (Preferido)
# pull: Descarga la imagen desde Docker Hub
pull:
	docker compose pull

build:
	docker build -t rawsmoke/singularity-suite:v1.4 .

up:
	docker compose up -d

down:
	docker compose down

restart:
	docker compose restart

logs:
	docker compose logs -f

# 2. Comandos de Acceso
attach:
	docker exec -it singularity_core python3 singularity.py

shell:
	docker exec -it singularity_core /bin/bash

# 3. Instalación de Estructura y Comandos Globales
install:
	@chmod +x final-user-install.sh
	@./final-user-install.sh
	@echo "RaW Suite: Estructura y comandos instalados correctamente."
