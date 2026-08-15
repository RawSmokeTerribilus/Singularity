#!/bin/bash
# Push-The-Tank.sh - Rigor de actualización para Singularity

echo "--- 🛠️  Iniciando forja de la imagen v3.0.9 (Limpia y sin cache) ---"

# 1. Construir ignorando la cache para asegurar frescura total
docker build --no-cache -t rawsmoke/singularity-suite:v3.0.9 .

# 2. Taggear como latest para despliegues estándar
docker tag rawsmoke/singularity-suite:v3.0.9 rawsmoke/singularity-suite:latest

# 3. Subir al Hub
echo "--- ☁️  Subiendo el Tanque (v3.0.9 & latest) a Docker Hub... ---"
docker push rawsmoke/singularity-suite:v3.0.9
docker push rawsmoke/singularity-suite:latest

echo "--------------------------------------------------------"
echo "✅ ¡Nube actualizada! Mañana solo tienes que hacer:"
echo "   sudo docker compose pull && sudo docker compose up -d"
echo "   en tu carpeta de producción."
echo "--------------------------------------------------------"
