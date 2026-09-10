#!/bin/bash
# Push-The-Tank.sh - Rigor de actualización para Singularity
set -euo pipefail

cd "$(dirname "$0")"

# La versión sale del fichero VERSION, igual que en el makefile y en el LABEL
# del Dockerfile. Antes se escribía a mano aquí y sólo aquí se actualizaba, así
# que las imágenes publicadas salían etiquetadas v3.1.2 declarando ser la 3.0.2.
VERSION="$(cat VERSION)"
IMAGE="rawsmoke/singularity-suite"

echo "--- 🛠️  Iniciando forja de la imagen v${VERSION} (Limpia y sin cache) ---"

# 1. Construir ignorando la cache para asegurar frescura total
docker build --no-cache --build-arg "VERSION=${VERSION}" -t "${IMAGE}:v${VERSION}" .

# 2. Taggear como latest para despliegues estándar
docker tag "${IMAGE}:v${VERSION}" "${IMAGE}:latest"

# 3. Subir al Hub
echo "--- ☁️  Subiendo el Tanque (v${VERSION} & latest) a Docker Hub... ---"
docker push "${IMAGE}:v${VERSION}"
docker push "${IMAGE}:latest"

echo "--------------------------------------------------------"
echo "✅ ¡Nube actualizada! Mañana solo tienes que hacer:"
echo "   sudo docker compose pull && sudo docker compose up -d"
echo "   en tu carpeta de producción."
echo "--------------------------------------------------------"
