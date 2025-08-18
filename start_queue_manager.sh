#!/bin/bash
# Script per avviare QueueManager

echo "🚀 Starting QueueManager System..."

# Vai nella directory del progetto
cd /home/pi/QueueManager 2>/dev/null || cd "$(dirname "$0")"

# Attiva virtual environment
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "❌ Virtual environment not found!"
    echo "Run: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Crea directory per logs se non esiste
mkdir -p logs
mkdir -p data

# Verifica permissions per GPIO (se hardware presente)
if [ -c "/dev/gpiomem" ]; then
    echo "🔧 Hardware GPIO available"
    # Aggiungi utente al gruppo gpio se necessario
    sudo usermod -a -G gpio $USER 2>/dev/null || true
else
    echo "⚠️ Running in simulation mode (no GPIO hardware)"
fi

# Abilita I2C se disponibile
if [ -c "/dev/i2c-1" ]; then
    echo "🔌 I2C available for display"
else
    echo "⚠️ I2C not available - display will run in simulation"
fi

# Imposta variabili d'ambiente
export FLASK_ENV=production
export FLASK_DEBUG=false
export LOG_LEVEL=INFO

# Avvia l'applicazione
echo "🎯 Starting Flask application..."
python app.py

# Se l'app si chiude, mostra il motivo
if [ $? -ne 0 ]; then
    echo "❌ Application exited with error"
    echo "Check logs in logs/ directory"
    exit 1
fi
