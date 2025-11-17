# 🚀 Deployment - Instrukcja wdrożenia do produkcji

## 📋 Które pliki `.env` modyfikować?

Stwórz plik `.env` w **głównym katalogu projektu** (obok `docker-compose.yml`)

```
fama/
├── .env              ← Stwórz ten plik dla produkcji
├── .env.example      ← Szablon (NIE edytuj, służy jako przykład)
├── docker-compose.yml
├── backend/
├── frontend/
└── ...
```

---

## 📝 Kompletny plik `.env` dla produkcji

**Skopiuj i dostosuj** (wszystkie wartości w `<...>` MUSISZ zmienić):

```bash
# PostgreSQL Configuration
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<ZMIEŃ-NA-SILNE-HASŁO-16+-znaków>
POSTGRES_DB=cryptography_production
POSTGRES_PORT=5432

# Backend Configuration
BACKEND_PORT=5000
FLASK_DEBUG=False
FLASK_TESTING=False
SECRET_KEY=<WYGENERUJ-32-ZNAKOWY-KLUCZ>

# JWT Configuration
JWT_SECRET_KEY=<WYGENERUJ-32-ZNAKOWY-KLUCZ>
JWT_ACCESS_TOKEN_EXPIRES=3600
JWT_REFRESH_TOKEN_EXPIRES=2592000
JWT_COOKIE_SECURE=True
VALIDATE_PASSWORD_STRENGTH=True

# Nginx Configuration
NGINX_PORT=443

# CORS Configuration
CORS_ORIGINS=https://fama.fkor.us

# SocketIO configuration
SOCKETIO_MESSAGE_QUEUE=
```

---

## 🔑 Jak wygenerować bezpieczne klucze?

### SECRET_KEY i JWT_SECRET_KEY

**Opcja 1: OpenSSL (Linux/Mac/Git Bash/WSL)**

```bash
openssl rand -base64 32
```

**Opcja 2: Python**

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Opcja 3: PowerShell (Windows)**

```powershell
-join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | % {[char]$_})
```

**Przykładowe wygenerowane klucze (NIE UŻYWAJ TYCH!):**

```bash
SECRET_KEY=xK9mP3qR8tY6uE2wZ5vB7nA4sD1fG0hJ
JWT_SECRET_KEY=qW8eR3tY7uI9oP1aS5dF2gH6jK4lZ0xC
```

---

## ✅ Checklist przed deployem

**KRYTYCZNE - zmień te wartości:**

- [ ] `SECRET_KEY` - wygeneruj unikalny 32-znakowy klucz
- [ ] `JWT_SECRET_KEY` - wygeneruj unikalny 32-znakowy klucz (inny niż SECRET_KEY)
- [ ] `POSTGRES_PASSWORD` - silne hasło (16+ znaków, mix znaków)
- [ ] `FLASK_DEBUG=False` - NIGDY True w produkcji!
- [ ] `JWT_COOKIE_SECURE=True` - wymaga HTTPS
- [ ] `CORS_ORIGINS` - zmień z `*` na twoje domeny
- [ ] `VITE_API_URL` - ustaw URL swojego API (https://...)
- [ ] `VALIDATE_PASSWORD_STRENGTH=True` - wymusza silne hasła użytkowników

**⚠️ Plik `.env` NIE MOŻE być w repozytorium Git!** (sprawdź `.gitignore`)

---

## 🚀 Uruchomienie produkcji

```bash
# 1. Skopiuj szablon
cp .env.example .env

# 2. Edytuj .env i ustaw wszystkie wartości
nano .env

# 3. Uruchom
docker-compose up -d --build

# 4. Sprawdź logi
docker-compose logs -f
```

---

## 📚 Szczegółowy opis wszystkich zmiennych

### PostgreSQL Database

| Zmienna | Domyślna | Opis |
|---------|----------|------|
| `POSTGRES_USER` | `postgres` | Nazwa użytkownika bazy danych |
| `POSTGRES_PASSWORD` | `postgres` | Hasło do bazy (**ZMIEŃ W PRODUKCJI!**) |
| `POSTGRES_DB` | `cryptography_db` | Nazwa bazy danych |
| `POSTGRES_PORT` | `5432` | Port PostgreSQL |

**Uwagi:**
- Zmienne są używane przy pierwszym uruchomieniu
- Po utworzeniu bazy, zmiana wymaga usunięcia volume: `docker-compose down -v`
- W produkcji użyj silnych haseł (minimum 16 znaków)

### Backend (Flask)

| Zmienna | Domyślna | Opis |
|---------|----------|------|
| `BACKEND_PORT` | `5000` | Port backendu (wewnętrzny w Docker) |
| `FLASK_DEBUG` | `False` | Tryb debug (**NIGDY True w produkcji!**) |
| `FLASK_TESTING` | `False` | Tryb testowy |
| `SECRET_KEY` | - | Klucz dla sesji Flask (**ZMIEŃ!**) |
| `JWT_SECRET_KEY` | - | Klucz dla tokenów JWT (**ZMIEŃ!**) |
| `JWT_ACCESS_TOKEN_EXPIRES` | `3600` | Czas życia access tokenu (sekundy, 1h) |
| `JWT_REFRESH_TOKEN_EXPIRES` | `2592000` | Czas życia refresh tokenu (sekundy, 30 dni) |
| `JWT_COOKIE_SECURE` | `False` | Wymaga HTTPS dla cookies (True w produkcji) |
| `VALIDATE_PASSWORD_STRENGTH` | `False` | Wymagaj silnych haseł (True w produkcji) |
| `CORS_ORIGINS` | `*` | Dozwolone originy CORS (ograniczyć w produkcji) |

**Uwagi:**
- `FLASK_DEBUG=True` włącza auto-reload i szczegółowe error pages (niebezpieczne!)
- `JWT_COOKIE_SECURE=True` wymaga HTTPS
- `VALIDATE_PASSWORD_STRENGTH=True` wymusza: wielką/małą literę, cyfrę (min 8 znaków)

### Nginx Reverse Proxy

| Zmienna | Domyślna | Opis |
|---------|----------|------|
| `NGINX_PORT` | `8080` | Port Nginx (główny punkt wejścia) |

---

## 📝 Przykładowe konfiguracje

### Development (Lokalne)

```env
POSTGRES_USER=dev_user
POSTGRES_PASSWORD=dev_password
POSTGRES_DB=cryptography_dev
POSTGRES_PORT=5432

BACKEND_PORT=5000
FLASK_DEBUG=True
FLASK_TESTING=False
SECRET_KEY=dev-secret-key-not-for-production
JWT_SECRET_KEY=dev-jwt-secret-key

NGINX_PORT=8080
CORS_ORIGINS=*

JWT_COOKIE_SECURE=False
VALIDATE_PASSWORD_STRENGTH=False
```

### Production

```env
POSTGRES_USER=prod_cryptography_user
POSTGRES_PASSWORD=aVeryStr0ng!RandomP@ssw0rd123!
POSTGRES_DB=cryptography_production
POSTGRES_PORT=5432

BACKEND_PORT=5000
FLASK_DEBUG=False
FLASK_TESTING=False
SECRET_KEY=wygenerowany-losowy-32-znakowy-klucz-abc123xyz
JWT_SECRET_KEY=inny-wygenerowany-32-znakowy-klucz-xyz789abc
JWT_ACCESS_TOKEN_EXPIRES=3600
JWT_REFRESH_TOKEN_EXPIRES=2592000
JWT_COOKIE_SECURE=True
VALIDATE_PASSWORD_STRENGTH=True

NGINX_PORT=443
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

SOCKETIO_MESSAGE_QUEUE=
```

---

## 🆘 Troubleshooting

### "Database connection failed"

- Sprawdź `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
- Sprawdź czy kontener db działa: `docker-compose ps`
- Zobacz logi: `docker-compose logs db`

### "CORS error" w przeglądarce

- Sprawdź `CORS_ORIGINS` w backendie
- Sprawdź `VITE_API_URL` we frontendzie
- Zobacz logi: `docker-compose logs backend`

### "Port already in use"

- Zmień `NGINX_PORT`, lub `BACKEND_PORT`
- Windows: `netstat -ano | findstr :8080`
- Linux: `lsof -i :8080`

### Zmienne nie działają

- Restart kontenerów: `docker-compose down && docker-compose up`
- Rebuild: `docker-compose up --build`
- Sprawdź czy plik nazywa się dokładnie `.env`

### Cookies nie działają (refresh token)

- Sprawdź `JWT_COOKIE_SECURE`:
  - `True` wymaga HTTPS
  - `False` dla HTTP (tylko development)
- Sprawdź czy HTTPS jest poprawnie skonfigurowane
