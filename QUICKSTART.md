# 🚀 Quick Start Guide

## Szybkie uruchomienie projektu

### Windows (PowerShell)

```powershell
# 1. Uruchom aplikację
.\start.ps1

# 2. Otwórz przeglądarkę
# http://localhost:8080

# 3. Zatrzymaj aplikację (w innym terminalu)
.\stop.ps1

# 4. Uruchom testy
.\test.ps1
```

### Linux/Mac (Bash)

```bash
# Najpierw nadaj uprawnienia do wykonywania
chmod +x start.sh stop.sh test.sh start-dev.sh

# 1. Uruchom aplikację
./start.sh

# 2. Otwórz przeglądarkę
# http://localhost:8080

# 3. Zatrzymaj aplikację (w innym terminalu)
./stop.sh

# 4. Uruchom testy
./test.sh
```

## Alternatywne uruchomienie (Docker Compose)

```bash
# Uruchomienie w trybie detached (w tle)
docker-compose up -d --build

# Sprawdzenie logów
docker-compose logs -f

# Zatrzymanie
docker-compose down

# Zatrzymanie z usunięciem danych
docker-compose down -v
```

## Pierwsze kroki w aplikacji

1. **Otwórz aplikację**: http://localhost:8080
2. **Stwórz użytkownika**: Wpisz nazwę użytkownika i kliknij "Create User"
3. **Wyślij wiadomość**: Wpisz wiadomość i kliknij "Send Message"
4. **Testuj szyfrowanie**: 
   - Zaznacz checkbox "Encrypt message"
   - Lub użyj przycisku "Test Encrypt"

## Dostęp do serwisów

- **Aplikacja główna**: http://localhost:8080
- **Frontend bezpośrednio**: http://localhost:3000
- **Backend API**: http://localhost:5000/api/health
- **PostgreSQL**: localhost:5432

## Częste problemy

### Port jest zajęty
Zmień port w pliku `.env`:
```env
NGINX_PORT=8081
```

### Baza danych nie działa
Sprawdź status kontenera:
```bash
docker-compose ps
docker-compose logs db
```

### Frontend nie łączy się z backendem
Sprawdź czy wszystkie kontenery działają:
```bash
docker-compose ps
```

## 🔧 Lokalne uruchomienie (Development)

Jeśli wolisz uruchamiać backend i frontend lokalnie (szybszy development):

### 1. Uruchom tylko bazę danych

```bash
docker-compose -f docker-compose.dev.yml up -d
```

### 2. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

pip install -r requirements.txt

# Windows PowerShell
$env:DATABASE_URL="postgresql://postgres:postgres@localhost:5432/cryptography_db"
$env:FLASK_DEBUG="True"

python app.py
```

Backend na: http://localhost:5000

### 3. Frontend

```bash
cd frontend
npm install

# Stwórz .env.local
echo "VITE_API_URL=http://localhost:5000" > .env.local

npm run dev
```

Frontend na: http://localhost:3000

## Następne kroki

Przeczytaj pełną dokumentację w [README.md](README.md)
