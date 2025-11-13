# API Autoryzacji - Dokumentacja

## Przegląd

Moduł autoryzacji zapewnia bezpieczny system rejestracji i logowania użytkowników z wykorzystaniem tokenów JWT (JSON Web Tokens).

**Mechanizm tokenów:**
- **Access Token** - wysyłany w odpowiedzi JSON, używany do autoryzacji zapytań API
- **Refresh Token** - wysyłany jako HTTP-only cookie, używany do odświeżania access tokenów

**Obsługa wielu urządzeń:**
- Każdy użytkownik może mieć wiele urządzeń (telefon, laptop, tablet)
- Każde urządzenie ma swój unikalny klucz publiczny ML-KEM do szyfrowania post-kwantowego
- Nazwy urządzeń są automatycznie generowane z User-Agent lub mogą być ustawione ręcznie

> **Ważne:** Refresh tokeny są przechowywane wyłącznie w HTTP-only cookies dla zwiększenia bezpieczeństwa. Access tokeny nadal są zwracane w JSON i powinny być przechowywane bezpiecznie po stronie klienta.

## Endpointy API

Wszystkie endpointy znajdują się pod prefiksem `/api/auth`.

### 1. Rejestracja użytkownika

**Endpoint:** `POST /api/auth/register`

**Opis:** Tworzy nowe konto użytkownika i rejestruje pierwsze urządzenie. Użytkownik musi wygenerować parę kluczy ML-KEM (Kyber) po stronie klienta i przesłać klucz publiczny. Klucz prywatny NIGDY nie powinien być wysyłany do serwera.

**Żądanie:**
```json
{
  "username": "string",
  "password": "string",
  "public_key": "string (Base64-encoded ML-KEM public key)",
  "device_name": "string (optional, e.g., 'iPhone 15 Pro', 'MacBook Pro')"
}
```

**Wymagania:**

- **Username:**
  - Długość: 3-80 znaków
  - Dozwolone znaki: litery (a-z, A-Z), cyfry (0-9), podkreślnik (_), myślnik (-)
  - Unikalny w systemie
  
- **Password:**
  - Minimum 8 znaków
  - Walidacja siły hasła (wielkie/małe litery, cyfry) jest opcjonalna i kontrolowana przez `VALIDATE_PASSWORD_STRENGTH` w konfiguracji

- **Public Key:**
  - Format: Base64-encoded string
  - Rozmiar zdekodowany: 800 bytes (Kyber512), 1184 bytes (Kyber768), lub 1568 bytes (Kyber1024)
  - Generowany z biblioteki `liboqs-python` lub kompatybilnej implementacji ML-KEM

- **Device Name (opcjonalne):**
  - Jeśli nie podany, zostanie automatycznie wygenerowany z User-Agent
  - Przykłady: "Chrome 120 on Windows 10", "Safari 17 on iPhone", "Firefox 119 on Ubuntu"

**Odpowiedź sukcesu (201):**

```json
{
  "message": "User registered successfully",
  "user": {
    "id": 1,
    "username": "testuser",
    "created_at": "2024-01-15T10:30:00",
    "updated_at": "2024-01-15T10:30:00"
  },
  "device": {
    "id": 1,
    "device_name": "Chrome 120 on Windows 10",
    "public_key": "OwOc0pQrXx...",
    "created_at": "2024-01-15T10:30:00",
    "last_used_at": "2024-01-15T10:30:00"
  },
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Cookies:**
- `refresh_token` - HTTP-only cookie z refresh tokenem

**Błędy:**

- `400` - Nieprawidłowe dane wejściowe (username, password, lub public_key), lub użytkownik już istnieje
- `500` - Błąd serwera

**Przykład użycia (axios):**

```javascript
import axios from 'axios';

// Krok 1: Wygeneruj parę kluczy ML-KEM po stronie klienta
// UWAGA: Wymaga biblioteki liboqs-node lub WebAssembly implementation
const crypto = new MLKEMCrypto('Kyber768');
const { publicKey, privateKey } = await crypto.generateKeypair();

// WAŻNE: Przechowaj privateKey bezpiecznie po stronie klienta!
// NIGDY nie wysyłaj privateKey do serwera!
localStorage.setItem('ml_kem_private_key', privateKey);

// Krok 2: Zarejestruj się z kluczem publicznym
const response = await axios.post('/api/auth/register', {
  username: 'nowyuzytkownik',
  password: 'Haslo123',
  public_key: publicKey, // Base64-encoded
  device_name: 'Moj Laptop' // Opcjonalne - jeśli brak, użyje User-Agent
}, {
  withCredentials: true // Umożliwia odbieranie cookies
});

console.log(response.data);
// {
//   message: "User registered successfully",
//   user: { id: 1, username: "nowyuzytkownik", ... },
//   device: { id: 1, device_name: "Moj Laptop", public_key: "...", ... },
//   access_token: "..."
// }
```

---

### 2. Logowanie

**Endpoint:** `POST /api/auth/login`

**Opis:** Loguje użytkownika i zwraca tokeny JWT.

**Żądanie:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Odpowiedź sukcesu (200):**

```json
{
  "message": "Login successful",
  "user": {
    "id": 1,
    "username": "testuser",
    "created_at": "2024-01-15T10:30:00",
    "updated_at": "2024-01-15T10:30:00"
  },
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Cookies:**

- `refresh_token` - HTTP-only cookie z refresh tokenem

**Błędy:**

- `400` - Brak wymaganych danych
- `401` - Nieprawidłowa nazwa użytkownika lub hasło
- `500` - Błąd serwera

**Przykład użycia (axios):**

```javascript
import axios from 'axios';

const response = await axios.post('/api/auth/login', {
  username: 'nowyuzytkownik',
  password: 'Haslo123'
}, {
  withCredentials: true // Umożliwia odbieranie cookies
});

console.log(response.data);
// { message: "Login successful", user: {...}, access_token: "..." }
```

---

### 3. Odświeżanie tokenu

**Endpoint:** `POST /api/auth/refresh`

**Opis:** Generuje nowy access token używając refresh tokenu z HTTP-only cookie.

**Cookies:**

- `refresh_token` - Refresh token (HTTP-only cookie)

**Odpowiedź sukcesu (200):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Błędy:**

- `401` - Nieprawidłowy lub unieważniony token
- `500` - Błąd serwera

**Przykład użycia (axios z interceptorem):**

```javascript
import axios from 'axios';

// Konfiguracja axios z automatycznym odświeżaniem tokenów
const api = axios.create({
  baseURL: '/api',
  withCredentials: true // Wysyła cookies
});

// Interceptor odpowiedzi - automatycznie odświeża token gdy wygaśnie
api.interceptors.response.use(
  (response) => response, // Jeśli OK, zwróć odpowiedź
  async (error) => {
    const originalRequest = error.config;
    
    // Jeśli błąd 401 i nie próbowaliśmy jeszcze odświeżyć tokenu
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true; // Oznacz, że próbujemy odświeżyć
      
      try {
        // Wywołaj /refresh aby dostać nowy access token
        const response = await axios.post('/api/auth/refresh', {}, {
          withCredentials: true
        });
        
        const newAccessToken = response.data.access_token;
        
        // Zaktualizuj token w localStorage
        localStorage.setItem('access_token', newAccessToken);
        
        // Zaktualizuj nagłówek w oryginalnym zapytaniu
        originalRequest.headers['Authorization'] = `Bearer ${newAccessToken}`;
        
        // Ponów oryginalne zapytanie z nowym tokenem
        return api(originalRequest);
      } catch (refreshError) {
        // Refresh token wygasł lub jest nieprawidłowy - wyloguj użytkownika
        localStorage.removeItem('access_token');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }
    
    return Promise.reject(error);
  }
);

// Użycie - automatycznie odświeży token jeśli wygaśnie
const getUserData = async () => {
  const accessToken = localStorage.getItem('access_token');
  const response = await api.get('/auth/me', {
    headers: { Authorization: `Bearer ${accessToken}` }
  });
  return response.data;
};
```

---

### 4. Wylogowanie

**Endpoint:** `POST /api/auth/logout`

**Opis:** Wylogowuje użytkownika przez unieważnienie refresh tokenu z HTTP-only cookie.

**Cookies:**

- `refresh_token` - Refresh token (HTTP-only cookie)

**Odpowiedź sukcesu (200):**

```json
{
  "message": "Logout successful"
}
```

**Błędy:**

- `401` - Nieprawidłowy token
- `500` - Błąd serwera

**Przykład użycia (axios):**

```javascript
import axios from 'axios';

const logout = async () => {
  await axios.post('/api/auth/logout', {}, {
    withCredentials: true // Wysyła HTTP-only cookie z refresh tokenem
  });
  
  localStorage.removeItem('access_token');
  window.location.href = '/login';
};
```

---

### 5. Pobierz dane użytkownika

**Endpoint:** `GET /api/auth/me`

**Opis:** Zwraca informacje o aktualnie zalogowanym użytkowniku.

**Nagłówki:**
```
Authorization: Bearer <access_token>
```

**Odpowiedź sukcesu (200):**
```json
{
  "user": {
    "id": 1,
    "username": "testuser",
    "created_at": "2024-01-15T10:30:00",
    "updated_at": "2024-01-15T10:30:00"
  }
}
```

**Błędy:**

- `401` - Brak tokenu lub nieprawidłowy token
- `404` - Użytkownik nie znaleziony
- `500` - Błąd serwera

**Przykład użycia (axios):**

```javascript
import axios from 'axios';

const getCurrentUser = async () => {
  const accessToken = localStorage.getItem('access_token');
  
  const response = await axios.get('/api/auth/me', {
    headers: {
      Authorization: `Bearer ${accessToken}`
    }
  });
  
  return response.data.user;
};
```

---

## Tokeny JWT

System wykorzystuje dwa rodzaje tokenów JWT:

### Access Token
- **Czas życia:** 1 godzina (domyślnie)
- **Przeznaczenie:** Autoryzacja zapytań API
- **Użycie:** Dodaj do nagłówka `Authorization: Bearer <access_token>`

### Refresh Token

- **Czas życia:** 30 dni (domyślnie)
- **Przeznaczenie:** Generowanie nowych access tokenów
- **Przechowywanie:** 
  - Zapisywany w HTTP-only cookie po stronie klienta
  - Zapisywany w bazie danych z możliwością unieważnienia
- **Użycie:** Automatycznie wysyłany jako cookie do `/api/auth/refresh` aby otrzymać nowy access token

---

### Struktura tokenu JWT

```json
{
  "sub": "1",           // ID użytkownika
  "iat": 1642252800,    // Czas utworzenia
  "exp": 1642256400,    // Czas wygaśnięcia
  "jti": "unique-id",   // Unikalny identyfikator tokenu
  "type": "access"      // Typ tokenu (access/refresh)
}
```

---

## Modele bazy danych

### User (Użytkownik)

**Tabela:** `users`

| Pole | Typ | Opis |
|------|-----|------|
| id | Integer | Klucz główny |
| username | String(80) | Unikalna nazwa użytkownika |
| password_hash | String(255) | Zahashowane hasło (bcrypt) |
| created_at | DateTime | Data utworzenia konta |
| updated_at | DateTime | Data ostatniej aktualizacji |

**Metody:**
- `set_password(password)` - Hashuje i zapisuje hasło
- `check_password(password)` - Weryfikuje hasło
- `to_dict()` - Konwertuje obiekt do słownika (bez hasła)

### RefreshToken (Token odświeżania)

**Tabela:** `refresh_tokens`

| Pole | Typ | Opis |
|------|-----|------|
| id | Integer | Klucz główny |
| jti | String(36) | Unikalny identyfikator tokenu JWT |
| user_id | Integer | Klucz obcy do użytkownika |
| revoked | Boolean | Czy token został unieważniony |
| expires_at | DateTime | Data wygaśnięcia tokenu |
| created_at | DateTime | Data utworzenia tokenu |

---

## Bezpieczeństwo

### Hashowanie haseł
- Wykorzystuje Werkzeug's `generate_password_hash` (bcrypt)
- Hasła nigdy nie są przechowywane w formie jawnej
- Salt jest automatycznie generowany dla każdego hasła

### Walidacja danych
- Walidacja długości i formatu nazwy użytkownika
- Wymagania dotyczące siły hasła
- Sanityzacja danych wejściowych (`.strip()`)

### Tokeny JWT
- Podpisywane kluczem tajnym (`JWT_SECRET_KEY`)
- Zawierają czas wygaśnięcia
- Refresh tokeny przechowywane w bazie z możliwością unieważnienia
- Automatyczne sprawdzanie czy token nie został unieważniony

### Najlepsze praktyki

1. **Przechowuj access tokeny bezpiecznie** - używaj odpowiednich mechanizmów przechowywania (np. memory, sessionStorage dla SPA)
2. **Refresh tokeny są automatycznie w HTTP-only cookies** - nie musisz nimi zarządzać ręcznie po stronie frontendu
3. **Zawsze używaj HTTPS** w produkcji (ustaw `JWT_COOKIE_SECURE=True`)
4. **Regularnie odświeżaj access tokeny** przed ich wygaśnięciem
5. **Wyloguj użytkownika** gdy refresh token wygaśnie lub zostanie unieważniony
6. **Zmień domyślne klucze tajne** w produkcji (`SECRET_KEY` i `JWT_SECRET_KEY`)

---

## Konfiguracja

W pliku `config.py` można skonfigurować następujące parametry:

```python
# Klucz tajny JWT (ZMIEŃ W PRODUKCJI!)
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')

# Czas życia access tokenu (timedelta lub sekundy)
JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)  # 1 godzina

# Czas życia refresh tokenu (timedelta lub sekundy)
JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)  # 30 dni

# Bezpieczeństwo cookie (włącz w produkcji z HTTPS)
JWT_COOKIE_SECURE = False  # Ustaw True w produkcji

# Walidacja siły hasła (opcjonalne)
VALIDATE_PASSWORD_STRENGTH = False  # Ustaw True aby wymagać wielkich/małych liter i cyfr
```

**Zmienne środowiskowe:**

- `JWT_SECRET_KEY` - Klucz do podpisywania tokenów JWT
- `JWT_ACCESS_TOKEN_EXPIRES` - Czas życia access tokenu w sekundach
- `JWT_REFRESH_TOKEN_EXPIRES` - Czas życia refresh tokenu w sekundach
- `JWT_COOKIE_SECURE` - Czy cookies powinny być oznaczone jako "Secure" (tylko HTTPS)
- `VALIDATE_PASSWORD_STRENGTH` - Czy wymagać silnych haseł (wielkie/małe litery, cyfry)

---

## Przykładowy przepływ autoryzacji

### 1. Rejestracja nowego użytkownika

```javascript
// Frontend
const response = await fetch('/api/auth/register', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  credentials: 'include', // Ważne! Umożliwia wysyłanie/odbieranie cookies
  body: JSON.stringify({
    username: 'nowyuzytkownik',
    password: 'Haslo123'
  })
});

const data = await response.json();
// Zapisz tylko access token (refresh token jest w HTTP-only cookie)
localStorage.setItem('access_token', data.access_token);
```

### 2. Logowanie użytkownika

```javascript
const response = await fetch('/api/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  credentials: 'include', // Ważne! Umożliwia wysyłanie/odbieranie cookies
  body: JSON.stringify({
    username: 'nowyuzytkownik',
    password: 'Haslo123'
  })
});

const data = await response.json();
// Zapisz tylko access token
localStorage.setItem('access_token', data.access_token);
```

### 3. Autoryzowane zapytanie API

```javascript
const accessToken = localStorage.getItem('access_token');

const response = await fetch('/api/auth/me', {
  headers: {
    'Authorization': `Bearer ${accessToken}`
  }
});

const userData = await response.json();
```

### 4. Odświeżanie tokenu

```javascript
async function refreshAccessToken() {
  const response = await fetch('/api/auth/refresh', {
    method: 'POST',
    credentials: 'include' // Ważne! Wysyła HTTP-only cookie z refresh tokenem
  });
  
  if (response.ok) {
    const data = await response.json();
    localStorage.setItem('access_token', data.access_token);
    return data.access_token;
  } else {
    // Refresh token wygasł lub został unieważniony
    // Przekieruj do strony logowania
    localStorage.removeItem('access_token');
    window.location.href = '/login';
  }
}
```

### 5. Wylogowanie

```javascript
async function logout() {
  await fetch('/api/auth/logout', {
    method: 'POST',
    credentials: 'include' // Ważne! Wysyła HTTP-only cookie z refresh tokenem
  });
  
  // Usuń access token
  localStorage.removeItem('access_token');
  
  // Przekieruj do strony logowania
  window.location.href = '/login';
}
```

---

## Obsługa błędów

### Typowe kody błędów

| Kod | Znaczenie | Działanie |
|-----|-----------|-----------|
| 400 | Bad Request | Sprawdź poprawność danych wejściowych |
| 401 | Unauthorized | Token wygasł lub jest nieprawidłowy - odśwież lub zaloguj ponownie |
| 404 | Not Found | Użytkownik nie istnieje |
| 422 | Unprocessable Entity | Nieprawidłowy format tokenu JWT |
| 500 | Internal Server Error | Błąd serwera - skontaktuj się z administratorem |

### Przykład obsługi błędów

```javascript
async function makeAuthenticatedRequest(url) {
  let accessToken = localStorage.getItem('access_token');
  
  let response = await fetch(url, {
    headers: {
      'Authorization': `Bearer ${accessToken}`
    },
    credentials: 'include' // Ważne dla odświeżania tokenu
  });
  
  // Jeśli access token wygasł, spróbuj odświeżyć
  if (response.status === 401) {
    accessToken = await refreshAccessToken();
    
    if (accessToken) {
      // Ponów zapytanie z nowym tokenem
      response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${accessToken}`
        },
        credentials: 'include'
      });
    }
  }
  
  return response;
}
```

---

## Testowanie

Moduł zawiera kompleksowe testy w pliku `tests/test_auth.py`.

### Uruchomienie testów

```bash
# Wszystkie testy autoryzacji
pytest backend/tests/test_auth.py -v

# Konkretny test
pytest backend/tests/test_auth.py::TestAuthAPI::test_register_success -v

# Z pokryciem kodu
pytest backend/tests/test_auth.py --cov=api.auth --cov-report=html
```

### Zakres testów
- Rejestracja użytkownika (pozytywne i negatywne scenariusze)
- Logowanie (poprawne i niepoprawne dane)
- Walidacja nazwy użytkownika
- Walidacja siły hasła
- Generowanie i odświeżanie tokenów
- Wylogowanie i unieważnianie tokenów
- Hashowanie haseł
- Przechowywanie tokenów w bazie danych
