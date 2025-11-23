# Quick Start Guide

Przewodnik szybkiego uruchomienia i obsługi projektu.

## Szybkie uruchomienie

### Windows (PowerShell)

```powershell
# 1. Uruchomienie aplikacji
.\start.ps1

# 2. Zatrzymanie aplikacji
.\stop.ps1

# 3. Uruchomienie testów
.\test.ps1
```

### Linux / macOS (Bash)

Wymagane nadanie uprawnień wykonywania (`chmod +x *.sh`).

```bash
# 1. Uruchomienie aplikacji
./start.sh

# 2. Zatrzymanie aplikacji
./stop.sh

# 3. Uruchomienie testów
./test.sh
```

### Docker Compose (Manualnie)

Uruchomienie bez skryptów pomocniczych.

```bash
# Start w tle
docker compose up -d --build

# Logi kontenerów
docker compose logs -f

# Zatrzymanie
docker compose down -v
```

## Obsługa aplikacji

### Pierwsze kroki

1.  **Dostęp:** Otwórz przeglądarkę pod adresem `http://localhost:8080`.
2.  **Użytkownik:** W panelu bocznym wprowadź nazwę i użyj przycisku "Create User".
3.  **Wiadomości:** Wpisz tekst w polu wejściowym i zatwierdź przyciskiem "Send Message".
4.  **Szyfrowanie:**
    *   Zaznacz opcję "Encrypt message".
    *   Użyj "Test Encrypt" dla podglądu działania algorytmu.

### Dostępne serwisy

| Usługa | Adres | Opis |
| --- | --- | --- |
| **Główny interfejs** | `http://localhost:8080` | Nginx Proxy (App + WebSocket) |
| **Frontend (Dev)** | `http://localhost:3000` | Serwer deweloperski React |
| **Backend API** | `http://localhost:5000` | Bezpośredni dostęp do Flask |
| **PostgreSQL** | `localhost:5432` | Port bazy danych |

## Rozwiązywanie problemów

### Konflikt portów
Błąd: `Bind for 0.0.0.0:8080 failed`.
Rozwiązanie: Zmiana portu w pliku `.env`:
```env
NGINX_PORT=8081
```

### Problemy z bazą danych
Błąd połączenia lub startu kontenera `db`.
Diagnostyka:
```bash
docker compose logs db
```
Najczęstsza przyczyna: lokalna instancja PostgreSQL zajmuje port 5432. Należy ją zatrzymać lub zmienić mapowanie portów w `.env`.

### Brak komunikacji Frontend-Backend
Objaw: Błędy WebSocket / API w konsoli przeglądarki.
Weryfikacja stanu kontenerów:
```bash
docker compose ps
```
Wymagany status `Up` dla serwisów `backend` i `frontend`.

## Development lokalny

Uruchomienie komponentów bez pełnej konteneryzacji (oprócz bazy danych).

**1. Baza danych (Docker)**
```bash
docker compose -f docker-compose.dev.yml up -d
```

**2. Backend**
```bash
cd backend
# Konfiguracja środowiska
# Windows: $env:FLASK_DEBUG="True"
# Linux: export FLASK_DEBUG="True"
pip install -r requirements.txt
python run.py
```
Adres: `http://localhost:5000`

**3. Frontend**
```bash
cd frontend
npm install
# Utworzenie pliku .env.local z VITE_API_URL=http://localhost:5000
npm run dev
```
Adres: `http://localhost:3000`

## Dokumentacja
Szczegóły architektury i konfiguracji dostępne w pliku [README.md](README.md).
