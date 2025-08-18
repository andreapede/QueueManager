#!/bin/bash
# Script per verificare e avviare QueueManager

echo "🔍 Checking QueueManager setup..."

# Verifica Python e virtual environment
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Run: python3 -m venv .venv"
    exit 1
fi

# Attiva virtual environment
source .venv/bin/activate

# Verifica dipendenze critiche
echo "📦 Checking dependencies..."
python -c "import flask; print('✅ Flask OK')" || echo "❌ Flask missing"
python -c "import flask_socketio; print('✅ Flask-SocketIO OK')" || echo "❌ Flask-SocketIO missing"

# Verifica hardware (opzionale)
python -c "
try:
    import RPi.GPIO
    print('✅ RPi.GPIO OK')
except ImportError:
    print('⚠️ RPi.GPIO not available (simulation mode will be used)')
"

# Verifica I2C per display
if command -v i2cdetect &> /dev/null; then
    echo "🔌 Checking I2C devices..."
    sudo i2cdetect -y 1 2>/dev/null || echo "⚠️ No I2C devices found"
else
    echo "⚠️ i2c-tools not installed"
fi

echo "✅ Setup check completed!"
