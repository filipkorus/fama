# Post-Quantum Cryptography Project (Kryptografia Postkwantowa)

Projekt na przedmiot Kryptografia Postkwantowa.

## Spis treści

- [Architektura](#architektura)
- [Technologie](#technologie)
- [Wymagania](#wymagania)
- [Instalacja i uruchomienie](#instalacja-i-uruchomienie)
- [Konfiguracja](#konfiguracja)
- [Testy](#testy)
- [Struktura projektu](#struktura-projektu)
- [Funkcjonalności](#funkcjonalności)
- [Rozwój projektu](#rozwój-projektu)

## Architektura

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
- Minimalistyczny WebSocket server
- Rejestracja użytkowników
- Routing wiadomości (broadcast i private)
- Custom React hook do WebSocket
- Testy jednostkowe (backend + frontend)
- Gotowe do rozbudowy o algorytmy kryptografii postkwantowej

## Technologie

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

## Wymagania

- Docker Desktop (Windows/Mac) lub Docker Engine + Docker Compose (Linux)
- Git
- (Opcjonalnie) Node.js 20+ i Python 3.11+ dla lokalnego developmentu

## Instalacja i uruchomienie

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

Plik `.env` można edytować w razie potrzeby.

### 3. Uruchomienie aplikacji

```bash
# Budowanie i uruchomienie wszystkich serwisów
docker compose up --build

# W tle (detached mode)
docker compose up -d --build
```

Aplikacja będzie dostępna pod adresem: **http://localhost:8080**

Adminer (DB GUI) będzie dostępny przez nginx pod adresem: `http://localhost:{NGINX_PORT}/adminer/`.

### 4. Zatrzymanie aplikacji

```bash
# Zatrzymanie serwisów
docker compose down

# Zatrzymanie z usunięciem wolumenów (bazy danych)
docker compose down -v
```

## Konfiguracja

Konfiguracja systemu odbywa się poprzez plik `.env`:

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

## Testy

### Szybkie uruchomienie testów

#### Windows PowerShell

```powershell
.\test.ps1
```

#### Linux/Mac

```bash
./test.sh
```

Skrypty wykonują następujące operacje:

1. Przebudowa kontenerów testowych (`--no-cache`)
2. Uruchomienie testów backendu i frontendu
3. Wyświetlenie wyników coverage
4. Czyszczenie kontenerów

### Uruchamianie testów ręcznie w Dockerze

```bash
# Rebuild i uruchomienie wszystkich testów
docker compose -f docker-compose.test.yml build
docker compose -f docker-compose.test.yml up

# Tylko backend
docker compose -f docker-compose.test.yml up backend-test

# Tylko frontend
docker compose -f docker-compose.test.yml up frontend-test

# Czyszczenie
docker compose -f docker-compose.test.yml down
```

### Testy lokalne (bez Dockera)

Testy można również uruchomić bezpośrednio na lokalnym systemie:

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

### Lokalne uruchomienie (development bez Dockera)

Dla szybszego hot reload i debugowania dostępna jest opcja uruchomienia tylko bazy danych w Dockerze, przy jednoczesnym lokalnym uruchomieniu backendu i frontendu.

#### 1. Uruchom bazę danych

```bash
# Tylko PostgreSQL w Docker
./start-dev.ps1   # Windows
./start-dev.sh    # Linux/Mac

# Sprawdź status
docker compose -f docker-compose.dev.yml ps
```

#### 2. Backend lokalnie

```bash
cd backend

# Zainstaluj zależności
pip install -r requirements.txt

# Skopiuj i edytuj .env
cp .env.example .env

# Uruchom aplikację
python run.py
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

#### Zatrzymanie

```bash
# Zatrzymaj bazę danych
docker compose -f docker-compose.dev.yml down

# Backend i frontend - Ctrl+C w terminalach
```

## Przydatne komendy

### Docker

```bash
# Restart wszystkich serwisów
docker compose restart

# Logi z konkretnego serwisu
docker compose logs -f backend
docker compose logs -f frontend

# Wejście do kontenera
docker compose exec backend bash
docker compose exec db psql -U postgres -d cryptography_db

# Czyszczenie wszystkiego
docker compose down -v --rmi all
docker system prune -a
```

### Baza danych

```bash
# Backup bazy
docker compose exec db pg_dump -U postgres cryptography_db > backup.sql

# Restore bazy
cat backup.sql | docker compose exec -T db psql -U postgres cryptography_db
```
