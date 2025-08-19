# Queue Manager System

Sistema avanzato di gestione coda per ufficio con supporto fisico (Raspberry Pi), interfaccia web e statistiche complete.

## 🎯 Panoramica

Sistema completo per la gestione intelligente dell'accesso ad un ufficio attraverso:

### 🚀 **Funzionalità Principali**
- **Accesso Multiplo**: Pulsante fisico diretto e sistema prenotazioni web
- **Rilevamento Intelligente**: Sensori PIR e ultrasonico con gestione conflitti
- **Gestione Coda Persistente**: Database SQLite con recupero automatico dopo riavvio
- **Dashboard Amministrativa**: Controllo completo con statistiche dettagliate
- **Notifiche Real-time**: WebSocket + opzionalmente Pushover
- **Sistema Resiliente**: Auto-recovery dopo interruzioni impreviste
- **Analytics Avanzate**: Statistiche complete su utilizzo, no-show, metodi accesso

### 📊 **Statistiche & Analytics**
- **Occupazioni**: Totali, durata media, tempo utilizzo
- **Metodi Accesso**: Differenziazione tra accesso diretto (pulsante) e web booking
- **Affidabilità**: Tasso successo, no-show tracking, efficienza sistema
- **Code**: Dimensione massima, tempi attesa, pattern utilizzo
- **Trends**: Analisi orarie, giornaliere, settimanali, mensili

### 🔄 **Startup Recovery System**
- **Auto-diagnosi**: Controllo stato hardware vs database al riavvio
- **Pulizia Intelligente**: Rimozione prenotazioni scadute/orfane
- **Ripristino Sessioni**: Continuazione sessioni attive interrotte  
- **Attivazione Coda**: Se ufficio libero e prenotazioni valide → scala automaticamente la coda
- **Consistenza Dati**: Allineamento automatico realtà fisica/digitale
- **Recovery Robusto**: Gestione errori con fallback sicuro

## 🔧 Hardware Richiesto

- Raspberry Pi Zero 2W
- Sensore PIR HC-SR501
- Sensore Ultrasonico HC-SR04
- Display OLED 0.96" SSD1306 (I2C)
- 2x Pulsanti tattili
- 4x LED (2 rossi, 2 verdi)
- Alimentazione 5V per Raspberry Pi e LED esterni

## 📦 Installazione

### 1. Configurazione Raspberry Pi

```bash
# Abilita I2C
sudo raspi-config
# Interfacing Options -> I2C -> Enable

# Installa dipendenze sistema
sudo apt update
sudo apt install python3-pip python3-venv git i2c-tools
```

### 2. Clone del repository

```bash
git clone https://github.com/andreapede/QueueManager.git
cd QueueManager
```

### 3. Setup ambiente virtuale

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Configurazione

```bash
# Copia configurazione di esempio
cp config/config_example.py config/config.py

# Modifica parametri se necessario
nano config/config.py
```

### 5. Inizializzazione database

```bash
python init_db.py
```

### 6. Test hardware (opzionale)

```bash
# Test sensori
python test/test_sensors.py

# Test display OLED
python test/test_display.py
```

## 🚀 Avvio

### Modalità sviluppo
```bash
source venv/bin/activate
python app.py
```

### Modalità produzione (con systemd)
```bash
sudo cp scripts/queuemanager.service /etc/systemd/system/
sudo systemctl enable queuemanager
sudo systemctl start queuemanager
```

## 🌐 Utilizzo

### Interfacce Web
- **Dashboard Utente**: `http://raspberry-pi-ip:5000`
  - Visualizzazione stato ufficio in tempo reale
  - Sistema prenotazioni con selezione utente
  - Statistiche utilizzo (tempo attesa medio)
  - Gestione posizione in coda (sostituzione)

- **Dashboard Admin**: `http://raspberry-pi-ip:5000/admin`
  - Controlli sistema (sblocco forzato, reset, svuota coda)
  - Statistiche dettagliate con filtri temporali (giorno/settimana/mese)
  - Log eventi in tempo reale
  - Gestione configurazione dinamica
  - Test hardware e diagnostica

### API REST Endpoints

#### **Status & Queue**
- `GET /api/status` - Stato attuale completo del sistema
- `GET /api/queue` - Visualizza coda con dettagli utenti
- `GET /api/stats` - Statistiche pubbliche di base
- `POST /api/book` - Nuova prenotazione
- `POST /api/book/replace` - Sostituisci posizione in coda

#### **Admin API**
- `GET /api/admin/stats?period=day|week|month` - Statistiche dettagliate
- `POST /api/admin/force_unlock` - Sblocco forzato ufficio
- `POST /api/admin/clear_queue` - Svuota coda
- `POST /api/admin/reset_system` - Reset completo sistema
- `GET /api/admin/events` - Log eventi recenti
- Vedi [API Documentation](docs/api.md) per dettagli completi

## � Funzionalità Avanzate

### 🎯 **Sistema di Recovery Automatico**
Al riavvio del sistema viene eseguita una **startup recovery** che:
- Verifica la consistenza tra stato hardware e database
- Ripristina sessioni attive interrotte
- Pulisce prenotazioni scadute o orfane  
- Riprende automaticamente il processamento della coda
- Logga tutte le operazioni di recovery

### 📊 **Analytics Comprehensive**
Il sistema traccia e analizza:
- **Occupancy Stats**: Sessioni totali, durata media, tempo utilizzo
- **Access Methods**: Distinzione tra accesso diretto (pulsante) e prenotazioni web
- **Reliability**: Tasso successo sessioni, tracking no-show, conflitti risolti
- **Queue Analytics**: Dimensione massima, pattern attesa, efficienza processamento  
- **Time-based Analysis**: Breakdown orario, trend giornalieri/settimanali/mensili

### 🔄 **Gestione Conflitti Avanzata**
- **Race Condition Prevention**: Gestione accessi simultanei pulsante/web
- **Conflict Resolution**: Sistema di priorità per risolvere conflitti
- **Duplicate Detection**: Prevenzione prenotazioni multiple stesso utente
- **Timeout Management**: Gestione automatica scadenze con cleanup

### 🛡️ **Sicurezza & Robustezza**
- **Session Management**: Login admin con timeout automatico
- **Rate Limiting**: Protezione da tentativi login multipli
- **Data Persistence**: Database SQLite con backup automatici
- **Error Handling**: Gestione robusti errori hardware/software
- **Logging Comprehensive**: Trace completo eventi sistema

## �📱 Interfacce

### Display OLED
Mostra in tempo reale:
- Stato ufficio (LIBERO/OCCUPATO)
- Dimensione coda
- Tempo di occupazione
- Prossimo utente in coda

### LED di Stato
- **Verde fisso**: Ufficio libero
- **Rosso fisso**: Ufficio occupato  
- **Lampeggio**: Warning o coda attiva
- **Spento**: Errore sistema

### Dashboard Web
- Stato real-time
- Form prenotazione
- Visualizzazione coda
- Statistiche utilizzo

## ⚙️ Configurazione

Parametri principali in `config/config.py`:

```python
# Timeout prenotazione (minuti)
RESERVATION_TIMEOUT_MINUTES = 3

# Durata massima occupazione (minuti) 
MAX_OCCUPANCY_MINUTES = 10

# Dimensione massima coda
MAX_QUEUE_SIZE = 7

# Priorità in caso di conflitto
CONFLICT_PRIORITY = 'presence'  # 'presence' o 'reservation'
```

## 🔧 Schema GPIO

| Componente | GPIO | Funzione |
|------------|------|----------|
| Display SDA | 2 | I2C Data |
| Display SCL | 3 | I2C Clock |
| PIR Sensor | 4 | Digital Input |
| Ultrasonic TRIG | 18 | Digital Output |
| Ultrasonic ECHO | 24 | Digital Input |
| Pulsante 1 | 17 | Digital Input |
| Pulsante 2 | 27 | Digital Input |
| LED 1 Rosso | 22 | Digital Output |
| LED 1 Verde | 23 | Digital Output |
| LED 2 Rosso | 25 | Digital Output |
| LED 2 Verde | 26 | Digital Output |

## 📊 Statistiche

Il sistema raccoglie automaticamente:
- Tempo medio di occupazione
- Numero accessi giornalieri
- Rapporto accessi diretti vs prenotazioni
- Tasso di no-show
- Ore di picco utilizzo

## 🛠️ Sviluppo

### Struttura del progetto
```
QueueManager/
├── app.py                 # Applicazione principale
├── hardware/             # Controllo hardware
├── api/                  # Endpoint API REST
├── web/                  # Frontend web
├── database/             # Gestione database
├── config/               # Configurazioni
├── utils/                # Utilità varie
├── test/                 # Test hardware/software  
└── scripts/              # Script installazione/deploy
```

### Database Schema Completo
```sql
-- Utenti sistema
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,      -- Codice utente (es: "05")
    name TEXT NOT NULL,             -- Nome utente
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Sistema coda con stati avanzati
CREATE TABLE queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_code TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'waiting',   -- waiting/active/completed/no_show
    start_time DATETIME,            -- Quando diventa attiva
    end_time DATETIME,              -- Quando completata
    FOREIGN KEY (user_code) REFERENCES users(code)
);

-- Statistiche occupazioni dettagliate
CREATE TABLE occupancy_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_time DATETIME NOT NULL,
    end_time DATETIME,
    access_type TEXT NOT NULL,      -- 'direct' o 'reservation'  
    user_code TEXT,
    duration_minutes INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_code) REFERENCES users(code)
);

-- Log eventi sistema completo
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    event_type TEXT NOT NULL,       -- BOOKING_CREATED, SESSION_STARTED, ecc.
    user_code TEXT,
    duration_minutes INTEGER,
    state_from TEXT,               -- Stato precedente
    state_to TEXT,                 -- Nuovo stato
    queue_size INTEGER,            -- Dimensione coda al momento
    no_show BOOLEAN DEFAULT FALSE,
    conflict_occurred BOOLEAN DEFAULT FALSE,
    details TEXT,                  -- Dettagli aggiuntivi
    FOREIGN KEY (user_code) REFERENCES users(code)
);

-- Configurazione dinamica
CREATE TABLE config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Architettura Sistema

#### 🔄 **Event-Driven Architecture**
- **Main Loop**: Controllo hardware continuo (1Hz)
- **Background Scheduler**: Cleanup periodico, timeout gestione
- **WebSocket Layer**: Real-time updates a tutti i client connessi
- **Database Transactions**: ACID compliance per operazioni critiche

#### 🧠 **Startup Recovery System**
Al boot il sistema esegue diagnostica completa:

1. **Hardware State Check**: Verifica sensori fisici
2. **Database Consistency**: Confronto stato DB vs realtà  
3. **Orphaned Sessions**: Cleanup prenotazioni attive orfane
4. **Expired Reservations**: Rimozione timeout scaduti
5. **Queue Restoration**: Ripristino processamento coda
6. **Event Logging**: Trace completo recovery per debugging

#### 📊 **Analytics Engine**
Sistema di statistiche multi-livello:
- **Real-time Metrics**: Aggiornamenti istantanei
- **Aggregated Stats**: Pre-calcolo per performance
- **Historical Trends**: Analisi temporali avanzate
- **Comparative Analysis**: Confronti periodo su periodo

## 🧪 Testing & Quality Assurance

### Test Hardware
```bash
# Test completo sistema
python test/full_system_test.py

# Test sensori individuali  
python test/test_pir_sensor.py
python test/test_ultrasonic.py
python test/test_display.py

# Test GPIO e LED
python test/test_gpio_outputs.py
```

### Test Software
```bash
# Test unitari componenti
python -m pytest test/unit/ -v

# Test integrazione API
python test/api_integration_test.py

# Test database recovery
python test/test_startup_recovery.py

# Load testing
python test/load_test.py --concurrent 10 --duration 60
```

### Debugging Avanzato
```bash
# Modalità debug con trace completo
python app.py --debug --trace-hardware

# Monitor real-time eventi
tail -f data/logs/queuemanager.log | grep -E "(RECOVERY|CONFLICT|ERROR)"

# Analisi database
sqlite3 data/queue_manager.db ".schema"
sqlite3 data/queue_manager.db "SELECT * FROM events ORDER BY timestamp DESC LIMIT 20;"
```

## 🚀 Deployment Produzione

### Setup Completo Raspberry Pi
```bash
# Preparazione sistema
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv git i2c-tools sqlite3

# Setup repository
git clone https://github.com/andreapede/QueueManager.git
cd QueueManager
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configurazione GPIO
sudo usermod -a -G gpio,i2c $USER
sudo systemctl enable ssh

# Database inizializzazione
python database/db_manager.py --init
python utils/import_users.py --csv data/users.csv

# Test hardware completo
python test/hardware_integration.py
```

### Systemd Service Setup
```bash
# Service configuration
sudo cp scripts/queuemanager.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable queuemanager

# Environment configuration
sudo mkdir -p /etc/queuemanager
sudo cp config/.env.production /etc/queuemanager/.env

# Avvio e monitoring
sudo systemctl start queuemanager
sudo systemctl status queuemanager
```

### Backup & Recovery
```bash
# Backup automatico database
python utils/backup_manager.py --auto-schedule

# Recovery da backup
python utils/backup_manager.py --restore --file backup_20250819_120000.db

# Export statistiche
python utils/export_stats.py --format csv --period month --output stats_export.csv
```

## 🔧 Troubleshooting Avanzato

### Problemi Startup Recovery
```bash
# Debug recovery process
python app.py --debug-recovery 2>&1 | tee recovery_debug.log

# Force reset sistema in caso emergenza
python utils/emergency_reset.py --confirm

# Riparazione database corrotto
python utils/db_repair.py --analyze --repair
```

### Performance Monitoring
```bash
# Monitoring risorse sistema
python utils/system_monitor.py --realtime

# Analisi query database lente
python utils/db_profiler.py --slow-queries --threshold 100ms

# Memory leak detection
python utils/memory_profiler.py --duration 3600
```

### Diagnostica Hardware
```bash
# Test completo connessioni
python hardware/diagnostic_tool.py --full-check

# Calibrazione sensori
python hardware/sensor_calibration.py --pir --ultrasonic

# Test stress GPIO
python test/gpio_stress_test.py --duration 300
```

## 📈 Analytics & Reporting

### Statistiche Avanzate
Il sistema genera automaticamente:

- **📊 Dashboard Metrics**: Real-time KPI per admin
- **📈 Trend Analysis**: Pattern utilizzo temporali
- **🎯 Performance Reports**: Efficienza sistema, no-show rates  
- **💡 Insights**: Raccomandazioni ottimizzazione
- **📅 Scheduled Reports**: Export automatici periodici

### Business Intelligence
```bash
# Report utilizzo mensile
python utils/generate_report.py --type monthly --format pdf

# Analisi pattern utilizzo
python analytics/usage_patterns.py --analyze-peaks --timeframe 30d

# Previsioni carico
python analytics/demand_forecasting.py --predict-next 7d
```

## 🤝 Sviluppo & Contribuzioni

### Guidelines Sviluppo
- **Code Style**: Seguire PEP 8, utilizzare black formatter
- **Testing**: Copertura minima 80% per nuove features
- **Documentation**: Docstring complete per tutti i metodi pubblici
- **Hardware Testing**: Testare su Raspberry Pi reale prima merge

### Feature Request Process
1. 💡 **Proposta**: GitHub Discussion con caso d'uso dettagliato
2. 🎯 **Specification**: Design document con requisiti tecnici  
3. 🛠️ **Implementation**: Development in feature branch
4. 🧪 **Testing**: Unit + integration tests completi
5. 📝 **Documentation**: Aggiornamento README e API docs
6. 🔄 **Review**: Code review da maintainer
7. 🚀 **Merge**: Deploy in main branch

## 📞 Supporto & Community

### Canali Supporto
- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/andreapede/QueueManager/issues) con template
- 💡 **Feature Requests**: [GitHub Discussions](https://github.com/andreapede/QueueManager/discussions)  
- 📖 **Documentation**: [Wiki](https://github.com/andreapede/QueueManager/wiki)
- 💬 **Community Chat**: Discord server per discussioni real-time

### SLA & Response Times
- 🔴 **Critical Issues**: < 24h response time
- 🟡 **Bug Reports**: < 72h response time  
- 🔵 **Feature Requests**: < 1 week feedback
- 📚 **Documentation**: Updates with each release

## 📋 Roadmap & Future Features

### v2.1.0 (Q3 2025)
- 🔔 **Mobile App**: Notifiche push native iOS/Android
- 🌍 **Multi-language**: Supporto i18n italiano/inglese
- 📱 **QR Codes**: Check-in veloce tramite QR
- 🔐 **LDAP Integration**: Authentication enterprise

### v2.2.0 (Q4 2025)  
- 🤖 **AI Predictions**: Machine learning per previsioni carico
- 📊 **Advanced Analytics**: Dashboards interattive con grafici
- 🔗 **API Extensions**: GraphQL endpoint per integrazioni
- 🏢 **Multi-office**: Gestione network di uffici

### v3.0.0 (2026)
- ☁️ **Cloud Sync**: Sincronizzazione multi-site
- 🧠 **Smart Scheduling**: Ottimizzazione automatica orari
- 📞 **VoIP Integration**: Notifiche telefoniche
- 🏗️ **Microservices**: Architettura scalabile

## 📄 Licenza & Copyright

MIT License - Vedi file [LICENSE](LICENSE) per dettagli completi.

**Copyright © 2025 QueueManager Contributors**

---

<div align="center">

**🎯 Sistema Professionale per Gestione Efficiente Accessi Uffici**

*Sviluppato con ❤️ per massimizzare produttività e user experience*

[![GitHub stars](https://img.shields.io/github/stars/andreapede/QueueManager)](https://github.com/andreapede/QueueManager/stargazers)
[![GitHub issues](https://img.shields.io/github/issues/andreapede/QueueManager)](https://github.com/andreapede/QueueManager/issues)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

</div>
