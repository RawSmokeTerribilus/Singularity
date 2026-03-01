#!/bin/bash
# Push-The-Tank.sh - Rigor de actualización para Singularity

echo "--- 🛠️  Iniciando forja de la imagen v1.0 (Limpia y sin cache) ---"

# 1. Construir ignorando la cache para que pille los cambios del .py y el .dockerignore
sudo docker compose build --no-cache

# 2. Subir al Hub (Como el tag ya está en el YAML, lo pilla solo)
echo "--- ☁️  Subiendo el Tanque a Docker Hub... ---"
sudo docker push rawsmoke/singularity-suite:v1.0

echo "--------------------------------------------------------"
echo "✅ ¡Nube actualizada! Mañana solo tienes que hacer:"
echo "   sudo docker compose pull && sudo docker compose up -d"
echo "   en tu carpeta de producción."
echo "--------------------------------------------------------"
