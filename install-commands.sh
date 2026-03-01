#!/bin/bash
# install-commands.sh (Versión Producción - Rigor Máximo)

# 1. CREACIÓN DE ESTRUCTURA DE PERSISTENCIA (Work Data)
# Evitamos que Docker cree carpetas donde queremos archivos
echo "Preparando estructura de directorios y archivos de persistencia..."

mkdir -p config work_data/mass_editor work_data/logs/MKVerything work_data/logs/RawLoadrr work_data/reports work_data/tmp docs

# Crear archivos vacíos (placeholders) para que Docker los monte como archivos, no directorios
touch work_data/mass_editor/ids.txt
touch work_data/mass_editor/completados.txt
touch work_data/mass_editor/completados_img.txt

# El JSON maestro necesita estructura mínima para que Python no explote
if [ ! -f work_data/mass_editor/mapeo_maestro.json ]; then
    echo "{}" > work_data/mass_editor/mapeo_maestro.json
fi

# 2. INSTALACIÓN DE COMANDOS EN EL SISTEMA (HOST)

# Comando principal: Lanza una instancia NUEVA de la suite
echo 'sudo docker exec -it singularity_core python3 singularity.py' | sudo tee /usr/local/bin/singularity
sudo chmod +x /usr/local/bin/singularity

# Comando de mantenimiento: Entra a la bash del contenedor
echo 'sudo docker exec -it singularity_core /bin/bash' | sudo tee /usr/local/bin/singularity-shell
sudo chmod +x /usr/local/bin/singularity-shell

echo "--------------------------------------------------------"
echo "¡Arsenal Singularity e Infraestructura listos!"
echo ""
echo "PASO NECESARIO: Copia tus archivos de configuración reales a:"
echo "  ./config/.env"
echo "  ./config/singularity_config.py"
echo "  ./config/config.py"
echo "  ./config/mass_config.py"
echo ""
echo "Usa 'singularity' para lanzar el menú (admite multitarea)."
echo "Usa 'singularity-shell' para entrar a la terminal interna."
echo "--------------------------------------------------------"
