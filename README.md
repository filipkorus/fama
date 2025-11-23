# Post-Quantum Cryptography Project

Platforma bezpiecznej wymiany wiadomości (Real-time) przygotowana pod implementację algorytmów postkwantowych. Architektura mikroserwisowa oparta o WebSocket.

## Architektura

**Stack:**
*   **Frontend:** React 18 (TS), Vite, Socket.IO Client
*   **Backend:** Python Flask, Flask-SocketIO (Eventlet)
*   **Baza:** PostgreSQL 15
*   **Infra:** Docker Compose, Nginx (Reverse Proxy)

**Komunikacja:**
Klient łączy się przez Nginx (port 8080). Ruch HTTP trafia do Reacta, WebSocket do Flaska. Baza danych dostępna tylko dla backendu wewnątrz sieci Dockera.

## Wymagania

*   Docker + Docker Compose
*   Git
*   (Dev) Node.js 20+, Python 3.11+

## Uruchomienie

```bash
# 1. Klonowanie
git clone https://github.com/filipkorus/fama.git
cd fama

# 2. Konfiguracja (Linux/Mac)
cp .env.example .env
# (Windows: copy .env.example .env)

# 3. Start
docker compose up -d --build
```

App: `http://localhost:8080`
Adminer (DB): `http://localhost:8080/adminer/`

## Development (Hybrid)

Baza w Dockerze, aplikacja lokalnie (szybszy reload).

**1. Baza danych**
```bash
./start-dev.sh  # lub start-dev.ps1
```

**2. Backend**
```bash
cd backend
pip install -r requirements.txt
python run.py
```
Serwer: `http://localhost:5000`

**3. Frontend**
```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```
Serwer: `http://localhost:5173`

## Konfiguracja (.env)

Pełna lista zmiennych konfiguracyjnych. Plik `.env` jest wymagany do uruchomienia `docker compose`.

### Baza danych (PostgreSQL)
| Zmienna | Domyślnie | Opis |
| --- | --- | --- |
| `POSTGRES_USER` | `postgres` | Nazwa użytkownika (superuser) |
| `POSTGRES_PASSWORD` | `postgres` | Hasło do bazy danych |
| `POSTGRES_DB` | `cryptography_db` | Nazwa tworzonej bazy danych |
| `POSTGRES_PORT` | `5432` | Port wewnętrzny kontenera bazy |

### Backend (Flask)
| Zmienna | Przykład | Opis |
| --- | --- | --- |
| `BACKEND_PORT` | `5000` | Port, na którym nasłuchuje Flask (w kontenerze) |
| `FLASK_DEBUG` | `False` | Tryb debugowania (przeładowanie kodu, stacktrace) |
| `SECRET_KEY` | `your-secret` | Sól kryptograficzna dla sesji i tokenów (wymagana zmiana na prod) |
| `CORS_ORIGINS` | `*` | Lista domen dozwolonych w polityce CORS |

### Frontend & Proxy
| Zmienna | Przykład | Opis |
| --- | --- | --- |
| `FRONTEND_PORT` | `3000` | Port wewnętrzny serwera plików statycznych/dev |
| `VITE_API_URL` | `http://localhost:8080` | Adres API widziany przez przeglądarkę klienta |
| `NGINX_PORT` | `8080` | Główny port publiczny aplikacji (entrypoint) |

## Testy

**Docker (zalecane)**
```bash
# Full suite (Back+Front) z raportem coverage
./test.sh  # lub test.ps1

# Manualnie - wybrany serwis
docker compose -f docker-compose.test.yml up backend-test
docker compose -f docker-compose.test.yml up frontend-test
```

**Local (bez konteneryzacji)**
*   **Backend:** `pytest --cov=.` (uruchamiać w folderze `backend`)
*   **Frontend:** `npm run test:coverage` (uruchamiać w folderze `frontend`)

## Administracja

```bash
# Podgląd logów (wszystkie serwisy)
docker compose logs -f

# Interaktywny shell bazy danych
docker compose exec db psql -U postgres -d cryptography_db

# Pełny backup bazy do pliku SQL
docker compose exec db pg_dump -U postgres cryptography_db > dump.sql

# Reset środowiska (z usunięciem wolumenów danych!)
docker compose down -v
```
