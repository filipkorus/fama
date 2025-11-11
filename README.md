# 🔐 Post-Quantum Cryptography Project (Kryptografia Postkwantowa)

Projekt na przedmiot Kryptografia Postkwantowa.

## 📋 Spis treści

- [Architektura](#architektura)
- [Technologie](#technologie)
- [Wymagania](#wymagania)
- [Instalacja i uruchomienie](#instalacja-i-uruchomienie)
- [Konfiguracja](#konfiguracja)
- [Testy](#testy)
- [Struktura projektu](#struktura-projektu)
- [Funkcjonalności](#funkcjonalności)
- [Rozwój projektu](#rozwój-projektu)

## 🏗️ Architektura

Projekt składa się z następujących komponentów:

```
┌─────────────┐
│   Nginx     │  ← Reverse Proxy (port 8080)
└──────┬──────┘
       │
    ┌──┴───────────────────┐
    │                      │
┌───▼────┐          ┌──────▼─────┐
│Frontend│          │  Backend   │
│React+TS│◄────────►│   Flask    │
│(port   │ WebSocket│(port 5000) │
│ 3000)  │Socket.IO │            │
└────────┘          └──────┬─────┘
                           │
                    ┌──────▼──────┐
                    │ PostgreSQL  │
                    │ (port 5432) │
                    └─────────────┘
```

**Aktualna implementacja:**
- ✅ Minimalistyczny WebSocket server
- ✅ Rejestracja użytkowników
- ✅ Routing wiadomości (broadcast i private)
- ✅ Custom React hook do WebSocket
- ✅ Testy jednostkowe (backend + frontend)
- 🔨 Gotowe do rozbudowy o algorytmy kryptografii postkwantowej

## 🛠️ Technologie

### Backend

- **Flask 3.0.0** - Lekki framework webowy
- **Flask-SocketIO 5.3.5** - Komunikacja WebSocket w czasie rzeczywistym
- **eventlet 0.33.3** - Asynchroniczny worker dla WebSocket
- **pytest 7.4.3** - Framework do testowania

### Frontend

- **React 18.2.0** - Biblioteka UI
- **TypeScript 5.2.2** - Typowany JavaScript
- **Vite 5.0.0** - Szybki build tool
- **Socket.IO Client 4.6.0** - Klient WebSocket
- **Vitest 1.0.0** - Framework do testowania

### Infrastructure

- **Docker** & **Docker Compose** - Konteneryzacja
- **Nginx** - Reverse proxy
- **PostgreSQL 15** - Baza danych (gotowa do użycia, obecnie nieaktywna)

## ✅ Wymagania

- Docker Desktop (Windows/Mac) lub Docker Engine + Docker Compose (Linux)
- Git
- (Opcjonalnie) Node.js 20+ i Python 3.11+ dla lokalnego developmentu

## 🚀 Instalacja i uruchomienie

### 1. Klonowanie repozytorium

```bash
git clone https://github.com/filipkorus/fama.git
cd fama
```

### 2. Konfiguracja środowiska

Skopiuj przykładowy plik konfiguracyjny:

```bash
# Windows PowerShell
Copy-Item .env.example .env

# Linux/Mac
cp .env.example .env
```

Edytuj plik `.env` według potrzeb (opcjonalnie).

### 3. Uruchomienie aplikacji

```bash
# Budowanie i uruchomienie wszystkich serwisów
docker-compose up --build

# W tle (detached mode)
docker-compose up -d --build
```

Aplikacja będzie dostępna pod adresem: **http://localhost:8080**

### 4. Zatrzymanie aplikacji

```bash
# Zatrzymanie serwisów
docker-compose down

# Zatrzymanie z usunięciem wolumenów (bazy danych)
docker-compose down -v
```

## ⚙️ Konfiguracja

Wszystkie ustawienia można skonfigurować poprzez plik `.env`:

### PostgreSQL
```env
POSTGRES_USER=postgres          # Użytkownik bazy danych
POSTGRES_PASSWORD=postgres      # Hasło do bazy
POSTGRES_DB=cryptography_db     # Nazwa bazy danych
POSTGRES_PORT=5432             # Port PostgreSQL
```

### Backend (Flask)
```env
BACKEND_PORT=5000              # Port backendu
FLASK_DEBUG=False              # Tryb debug
SECRET_KEY=your-secret-key     # Klucz sesji (ZMIEŃ W PRODUKCJI!)
CORS_ORIGINS=*                 # Dozwolone originy CORS
```

### Frontend (React)
```env
FRONTEND_PORT=3000             # Port frontendu
VITE_API_URL=http://localhost:8080  # URL backendu
```

### Nginx
```env
NGINX_PORT=8080                # Port reverse proxy
```

## 🧪 Testy

### Szybkie uruchomienie testów

#### Windows PowerShell

```powershell
.\test.ps1
```

#### Linux/Mac

```bash
./test.sh
```

Skrypty automatycznie:

1. Przebudowują kontenery testowe (`--no-cache`)
2. Uruchamiają testy backendu i frontendu jednocześnie
3. Wyświetlają wyniki coverage w terminalu
4. Czyszczą kontenery po zakończeniu

### Uruchamianie testów ręcznie w Dockerze

```bash
# Rebuild i uruchomienie wszystkich testów
docker-compose -f docker-compose.test.yml build --no-cache
docker-compose -f docker-compose.test.yml up

# Tylko backend
docker-compose -f docker-compose.test.yml up backend-test

# Tylko frontend
docker-compose -f docker-compose.test.yml up frontend-test

# Czyszczenie
docker-compose -f docker-compose.test.yml down
```

### Testy lokalne (bez Dockera)

Możesz też uruchomić testy bezpośrednio na swoim systemie:

#### Backend (Python)

```bash
cd backend

# Instalacja zależności
pip install -r requirements.txt

# Uruchomienie testów
pytest

# Z coverage w terminalu
pytest --cov=. --cov-report=term-missing
```

#### Frontend (TypeScript)

```bash
cd frontend

# Instalacja zależności
npm install

# Uruchomienie testów
npm test

# Z coverage
npm run test:coverage

# UI interaktywne
npm run test:ui
```

## 📁 Struktura projektu

```text
fama/
├── backend/                    # Backend Flask
│   ├── app.py                 # Główna aplikacja (WebSocket server)
│   ├── config.py              # Konfiguracja (nieużywana obecnie)
│   ├── models.py              # Modele SQLAlchemy (nieużywane obecnie)
│   ├── database.py            # Połączenie z bazą (nieużywane obecnie)
│   ├── requirements.txt       # Zależności Python
│   ├── Dockerfile             # Dockerfile backendu
│   ├── pytest.ini             # Konfiguracja pytest
│   └── tests/                 # Testy backendu (6 testów)
│       ├── conftest.py        # Fixtures testowe
│       ├── test_api.py        # Testy REST API (2 testy)
│       └── test_socketio.py   # Testy Socket.IO (4 testy)
│
├── frontend/                   # Frontend React
│   ├── src/
│   │   ├── App.tsx            # Główny komponent (UI rejestracji + czat)
│   │   ├── main.tsx           # Entry point
│   │   ├── hooks/
│   │   │   └── useWebSocket.ts # Custom hook do WebSocket
│   │   ├── services/
│   │   │   ├── api.ts         # REST API service
│   │   │   └── socket.ts      # Socket.IO connection
│   │   └── tests/             # Testy frontendu (15 testów)
│   │       ├── App.test.tsx
│   │       ├── useWebSocket.test.ts
│   │       ├── api.test.ts
│   │       └── setup.ts
│   ├── package.json           # Zależności Node.js
│   ├── vite.config.ts         # Konfiguracja Vite
│   ├── vitest.config.ts       # Konfiguracja Vitest
│   ├── Dockerfile             # Dockerfile produkcyjny
│   └── Dockerfile.test        # Dockerfile testowy
│
├── nginx/                      # Konfiguracja Nginx
│   ├── nginx.conf             # Główna konfiguracja
│   └── conf.d/
│       └── default.conf       # Routing reverse proxy
│
├── docker-compose.yml          # Compose główny (wszystkie serwisy)
├── docker-compose.dev.yml      # Compose dev (tylko baza danych)
├── docker-compose.test.yml     # Compose testowy
├── start.ps1 / start.sh       # Skrypty uruchomienia aplikacji
├── start-dev.ps1 / start-dev.sh # Skrypty uruchomienia bazy dev
├── stop.ps1 / stop.sh         # Skrypty zatrzymania
├── test.ps1 / test.sh         # Skrypty testów
├── .env.example               # Przykładowa konfiguracja (Docker)
├── backend/.env.example       # Przykładowa konfiguracja (backend lokalnie)
├── frontend/.env.example      # Przykładowa konfiguracja (frontend lokalnie)
└── README.md                  # Ta dokumentacja
```

## 🎯 Funkcjonalności

### Aktualne (zaimplementowane)

#### Backend

- ✅ **WebSocket Server** - Flask-SocketIO
- ✅ **Health Check API** - `/api/health` endpoint
- ✅ **Rejestracja użytkowników** - event `register`
- ✅ **Routing wiadomości**:
  - Broadcast (do wszystkich)
  - Private messages (do konkretnego użytkownika przez `to` parameter)
- ✅ **Tracking połączonych użytkowników** - `connected_users` dict
- ✅ **Testy jednostkowe** - 6 testów z pytest

#### Frontend

- ✅ **Custom WebSocket Hook** - `useWebSocket.ts`
- ✅ **Dwuetapowy UI**:
  1. Ekran rejestracji (wprowadź username)
  2. Ekran czatu (wysyłanie wiadomości)
- ✅ **Obsługa wiadomości** - broadcast i private
- ✅ **Status połączenia** - real-time
- ✅ **Testy jednostkowe** - 15 testów z Vitest

### Planowane do implementacji

- 🔨 **Algorytmy kryptografii postkwantowej**:
  - Kyber (szyfrowanie)
  - Dilithium (podpisy cyfrowe)
  - SPHINCS+ (podpisy cyfrowe)
- 🔨 **Zarządzanie kluczami** - generowanie, przechowywanie, wymiana
- 🔨 **Szyfrowanie end-to-end** - szyfrowanie wiadomości przed wysłaniem
- 🔨 **Weryfikacja podpisów** - autentykacja nadawcy
- 🔨 **Historia wiadomości** - zapis do bazy danych
- 🔨 **UI do zarządzania kryptografią** - panel wyboru algorytmu

## 📚 API Documentation

### REST API Endpoints

#### Health Check

```http
GET /api/health
```

Sprawdza status backendu i liczbę połączonych użytkowników.

**Response:**

```json
{
  "status": "healthy",
  "connected_users": 2
}
```

### WebSocket Events (Socket.IO)

#### Connect

```javascript
// Automatyczne przy połączeniu
socket.on('connect', () => {
  console.log('Connected to server')
})
```

#### Disconnect

```javascript
socket.on('disconnect', () => {
  console.log('Disconnected from server')
})
```

#### Register User

**Emit:**

```javascript
socket.emit('register', { username: 'jan_kowalski' })
```

**Receive:**

```javascript
socket.on('registered', ({ username, session_id }) => {
  console.log(`Registered as ${username}`)
})
```

#### Send Message (Broadcast)

```javascript
socket.emit('message', {
  username: 'jan_kowalski',
  message: 'Hello everyone!'
})
```

#### Send Private Message

```javascript
socket.emit('message', {
  username: 'jan_kowalski',
  message: 'Private message',
  to: 'anna_nowak'  // username odbiorcy
})
```

#### Receive Message

```javascript
socket.on('message', (data) => {
  // data może być stringiem lub obiektem:
  // String: "jan_kowalski: Hello!"
  // Object: { username: 'jan_kowalski', message: 'Hello!', to: 'you' }
  console.log('New message:', data)
})
```

## 🔧 Rozwój projektu

### Struktura plików `.env`

Projekt używa różnych plików `.env` dla różnych środowisk:

| Plik | Używany przez | Kiedy używać |
|------|---------------|--------------|
| `/.env` | Docker Compose | Uruchamianie w Dockerze (`./start.ps1`) |
| `/backend/.env` | Backend lokalnie | Development backendu bez Dockera |
| `/frontend/.env.local` | Frontend lokalnie | Development frontendu bez Dockera |

**Przykład:** Jeśli pracujesz nad frontendem lokalnie (`npm run dev`) i backendem w Dockerze:

- Frontend użyje `/frontend/.env.local` → `VITE_API_URL=http://localhost:5000`
- Backend w Dockerze użyje `/.env`

### Lokalne uruchomienie (development bez Dockera)

Jeśli chcesz szybszy hot reload i debugowanie, możesz uruchomić tylko bazę danych w Dockerze, a backend i frontend lokalnie.

#### 1. Uruchom bazę danych

```bash
# Tylko PostgreSQL w Docker
./start-dev.ps1   # Windows
./start-dev.sh    # Linux/Mac

# Sprawdź status
docker-compose -f docker-compose.dev.yml ps
```

#### 2. Backend lokalnie

```bash
cd backend

# Zainstaluj zależności
pip install -r requirements.txt

# Skopiuj i edytuj .env
cp .env.example .env

# Uruchom aplikację
python app.py
```

Backend dostępny: <http://localhost:5000>

#### 3. Frontend lokalnie

```bash
cd frontend

# Zainstaluj zależności
npm install

# Skopiuj i edytuj .env.local
cp .env.local.example .env.local

# Uruchom dev server
npm run dev
```

Frontend dostępny: <http://localhost:5173>

**Zalety developmentu lokalnego:**

- ✅ Szybszy hot reload
- ✅ Łatwiejsze debugowanie (breakpointy, logging)
- ✅ Bezpośredni dostęp do kodu
- ✅ Szybsze iteracje developmentu
- ✅ Niższe zużycie zasobów

#### Zatrzymanie

```bash
# Zatrzymaj bazę danych
docker-compose -f docker-compose.dev.yml down

# Backend i frontend - Ctrl+C w terminalach
```

## 📝 Przydatne komendy

### Docker

```bash
# Restart wszystkich serwisów
docker-compose restart

# Logi z konkretnego serwisu
docker-compose logs -f backend
docker-compose logs -f frontend

# Wejście do kontenera
docker-compose exec backend bash
docker-compose exec db psql -U postgres -d cryptography_db

# Czyszczenie wszystkiego
docker-compose down -v --rmi all
docker system prune -a
```

### Baza danych

```bash
# Backup bazy
docker-compose exec db pg_dump -U postgres cryptography_db > backup.sql

# Restore bazy
cat backup.sql | docker-compose exec -T db psql -U postgres cryptography_db
```
