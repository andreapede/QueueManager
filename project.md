# Sistema Gestione Coda Ufficio - Specifiche Progetto

## 📋 Panoramica Generale

**Obiettivo**: Sviluppare un sistema di gestione coda per l'accesso ad un singolo ufficio con supporto fisico (Raspberry Pi) e interfaccia web.

**Funzionalità Principali**:
- Rilevamento presenza tramite sensori
- Accesso diretto fisico se ufficio libero
- Sistema prenotazioni web con gestione coda
- Notifiche multi-canale
- Dashboard amministrativa protetta
- Sistema statistiche avanzate

---

## 🔧 Hardware Utilizzato

### Componenti Principali
- **Raspberry Pi Zero 2W** (controllore principale)
- **Alimentazione**: USB-C 5V 3A + alimentatore esterno 5V 1A per LED
- **Sensore PIR HC-SR501** (rilevamento movimento)
- **Sensore Ultrasonico HC-SR04** (rilevamento presenza statica)
- **Display OLED 0.96" SSD1306** (I2C, 128x64 pixel)
- **2x Pulsanti tattili** + **4x LED separati** (2 rossi, 2 verdi)

### Mappatura GPIO Raspberry Pi Zero 2W
```
COMPONENTE              GPIO    FUNZIONE
────────────────────────────────────────────
Display OLED SDA        GPIO 2  I2C Data
Display OLED SCL        GPIO 3  I2C Clock
PIR Sensor OUT          GPIO 4  Digital Input
Ultrasonic TRIG         GPIO 18 Digital Output
Ultrasonic ECHO         GPIO 24 Digital Input (con voltage divider)
Pulsante 1              GPIO 17 Digital Input (pull-up interno)
Pulsante 2              GPIO 27 Digital Input (pull-up interno)
LED 1 Rosso (base TR)   GPIO 22 Digital Output → Transistor
LED 1 Verde (base TR)   GPIO 23 Digital Output → Transistor
LED 2 Rosso (base TR)   GPIO 25 Digital Output → Transistor
LED 2 Verde (base TR)   GPIO 26 Digital Output → Transistor
```

### Schema Elettrico LED
```
GPIO → 1kΩ → Base NPN2222
               ↓
              Collector ← +5V_EXT
               ↓
              220Ω → LED → GND_EXT

(Emitter del transistor va a GND_EXT)

Voltage Divider HC-SR04 Echo (5V → 3.3V):
Echo_5V → 2kΩ → GPIO24 → 1kΩ → GND
```

---

## 🏗️ Architettura Software

### Stack Tecnologico
- **Backend**: Python (Flask/FastAPI)
- **Database**: SQLite
- **Frontend**: HTML/CSS/JavaScript (vanilla o framework leggero)
- **Hardware Control**: Python con RPi.GPIO, smbus (I2C)
- **Notifiche**: Pushover API (opzionale)
- **Scheduling**: APScheduler per task automatici

### Struttura Database (SQLite)

```sql
-- Utenti predefiniti
users (
    id INTEGER PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL
);

-- Coda prenotazioni
queue (
    id INTEGER PRIMARY KEY,
    user_code TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'waiting', -- 'waiting', 'active', 'completed', 'no_show'
    start_time DATETIME,
    end_time DATETIME,
    FOREIGN KEY (user_code) REFERENCES users(code)
);

-- Statistiche occupazione
occupancy_stats (
    id INTEGER PRIMARY KEY,
    start_time DATETIME NOT NULL,
    end_time DATETIME,
    access_type TEXT NOT NULL, -- 'direct', 'reservation'
    user_code TEXT,
    duration_minutes INTEGER,
    FOREIGN KEY (user_code) REFERENCES users(code)
);

-- Eventi di sistema
events (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    event_type TEXT NOT NULL,
    user_code TEXT,
    duration_minutes INTEGER,
    state_from TEXT,
    state_to TEXT,
    queue_size INTEGER,
    no_show BOOLEAN DEFAULT FALSE,
    conflict_occurred BOOLEAN DEFAULT FALSE,
    details TEXT
);

-- Configurazione sistema
config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT
);

-- Sessioni amministratore
admin_sessions (
    session_id TEXT PRIMARY KEY,
    login_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_activity DATETIME DEFAULT CURRENT_TIMESTAMP,
    ip_address TEXT,
    is_active BOOLEAN DEFAULT TRUE
);

-- Tentativi login admin
login_attempts (
    id INTEGER PRIMARY KEY,
    ip_address TEXT NOT NULL,
    attempt_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    success BOOLEAN DEFAULT FALSE,
    lockout_until DATETIME
);
```

### Configurazione Sistema (Valori Default)

```python
DEFAULT_CONFIG = {
    'reservation_timeout_minutes': 3,
    'max_occupancy_minutes': 10,
    'max_queue_size': 7,
    'conflict_priority': 'presence',  # 'presence' | 'reservation'
    'auto_reset_time': '23:59',
    'pir_absence_seconds': 30,
    'movement_timeout_minutes': 5,
    'movement_warning_minutes': 3,
    'max_static_occupancy_minutes': 30,
    'presence_threshold_cm': 200,
    'ultrasonic_polling_seconds': 2,
    'use_pir_sensor': True,
    'use_ultrasonic_sensor': True,
    'dual_sensor_mode': 'AND',  # 'AND' | 'OR'
    'warning_flash_interval_seconds': 2,
    'pushover_enabled': False,
    'pushover_user_key': '',
    'pushover_api_token': '',
    'admin_password': 'admin123',  # Password hardcoded
    'session_timeout_minutes': 30,
    'max_login_attempts': 3,
    'lockout_duration_minutes': 15
}
```

---

## 🔄 Stati del Sistema

### Macchina a Stati Principale
```
STATO                 | DESCRIZIONE
──────────────────────|────────────────────────────────────
LIBERO               | Ufficio libero, nessuna coda
OCCUPATO_DIRETTO     | Occupato tramite pulsante fisico
OCCUPATO_PRENOTATO   | Occupato tramite prenotazione web
IN_CODA              | Libero ma con prenotazioni in attesa
WARNING_TIMEOUT      | Occupato oltre tempo massimo
RISERVATO_ATTESA     | Riservato, utente ha X min per entrare
SYSTEM_ERROR         | Errore sensori/sistema
MAINTENANCE_MODE     | Modalità manutenzione admin
```

### Matrice Transizioni Stati-Azioni
```
STATO ATTUALE     | AZIONE              | NUOVO STATO         | CONDIZIONI
------------------|---------------------|--------------------|-----------------
LIBERO           | Pulsante fisico     | OCCUPATO_DIRETTO   | Sensori confermano
LIBERO           | Prenotazione web    | OCCUPATO_PRENOTATO | Coda vuota
LIBERO           | Prenotazione web    | IN_CODA            | Ufficio occupato
OCCUPATO_*       | Sensori assenza     | LIBERO/PROSSIMO    | Check coda
OCCUPATO_*       | Timer max durata    | WARNING_TIMEOUT    | Solo avviso
PRENOTATO        | Timeout 3min        | LIBERO/PROSSIMO    | No-show
IN_CODA          | Reset giornaliero   | LIBERO             | 23:59
RISERVATO_ATTESA | PIR conferma        | OCCUPATO_PRENOTATO | Entro timeout
RISERVATO_ATTESA | Timeout scaduto     | LIBERO/PROSSIMO    | No-show
```

---

## 🌐 API REST Endpoints

### Endpoint Pubblici
```
GET  /api/status              # Stato attuale ufficio + coda
POST /api/book               # Nuova prenotazione {user_code}
GET  /api/queue              # Lista coda attuale
GET  /api/users              # Lista codici utente disponibili
GET  /api/stats              # Statistiche pubbliche
```

### Endpoint Amministratore (Protetti)
```
POST /api/admin/login        # Login admin {password}
POST /api/admin/logout       # Logout admin
GET  /api/admin/status       # Verifica sessione
GET  /api/admin/config       # Configurazione sistema
POST /api/admin/config       # Aggiorna configurazione
POST /api/admin/reset        # Reset sistema completo
POST /api/admin/clear_queue  # Svuota coda
POST /api/admin/force_unlock # Forza liberazione ufficio
GET  /api/admin/events       # Log eventi dettagliato
GET  /api/admin/stats/daily  # Statistiche giornaliere
GET  /api/admin/stats/weekly # Statistiche settimanali
```

### Formato Risposte API

**GET /api/status**
```json
{
    "status": "LIBERO",
    "occupied_by": null,
    "occupation_start": null,
    "queue_size": 2,
    "queue": [
        {"position": 1, "user_code": "USER_001", "user_name": "Mario Rossi", "wait_time_minutes": 5},
        {"position": 2, "user_code": "USER_002", "user_name": "Luigi Verdi", "wait_time_minutes": 12}
    ],
    "next_user": "USER_001",
    "estimated_wait_minutes": 8,
    "sensors": {
        "pir_movement": false,
        "ultrasonic_presence": false,
        "last_movement": "2025-08-18T14:30:00Z"
    }
}
```

**POST /api/book**
```json
{
    "user_code": "USER_003"
}
```

Risposta:
```json
{
    "success": true,
    "message": "Prenotazione confermata",
    "position": 3,
    "estimated_wait_minutes": 15,
    "reservation_id": 12345
}
```

---

## 📱 Interfacce Utente

### Display OLED (128x64 pixel)

**Stato LIBERO:**
```
┌─────────────────────┐
│ UFFICIO: LIBERO     │
│ Coda: 0 persone     │
│                     │
│ Premi per entrare   │
└─────────────────────┘
```

**Stato OCCUPATO:**
```
┌─────────────────────┐
│ UFFICIO: OCCUPATO   │
│ Tempo: 05:30        │
│ Coda: 3 persone     │
│ Prossimo: USER_001  │
└─────────────────────┘
```

**Warning Movimento:**
```
┌─────────────────────┐
│ UFFICIO: OCCUPATO   │
│ Ultimo movimento:   │
│ 3 minuti fa         │
│ Muoversi per        │
│ confermare presenza │
└─────────────────────┘
```

### Interfaccia Web

**Dashboard Principale:**
- Stato ufficio in tempo reale
- Visualizzazione coda con posizioni
- Form prenotazione (dropdown codici utente)
- Statistiche basic (utilizzo giornaliero)
- Timer live per occupazione corrente

**Dashboard Amministratore:**
- Form configurazione parametri sistema
- Controlli sistema (reset, svuota coda, forza unlock)
- Statistiche avanzate (grafici utilizzo)
- Log eventi in tempo reale
- Gestione utenti (CRUD codici)

### Stati LED

```
LED 1 (Pulsante 1)    | LED 2 (Generale)     | STATO
Verde fisso           | Verde fisso          | LIBERO
Rosso fisso           | Rosso fisso          | OCCUPATO
Verde lampeggio       | Giallo lampeggio     | IN_CODA
Rosso lampeggio       | Rosso lampeggio      | WARNING/TIMEOUT
Spento                | Rosso fisso          | ERRORE SISTEMA
```

---

## 🔔 Sistema Notifiche

### Tipi Notifiche
1. **Display OLED**: Sempre attivo, info stato locale
2. **Web Dashboard**: Update real-time via WebSocket/polling
3. **Pushover** (opzionale): Notifiche push su smartphone

### Eventi Notificati
- Prenotazione confermata
- Il tuo turno è arrivato
- Warning tempo scaduto
- Sistema in errore
- Reset giornaliero

### Formato Notifiche Pushover
```python
notification_templates = {
    'reservation_confirmed': "✅ Prenotazione confermata! Posizione in coda: {position}. Attesa stimata: {wait_time} min",
    'your_turn': "🚪 È il tuo turno! Hai {timeout} min per entrare nell'ufficio",
    'no_show': "⚠️ Prenotazione scaduta. Non ti sei presentato entro il tempo limite",
    'queue_cleared': "🔄 Coda svuotata dall'amministratore",
    'system_error': "❌ Sistema in errore. Contattare assistenza"
}
```

---

## 🎯 Logiche di Business Critiche

### Gestione Conflitti
```python
def handle_button_press():
    if current_state == "OCCUPATO_PRENOTATO":
        if config['conflict_priority'] == 'presence':
            # Presenza fisica ha priorità
            cancel_current_reservation()
            set_state("OCCUPATO_DIRETTO")
            notify_cancelled_user()
        else:
            # Prenotazione ha priorità
            show_display_message("RISERVATO - Attendere liberazione")
            flash_led_warning()
    
    elif current_state == "IN_CODA":
        if config['conflict_priority'] == 'presence':
            # Bypassa coda
            set_state("OCCUPATO_DIRETTO")
        else:
            # Rispetta coda
            show_display_message("CODA ATTIVA - Prenotare online")
```

### Logica Sensori Combinata
```python
def update_occupancy_sensors():
    pir_movement = read_pir_sensor()
    ultrasonic_distance = read_ultrasonic_sensor()
    presence_detected = ultrasonic_distance < config['presence_threshold_cm']
    
    if pir_movement:
        last_movement_time = now()
        confirmed_human_presence = True
    
    # Logica combinata
    if config['dual_sensor_mode'] == 'AND':
        # Entrambi devono confermare
        occupancy = presence_detected and (
            confirmed_human_presence or 
            time_since_last_movement() < config['movement_timeout_minutes']
        )
    else:  # 'OR'
        # Almeno uno deve confermare
        occupancy = presence_detected or (
            time_since_last_movement() < config['movement_timeout_minutes']
        )
    
    return occupancy
```

### Gestione Coda
```python
def process_queue():
    if current_state in ["LIBERO", "RISERVATO_ATTESA"]:
        next_reservation = get_next_in_queue()
        if next_reservation:
            set_state("RISERVATO_ATTESA")
            start_reservation_timer(config['reservation_timeout_minutes'])
            send_notification(next_reservation.user_code, 'your_turn')
            update_display_reservation(next_reservation)
```

---

## 📊 Analisi e Statistiche

### Metriche Raccolte
- Tempo medio di occupazione
- Numero accessi giornalieri/settimanali
- Rapporto accessi diretti vs prenotazioni
- Tasso di no-show
- Ore di picco utilizzo
- Efficienza sistema (tempo attesa vs utilizzo)

### Dashboard Statistiche
- Grafici utilizzo temporale
- Heatmap orari di picco
- KPI principali (utilizzo %, soddisfazione utenti)
- Trend settimanali/mensili
- Alert automatici per anomalie

---

## 🚀 Task di Implementazione

### Fase 1: Setup Base
1. Configurazione Raspberry Pi Zero 2W
2. Test hardware sensori e display
3. Implementazione driver sensori
4. Setup database SQLite
5. API REST base

### Fase 2: Logica Core
1. Macchina a stati sistema
2. Gestione sensori combinata
3. Sistema coda e prenotazioni
4. Interface OLED dinamica
5. Controllo LED

### Fase 3: Interface Web
1. Dashboard utente frontend
2. WebSocket real-time updates
3. Form prenotazioni
4. Dashboard admin protetto
5. Responsive design

### Fase 4: Features Avanzate
1. Sistema notifiche Pushover
2. Statistiche e analytics
3. Configurazione dinamica
4. Logging avanzato
5. Error handling robusto

### Fase 5: Deploy e Test
1. Containerizzazione (Docker)
2. Script avvio automatico
3. Backup automatico database
4. Monitoring sistema
5. Documentazione utente

---

## 🛠️ Considerazioni Tecniche

### Librerie Python Richieste
```
Flask/FastAPI          # Web framework
RPi.GPIO               # GPIO control
smbus/smbus2           # I2C communication  
luma.oled              # OLED display control
SQLite3                # Database
APScheduler            # Task scheduling
requests               # HTTP client per Pushover
websockets/socketio    # Real-time updates
```

### Performance e Reliability
- Polling sensori ogni 500ms
- Debounce pulsanti (50ms)
- Timeout connessioni web (5s)
- Retry automatico operazioni critiche
- Backup database giornaliero
- Watchdog per restart automatico

### Sicurezza
- Password admin hardcoded (temporanea)
- Rate limiting API (5 req/min per IP)
- Session timeout (30 min)
- Escape input SQL injection
- HTTPS per produzione (certificato self-signed)

---

## 📝 Note di Sviluppo

### Debugging e Test
- Log rotativi con livelli (DEBUG, INFO, WARNING, ERROR)
- Modalità simulazione sensori per test
- Unit test per logiche critiche
- API test con Postman/curl
- Mock hardware per sviluppo senza Pi

### Deployment
- Script install.sh per setup automatico
- Systemd service per avvio automatico
- Configurazione WiFi headless
- SSH abilitato per manutenzione remota
- Backup configurazione su USB/cloud

---

*Documento creato il 18/08/2025 - Versione 1.0*
*Per domande o chiarimenti contattare il team di sviluppo*