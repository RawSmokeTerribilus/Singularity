#!/bin/bash

echo "========================================"
echo "🔧 TOR SETUP - DOCKER MODE (v1.6.0)"
echo "========================================"

# 1. Detectar Entorno (Debian/RHEL)
if [ -f /etc/debian_version ]; then
    PKG_MANAGER="apt-get"
    INSTALL_CMD="apt-get update && apt-get install -y"
elif [ -f /etc/redhat-release ]; then
    PKG_MANAGER="dnf"
    INSTALL_CMD="dnf install -y"
fi

# 2. Instalación de Tor
echo "1️⃣  Instalando binarios de Tor..."
$INSTALL_CMD tor

# 3. Configuración de Inodo
echo "2️⃣  Configurando puerto SOCKS5..."
mkdir -p /etc/tor
echo "SocksPort 9050" > /etc/tor/torrc
echo "RunAsDaemon 1" >> /etc/tor/torrc

# 4. Lanzamiento Directo
echo "3️⃣  Iniciando servicio Tor..."
# En Docker no usamos systemctl, lanzamos el binario
tor --defaults-torrc /etc/tor/torrc & 

# 5. Dependencias Python
echo "4️⃣  Instalando PySocks..."
pip3 install --no-cache-dir requests[socks] pysocks

# 6. Verificación de Conectividad (Tu lógica de socket)
echo "5️⃣  Verificando socket 127.0.0.1:9050..."
python3 -c "
import socket
import sys
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    s.connect(('127.0.0.1', 9050))
    s.close()
    sys.exit(0)
except:
    sys.exit(1)
"
if [ $? -eq 0 ]; then
    TOR_OK=1
    echo "    ✓ Tor SOCKS5 accesible"
else
    TOR_OK=0
    echo "    ⏳ Tor arrancando en background..."
fi

echo "========================================"
echo "✅ SETUP COMPLETE"
echo "========================================"
