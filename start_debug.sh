#!/bin/bash
# Script per sviluppo con debug abilitato

echo "🐛 Starting QueueManager in DEBUG mode..."

cd "$(dirname "$0")"

# Attiva virtual environment
source .venv/bin/activate

# Crea directory necessarie
mkdir -p logs data

# Variabili per sviluppo
export FLASK_ENV=development
export FLASK_DEBUG=true
export LOG_LEVEL=DEBUG

# Avvia con reload automatico
echo "🔄 Debug mode - auto-reload enabled"
echo "📍 Access at: http://localhost:5000"
echo "📍 Admin at: http://localhost:5000/admin"
echo "🔑 Admin password: admin123"
echo ""
echo "Press Ctrl+C to stop"
echo ""

python app.py
