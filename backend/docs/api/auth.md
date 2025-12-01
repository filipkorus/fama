# Dokumentacja API Autoryzacji

System wykorzystuje podwójny mechanizm tokenów JWT (JSON Web Tokens) do zarządzania sesją użytkownika.

*   **Access Token**: Przesyłany w nagłówku `Authorization`, służy do autoryzacji zapytań. Zwracany w ciele odpowiedzi JSON.
*   **Refresh Token**: Przechowywany wyłącznie w ciasteczku `HTTP-only`, służy do odnawiania sesji.

Base URL: `/api/auth`

## Specyfikacja Endpointów

### 1. Rejestracja

Tworzy nowe konto użytkownika. Wymaga wygenerowania dwóch par kluczy po stronie klienta:
- **ML-KEM (Kyber)**: Do wymiany kluczy sesji (key exchange)
- **ML-DSA (Dilithium)**: Do podpisów cyfrowych (digital signatures)

**Endpoint:** `POST /api/auth/register`

**Payload żądania:**
```json
{
  "username": "string",                // 3-80 znaków, [a-zA-Z0-9_-]
  "password": "string",                // min. 8 znaków
  "public_key": "string",              // Base64 ML-KEM Public Key (Kyber)
  "dilithium_public_key": "string"     // Base64 ML-DSA Public Key (Dilithium)
}
```

**Odpowiedź (201 Created):**
```json
{
  "message": "User registered successfully",
  "user": {
    "id": 1,
    "username": "user1",
    "public_key": "BASE64_KYBER_KEY",
    "dilithium_public_key": "BASE64_DILITHIUM_KEY",
    "is_active": true,
    "created_at": "ISO_DATE"
  },
  "access_token": "JWT_STRING"
}
```
*Ciasteczko `refresh_token` jest ustawiane automatycznie.*

**Błędy:**
*   `400`: Błędne dane wejściowe lub użytkownik istnieje.
*   `500`: Błąd serwera.

**Przykład implementacji (Axios):**
```javascript
// Generuj parę kluczy Kyber (do wymiany kluczy sesji)
const kyberCrypto = new MLKEMCrypto('Kyber768');
const { publicKey: kyberPubKey, privateKey: kyberPrivKey } = await kyberCrypto.generateKeypair();

// Generuj parę kluczy Dilithium (do podpisów cyfrowych)
const dilithiumCrypto = new DigitalSignature('Dilithium3');
const { publicKey: dilithiumPubKey, privateKey: dilithiumPrivKey } = await dilithiumCrypto.generateKeypair();

// Zapisz klucze prywatne lokalnie
localStorage.setItem('ml_kem_private_key', kyberPrivKey);
localStorage.setItem('dilithium_private_key', dilithiumPrivKey);

// Wyślij tylko klucze publiczne do serwera
await axios.post('/api/auth/register', {
  username: 'alice',
  password: 'secure_password',
  public_key: kyberPubKey,
  dilithium_public_key: dilithiumPubKey
}, { withCredentials: true });
```

### 2. Logowanie

Uwierzytelnia użytkownika i inicjuje sesję.

**Endpoint:** `POST /api/auth/login`

**Payload żądania:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Odpowiedź (200 OK):**
```json
{
  "message": "Login successful",
  "user": { "id": 1, "username": "user1" },
  "access_token": "JWT_STRING"
}
```
*Ciasteczko `refresh_token` jest ustawiane automatycznie.*

### 3. Odświeżanie tokenu (Refresh)

Generuje nowy Access Token na podstawie ważnego Refresh Tokenu.

**Endpoint:** `POST /api/auth/refresh`

**Wymagania:**
*   Ciasteczko `refresh_token` (HTTP-only).

**Odpowiedź (200 OK):**
```json
{
  "access_token": "NEW_JWT_STRING"
}
```

**Implementacja Interceptora (Auto-refresh):**
```javascript
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      try {
        const { data } = await axios.post('/api/auth/refresh', {}, { withCredentials: true });
        localStorage.setItem('access_token', data.access_token);
        originalRequest.headers['Authorization'] = `Bearer ${data.access_token}`;
        return api(originalRequest);
      } catch (e) {
        localStorage.removeItem('access_token');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);
```

### 4. Wylogowanie

Unieważnia Refresh Token i kończy sesję.

**Endpoint:** `POST /api/auth/logout`

**Wymagania:**
*   Ciasteczko `refresh_token`.

**Odpowiedź (200 OK):**
```json
{
  "message": "Logout successful"
}
```

### 5. Dane użytkownika (Me)

Pobiera dane aktualnie zalogowanego użytkownika.

**Endpoint:** `GET /api/auth/me`

**Nagłówki:**
`Authorization: Bearer <ACCESS_TOKEN>`

**Odpowiedź (200 OK):**
```json
{
  "user": {
    "id": 1,
    "username": "user1",
    "created_at": "ISO_DATE"
  }
}
```

## Konfiguracja Tokenów JWT

**Access Token**
*   Typ: Bearer
*   Ważność: 1 godzina
*   Lokalizacja: Nagłówek `Authorization` / localStorage

**Refresh Token**
*   Ważność: 30 dni
*   Lokalizacja: Ciasteczko `HTTP-only`
*   Bezpieczeństwo: Wymaga flagi `Secure` (HTTPS) na produkcji

**Struktura Payloadu (Claims):**
```json
{
  "sub": "user_id",
  "type": "access|refresh",
  "iat": 1642252800,
  "exp": 1642256400,
  "jti": "unique_uuid"
}
```
