#!/bin/bash
# -*- coding: utf-8 -*-
"""
SETUP MILNUEVE UPLOADRR - Tor + Dependencies Installer

Configures your system for:
- Tor SOCKS5 proxy
- Python dependencies
- Ready for automatic Tor fallback
"""

set -e  # Exit on error

echo "========================================"
echo "🔧 MILNUEVE UPLOADRR SETUP"
echo "========================================"
echo ""

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    echo "❌ Cannot detect OS"
    exit 1
fi

echo "📋 Detected OS: $OS"
echo ""

# Install Tor
echo "1️⃣  Installing Tor..."
case $OS in
    "fedora"|"rhel"|"centos")
        echo "   Using dnf (Fedora/RHEL/CentOS)"
        sudo dnf install -y tor
        ;;
    "debian"|"ubuntu")
        echo "   Using apt (Debian/Ubuntu)"
        sudo apt-get update
        sudo apt-get install -y tor
        ;;
    *)
        echo "   ⚠️  Unknown package manager for $OS"
        echo "   Please install Tor manually: https://www.torproject.org/download/"
        ;;
esac

echo "   ✓ Tor installed"
echo ""

# Enable and start Tor
echo "2️⃣  Configuring Tor service..."
sudo systemctl enable tor
sudo systemctl start tor
echo "   ✓ Tor service enabled and started"
echo ""

# Verify Tor
echo "3️⃣  Verifying Tor SOCKS5..."
if sudo ss -tlnp 2>/dev/null | grep -q 9050; then
    echo "   ✓ Tor SOCKS5 listening on port 9050"
else
    echo "   ⚠️  Tor SOCKS5 may not be ready yet (normal for first start)"
    echo "   Wait 10 seconds and manually verify with:"
    echo "   sudo ss -tlnp | grep tor"
fi
echo ""

# Install Python dependencies
echo "4️⃣  Installing Python dependencies..."
pip_cmd="pip3"

# Check if pip3 exists
if ! command -v $pip_cmd &> /dev/null; then
    echo "   Installing pip..."
    sudo dnf install -y python3-pip || sudo apt-get install -y python3-pip
fi

# Install required packages for Tor
echo "   Installing PySocks (for Tor SOCKS5)..."
$pip_cmd install --user PySocks 2>/dev/null || $pip_cmd install PySocks

echo "   ✓ Python dependencies installed"
echo ""

# Verify Tor accessibility from regular user
echo "5️⃣  Checking Tor connectivity..."
if python3 -c "
import socket
import sys
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('127.0.0.1', 9050))
    s.close()
    print('   ✓ Tor SOCKS5 accessible from user')
    sys.exit(0)
except Exception as e:
    print(f'   ⚠️  Cannot connect to Tor yet: {e}')
    print('   (This is OK, Tor may still be starting)')
    sys.exit(1)
" 2>/dev/null; then
    TOR_OK=1
else
    TOR_OK=0
fi
echo ""

# Summary
echo "========================================"
echo "✅ SETUP COMPLETE"
echo "========================================"
echo ""
echo "📊 Status:"
echo "   ✓ Tor installed"
echo "   ✓ Tor service configured"
if [ $TOR_OK -eq 1 ]; then
    echo "   ✓ Tor SOCKS5 accessible"
else
    echo "   ⏳ Tor SOCKS5 (starting, wait 10-20 seconds)"
fi
echo "   ✓ Python dependencies installed"
echo ""
echo "🚀 Next steps:"
echo ""
echo "1. Test Tor fallback:"
echo "   python3 -c \"from src.tor_client import TorSession; t = TorSession(); print('Tor ready!')\""
echo ""
echo "2. MILNUEVE upload with auto Tor fallback:"
echo "   python3 upload.py --tracker MILNU --input /archivo --unattended"
echo ""
echo "3. Check Tor status anytime:"
echo "   sudo systemctl status tor"
echo ""
echo "4. View Tor logs:"
echo "   sudo journalctl -u tor -f"
echo ""
echo "⚙️  Tor will automatically fallback when Milnueve is blocked by ISP"
echo ""
