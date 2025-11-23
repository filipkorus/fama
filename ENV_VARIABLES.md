# Wdrożenie produkcyjne (Deployment)

## Konfiguracja zmiennych środowiskowych

Plik `.env` w głównym katalogu projektu definiuje parametry działania kontenerów. Poniżej znajduje się szablon konfiguracji dla środowiska produkcyjnego.

**Lokalizacja:** `fama/.env`

### Wzór konfiguracji produkcyjnej

```env
# PostgreSQL Configuration
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<SILNE_HASLO_16_ZNAKOW>
POSTGRES_DB=cryptography_production
POSTGRES_PORT=5432

# Backend Configuration
BACKEND_PORT=5000
FLASK_DEBUG=False
FLASK_TESTING=False
SECRET_KEY=<WYGENEROWANY_KLUCZ_32_ZNAKI>

# JWT Configuration
JWT_SECRET_KEY=<WYGENEROWANY_KLUCZ_JWT_32_ZNAKI>
JWT_ACCESS_TOKEN_EXPIRES=3600
JWT_REFRESH_TOKEN_EXPIRES=2592000
JWT_COOKIE_SECURE=True
VALIDATE_PASSWORD_STRENGTH=True

# Nginx Configuration
NGINX_PORT=443

# CORS Configuration
CORS_ORIGINS=https://fama.fkor.us

# SocketIO Configuration
SOCKETIO_MESSAGE_QUEUE=
```

## Generowanie kluczy kryptograficznych

Wymagane jest wygenerowanie unikalnych, losowych ciągów znaków dla zmiennych `SECRET_KEY` oraz `JWT_SECRET_KEY`.

**Metoda 1: OpenSSL (Linux/macOS)**
```bash
openssl rand -base64 32
```

**Metoda 2: Python**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Metoda 3: PowerShell**
```powershell
-join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | % {[char]$_})
```

## Weryfikacja przedwdrożeniowa

Należy upewnić się, że następujące parametry zostały poprawnie ustawione:

1.  `SECRET_KEY` i `JWT_SECRET_KEY`: Unikalne, 32-znakowe klucze.
2.  `POSTGRES_PASSWORD`: Hasło o wysokiej entropii (min. 16 znaków).
3.  `FLASK_DEBUG`: Ustawione na `False`.
4.  `JWT_COOKIE_SECURE`: Ustawione na `True` (wymaga SSL/HTTPS).
5.  `CORS_ORIGINS`: Ograniczone do domeny produkcyjnej.
6.  `VALIDATE_PASSWORD_STRENGTH`: Ustawione na `True`.

## Procedura uruchomienia

```bash
# 1. Utworzenie pliku konfiguracyjnego
cp .env.example .env

# 2. Edycja parametrów (wymagane nano/vim)
nano .env

# 3. Uruchomienie kontenerów w trybie detached
docker compose up -d --build

# 4. Weryfikacja logów startowych
docker compose logs -f
```

## Opis zmiennych konfiguracyjnych

### Baza danych (PostgreSQL)

| Zmienna | Wartość domyślna | Opis |
| --- | --- | --- |
| `POSTGRES_USER` | `postgres` | Użytkownik administracyjny |
| `POSTGRES_PASSWORD` | `postgres` | Hasło użytkownika (zmiana wymagana) |
| `POSTGRES_DB` | `cryptography_db` | Nazwa bazy danych |
| `POSTGRES_PORT` | `5432` | Port nasłuchiwania kontenera |

*Zmiana hasła po zainicjowaniu wolumenu bazy danych wymaga jego usunięcia (`docker compose down -v`) i ponownego utworzenia.*

### Backend (Flask)

| Zmienna | Wartość domyślna | Opis |
| --- | --- | --- |
| `BACKEND_PORT` | `5000` | Wewnętrzny port serwera aplikacji |
| `FLASK_DEBUG` | `False` | Tryb debugowania (wyłączony na produkcji) |
| `SECRET_KEY` | - | Klucz podpisywania sesji |
| `JWT_SECRET_KEY` | - | Klucz podpisywania tokenów JWT |
| `JWT_COOKIE_SECURE` | `False` | Flaga Secure dla ciasteczek (wymaga HTTPS) |
| `VALIDATE_PASSWORD_STRENGTH` | `False` | Wymuszanie złożoności haseł |
| `CORS_ORIGINS` | `*` | Lista dozwolonych domen (CORS) |

### Nginx (Reverse Proxy)

| Zmienna | Wartość domyślna | Opis |
| --- | --- | --- |
| `NGINX_PORT` | `8080` | Publiczny port aplikacji |

## Przykłady konfiguracji

### Środowisko deweloperskie

```env
POSTGRES_USER=dev_user
POSTGRES_PASSWORD=dev_password
POSTGRES_DB=cryptography_dev
FLASK_DEBUG=True
SECRET_KEY=dev-key
JWT_SECRET_KEY=dev-jwt
JWT_COOKIE_SECURE=False
VALIDATE_PASSWORD_STRENGTH=False
CORS_ORIGINS=*
```

### Środowisko produkcyjne

```env
POSTGRES_USER=prod_user
POSTGRES_PASSWORD=<SILNE_HASLO>
POSTGRES_DB=cryptography_prod
FLASK_DEBUG=False
SECRET_KEY=<LOSOWY_KLUCZ_1>
JWT_SECRET_KEY=<LOSOWY_KLUCZ_2>
JWT_COOKIE_SECURE=True
VALIDATE_PASSWORD_STRENGTH=True
CORS_ORIGINS=https://domena-produkcyjna.pl
NGINX_PORT=443
```

## Rozwiązywanie problemów

**Błąd połączenia z bazą danych**
*   Weryfikacja zgodności danych uwierzytelniających w `.env`.
*   Analiza logów kontenera: `docker compose logs db`.

**Błąd CORS**
*   Sprawdzenie zgodności `CORS_ORIGINS` z domeną frontendową.
*   Weryfikacja konfiguracji `VITE_API_URL` po stronie klienta.

**Konflikt portów**
*   Zmiana wartości `NGINX_PORT` lub `BACKEND_PORT` w przypadku zajęcia portów przez inne usługi systemowe.

**Problemy z uwierzytelnianiem (JWT)**
*   Jeżeli `JWT_COOKIE_SECURE=True`, aplikacja musi być serwowana przez HTTPS. W przypadku HTTP ciasteczka nie zostaną ustawione przez przeglądarkę.
