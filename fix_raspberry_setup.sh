#!/bin/bash
# Script per risolvere i problemi di installazione su Raspberry Pi

echo "🔧 Fixing Raspberry Pi setup issues..."

# 1. Installa Python development headers
echo "📦 Installing Python development headers..."
sudo apt update
sudo apt install -y python3-dev python3-setuptools

# 2. Installa build tools
echo "🛠️ Installing build tools..."
sudo apt install -y build-essential

# 3. Installa RPi.GPIO dal repository system (più stabile)
echo "⚡ Installing RPi.GPIO from system packages..."
sudo apt install -y python3-rpi.gpio

# 4. Installa altre dipendenze di sistema
echo "📚 Installing system dependencies..."
sudo apt install -y python3-pip python3-venv i2c-tools

# 5. Alternative: pip con --break-system-packages per le dipendenze problematiche
echo "🐍 Installing problematic packages with system override..."
pip install RPi.GPIO --break-system-packages

echo "✅ Setup completed!"
echo "Now you can run: pip install -r requirements.txt --break-system-packages"
