# Queue Manager System

Sistema di gestione coda per ufficio con supporto fisico (Raspberry Pi) e interfaccia web.

## 🎯 Panoramica

Questo sistema permette di gestire l'accesso ad un ufficio attraverso:
- **Accesso diretto**: tramite pulsante fisico se l'ufficio è libero
- **Sistema prenotazioni**: interfaccia web per prenotare un posto in coda
- **Rilevamento presenza**: sensori PIR e ultrasonico per confermare occupazione
- **Dashboard amministrativa**: controllo completo del sistema
- **Notifiche**: aggiornamenti in tempo reale via web e opzionalmente Pushover

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

### Interfaccia Web
- **Dashboard Utente**: `http://raspberry-pi-ip:5000`
- **Dashboard Admin**: `http://raspberry-pi-ip:5000/admin`

### API REST
- `GET /api/status` - Stato attuale sistema
- `POST /api/book` - Nuova prenotazione
- `GET /api/queue` - Visualizza coda
- Vedi [API Documentation](docs/api.md) per dettagli completi

## 📱 Interfacce

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

### Test
```bash
# Test unitari
python -m pytest test/

# Test integrazione hardware
python test/hardware_integration.py
```

## 📝 Licenza

MIT License - vedi file [LICENSE](LICENSE) per dettagli.

## 🤝 Contribuire

1. Fork del progetto
2. Crea feature branch (`git checkout -b feature/NuovaFunzionalita`)
3. Commit modifiche (`git commit -m 'Aggiungi nuova funzionalità'`)
4. Push al branch (`git push origin feature/NuovaFunzionalita`)
5. Apri Pull Request

## 📞 Supporto

Per domande o problemi, apri una issue su GitHub o contatta il team di sviluppo.

---

*Progetto sviluppato per la gestione efficiente di accessi ad uffici singoli*
