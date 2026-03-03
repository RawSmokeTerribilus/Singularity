#!/bin/bash
# Push-The-Tank.sh - Rigor de actualización para Singularity

echo "--- 🛠️  Iniciando forja de la imagen v1.4.0 (Limpia y sin cache) ---"

# 1. Construir ignorando la cache para asegurar frescura total
docker build --no-cache -t rawsmoke/singularity-suite:v1.4.0 .

# 2. Taggear como latest para despliegues estándar
docker tag rawsmoke/singularity-suite:v1.4.0 rawsmoke/singularity-suite:latest

# 3. Subir al Hub
echo "--- ☁️  Subiendo el Tanque (v1.4.0 & latest) a Docker Hub... ---"
docker push rawsmoke/singularity-suite:v1.4.0
docker push rawsmoke/singularity-suite:latest

echo "--------------------------------------------------------"
echo "✅ ¡Nube actualizada! Mañana solo tienes que hacer:"
echo "   sudo docker compose pull && sudo docker compose up -d"
echo "   en tu carpeta de producción."
echo "--------------------------------------------------------"
