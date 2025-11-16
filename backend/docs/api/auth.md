# API Autoryzacji - Dokumentacja

## Przegląd

Moduł autoryzacji zapewnia bezpieczny system rejestracji i logowania użytkowników z wykorzystaniem tokenów JWT (JSON Web Tokens).

**Mechanizm tokenów:**
- **Access Token** - wysyłany w odpowiedzi JSON, używany do autoryzacji zapytań API
  - Zawiera `user_id` w claims
- **Refresh Token** - wysyłany jako HTTP-only cookie, używany do odświeżania access tokenów

> **Ważne:** Refresh tokeny są przechowywane wyłącznie w HTTP-only cookies dla zwiększenia bezpieczeństwa. Access tokeny nadal są zwracane w JSON i powinny być przechowywane bezpiecznie po stronie klienta.

## Endpointy API

Wszystkie endpointy znajdują się pod prefiksem `/api/auth`.

### 1. Rejestracja użytkownika

**Endpoint:** `POST /api/auth/register`

**Opis:** Tworzy nowe konto użytkownika. Użytkownik musi wygenerować parę kluczy ML-KEM (Kyber) po stronie klienta i przesłać klucz publiczny. Klucz prywatny NIGDY nie powinien być wysyłany do serwera.

**Żądanie:**
```json
{
  "username": "string",
  "password": "string",
  "public_key": "string (Base64-encoded ML-KEM public key)"
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

- `400` - Brak wymaganych danych (username, password)
- `401` - Nieprawidłowa nazwa użytkownika lub hasło
- `500` - Błąd serwera

**Przykład użycia:**

```javascript
import axios from 'axios';

const response = await axios.post('/api/auth/login', {
  username: 'nowyuzytkownik',
  password: 'Haslo123'
}, {
  withCredentials: true
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
