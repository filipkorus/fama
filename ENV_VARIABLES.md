# 🔐 Environment Variables Documentation

## Plik `.env`

Wszystkie zmienne środowiskowe używane w projekcie i ich opis.

## 📋 Kompletna lista zmiennych

### PostgreSQL Database

```env
# Nazwa użytkownika bazy danych
POSTGRES_USER=postgres

# Hasło do bazy danych (ZMIEŃ W PRODUKCJI!)
POSTGRES_PASSWORD=postgres

# Nazwa bazy danych
POSTGRES_DB=cryptography_db

# Port PostgreSQL (lokalnie dostępny)
POSTGRES_PORT=5432
```

**Uwagi:**
- `POSTGRES_USER` i `POSTGRES_PASSWORD` są używane przy pierwszym uruchomieniu
- Po utworzeniu bazy, zmiana tych wartości wymaga usunięcia volume: `docker-compose down -v`
- W produkcji użyj silnych haseł (minimum 16 znaków, mix znaków)

### Backend (Flask)

```env
# Port backendu (wewnętrzny w Docker, lokalnie dostępny)
BACKEND_PORT=5000

# Tryb debug Flask (True/False)
# NIGDY nie używaj True w produkcji!
FLASK_DEBUG=False

# Tryb testowy Flask (True/False)
FLASK_TESTING=False

# Klucz tajny dla sesji Flask
# KONIECZNIE zmień w produkcji! Wygeneruj losowy string.
SECRET_KEY=your-secret-key-change-this-in-production

# Dozwolone originy CORS
# '*' = wszystkie (tylko development)
# W produkcji: 'https://twoja-domena.com,https://api.twoja-domena.com'
CORS_ORIGINS=*
```

**Generowanie SECRET_KEY:**
```python
# W Pythonie
import secrets
print(secrets.token_urlsafe(32))
```

```bash
# W bashu
openssl rand -base64 32
```

**Uwagi:**
- `FLASK_DEBUG=True` włącza auto-reload i szczegółowe error pages
- `SECRET_KEY` używany do podpisywania sesji i cookies
- `CORS_ORIGINS` powinien być ograniczony w produkcji

### Frontend (React + Vite)

```env
# Port frontendu (wewnętrzny w Docker, lokalnie dostępny)
FRONTEND_PORT=3000

# URL backendu - używany przez frontend do komunikacji
# W development z Docker: http://localhost:8080
# W production: https://api.twoja-domena.com
VITE_API_URL=http://localhost:8080
```

**Uwagi:**
- Zmienne dla Vite MUSZĄ zaczynać się od `VITE_`
- `VITE_API_URL` powinien wskazywać na Nginx (reverse proxy), nie bezpośrednio na backend
- W produkcji użyj HTTPS

### Nginx Reverse Proxy

```env
# Port Nginx (główny punkt wejścia do aplikacji)
NGINX_PORT=8080
```

**Uwagi:**
- To główny port przez który użytkownicy uzyskują dostęp do aplikacji
- W produkcji zazwyczaj 80 (HTTP) lub 443 (HTTPS)
- Jeśli port jest zajęty, zmień na inny (np. 8081, 8082)

## 📝 Przykładowe konfiguracje

### Development (Lokalne)

```env
# .env dla development
POSTGRES_USER=dev_user
POSTGRES_PASSWORD=dev_password
POSTGRES_DB=cryptography_dev
POSTGRES_PORT=5432

BACKEND_PORT=5000
FLASK_DEBUG=True
FLASK_TESTING=False
SECRET_KEY=dev-secret-key-not-for-production

FRONTEND_PORT=3000
VITE_API_URL=http://localhost:8080

NGINX_PORT=8080
CORS_ORIGINS=*
```

### Testing

```env
# .env dla testów (używa docker-compose.test.yml)
POSTGRES_USER=test_user
POSTGRES_PASSWORD=test_password
POSTGRES_DB=cryptography_test_db

FLASK_DEBUG=False
FLASK_TESTING=True
SECRET_KEY=test-secret-key

CORS_ORIGINS=*
```

### Production

```env
# .env dla produkcji
POSTGRES_USER=prod_cryptography_user
POSTGRES_PASSWORD=aVeryStr0ng!RandomP@ssw0rd123!
POSTGRES_DB=cryptography_production
POSTGRES_PORT=5432

BACKEND_PORT=5000
FLASK_DEBUG=False
FLASK_TESTING=False
SECRET_KEY=wygenerowany-losowy-32-znakowy-klucz-abc123xyz

FRONTEND_PORT=3000
VITE_API_URL=https://api.yourdomain.com

NGINX_PORT=80
CORS_ORIGINS=https://yourdomain.com
```

## 🔒 Best Practices

### Bezpieczeństwo

1. **Nigdy nie commituj pliku `.env`** do repozytorium
   - `.env` jest w `.gitignore`
   - Użyj `.env.example` jako template

2. **Zmień SECRET_KEY w produkcji**
   - Użyj długiego, losowego ciągu znaków
   - Przechowuj bezpiecznie (np. w secrets manager)

3. **Użyj silnych haseł do bazy danych**
   - Minimum 16 znaków
   - Mix wielkich/małych liter, cyfr, symboli
   - Nie używaj słownikowych słów

4. **Ogranicz CORS_ORIGINS w produkcji**
   - Lista konkretnych domen
   - Nigdy `*` w produkcji

5. **Wyłącz FLASK_DEBUG w produkcji**
   - Debug mode ujawnia wrażliwe informacje
   - Używaj tylko w development

### Zarządzanie

1. **Różne ENV dla różnych środowisk**
   ```
   .env.development
   .env.staging
   .env.production
   ```

2. **Dokumentuj zmiany**
   - Aktualizuj `.env.example` przy dodawaniu zmiennych
   - Dodaj komentarze wyjaśniające

3. **Walidacja konfiguracji**
   - Sprawdź czy wszystkie wymagane zmienne są ustawione
   - Użyj sensownych default values

## 🔧 Zaawansowane użycie

### Używanie różnych plików .env

```bash
# Development
docker-compose --env-file .env.development up

# Production
docker-compose --env-file .env.production up
```

### Override w docker-compose

Stwórz `docker-compose.override.yml` (nie commituj):

```yaml
version: '3.8'

services:
  backend:
    environment:
      FLASK_DEBUG: "True"
    volumes:
      - ./backend:/app  # Hot reload
```

### Zmienne per serwis

```yaml
# docker-compose.yml
services:
  backend:
    environment:
      # Nadpisz zmienną tylko dla backendu
      CUSTOM_BACKEND_VAR: "value"
```

### Secrets w Docker Swarm/Kubernetes

W produkcji, rozważ użycie:
- Docker Secrets (Swarm)
- Kubernetes Secrets
- AWS Secrets Manager
- Azure Key Vault
- HashiCorp Vault

## ✅ Checklist przed deploymentem

- [ ] SECRET_KEY zmieniony na losowy
- [ ] POSTGRES_PASSWORD silne i unikalne
- [ ] FLASK_DEBUG=False
- [ ] CORS_ORIGINS ograniczone do Twoich domen
- [ ] VITE_API_URL wskazuje na produkcyjny URL
- [ ] Wszystkie zmienne są udokumentowane
- [ ] `.env` NIE jest w repozytorium
- [ ] Backup `.env` jest bezpiecznie przechowywany

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
- Zmień `NGINX_PORT`, `BACKEND_PORT`, lub `FRONTEND_PORT`
- Sprawdź co używa portu: `netstat -ano | findstr :8080` (Windows)
- Zatrzymaj konfliktujący serwis

### Zmienne nie są brane pod uwagę
- Restart kontenerów: `docker-compose down && docker-compose up`
- Rebuild: `docker-compose up --build`
- Sprawdź czy plik nazywa się dokładnie `.env`
