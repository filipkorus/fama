# Socket.IO — Dokumentacja Połączeń

Moduł WebSocket (Socket.IO) odpowiada za komunikację w czasie rzeczywistym. Wszystkie połączenia wymagają autoryzacji za pomocą ważnego tokena JWT (Access Token).

## Autoryzacja Połączenia

Klient inicjujący połączenie musi przekazać token w obiekcie `auth` podczas handshake'u.

**Parametry połączenia (Client-Side):**
```javascript
const socket = io('https://api.fama.fkor.us', {
  auth: {
    token: 'Bearer <ACCESS_TOKEN>' // lub sam token bez prefixu
  }
});
```

**Proces weryfikacji (Server-Side):**
1.  Serwer ekstrahuje token z parametru `auth`.
2.  Weryfikuje podpis i ważność JWT (`decode_token`).
3.  W przypadku sukcesu:
    *   Pobiera dane użytkownika z bazy.
    *   Mapuje `socket.id` do `user_id` w pamięci serwera (`connected_users`).
    *   Emituje zdarzenie `connected`.
4.  W przypadku błędu:
    *   Odrzuca połączenie lub emituje zdarzenie `error` i rozłącza klienta.

## Zdarzenia Systemowe

### 1. Połączenie (Client -> Server)

Zdarzenie inicjowane automatycznie przez bibliotekę klienta po udanym nawiązaniu połączenia TCP/Transport.

**Event:** `connect`

**Działania serwera:**
*   Rejestracja sesji użytkownika.
*   Dołączenie socketa do prywatnego pokoju (np. `user_<id>`).
*   Broadcast statusu "online" do innych użytkowników (opcjonalnie).

### 2. Potwierdzenie połączenia (Server -> Client)

Potwierdzenie udanej autoryzacji i rejestracji w systemie.

**Event:** `connected`

**Payload:**
```json
{
  "message": "Successfully connected",
  "user": {
    "user_id": 5,
    "username": "alice"
  }
}
```

### 3. Obsługa Błędów (Server -> Client)

Zdarzenie emitowane w przypadku problemów z autoryzacją, walidacją danych lub błędów wewnętrznych.

**Event:** `error`

**Payload:**
```json
{
  "message": "Authentication failed: Token expired"
}
```

**Typowe przyczyny błędów:**
*   Brak tokena w parametrach `auth`.
*   Token wygasł lub jest nieprawidłowy.
*   Użytkownik nie istnieje w bazie danych.

### 4. Rozłączenie (Client <-> Server)

**Event:** `disconnect`

**Działania serwera:**
*   Usunięcie mapowania `socket.id` <-> `user_id`.
*   Aktualizacja statusu użytkownika na "offline".
*   Zwolnienie zasobów połączenia.

## Przykład Implementacji (Client-Side)

```javascript
import { io } from 'socket.io-client';

const accessToken = localStorage.getItem('access_token');

const socket = io('http://localhost:5000', {
  auth: {
    token: `Bearer ${accessToken}`
  },
  reconnection: true,
  reconnectionAttempts: 5
});

// Obsługa sukcesu
socket.on('connected', (data) => {
  console.log('Połączono jako:', data.user.username);
});

// Obsługa błędów
socket.on('connect_error', (err) => {
  console.error('Błąd połączenia:', err.message);
});

socket.on('error', (data) => {
  console.error('Błąd serwera:', data.message);
  if (data.message.includes('Token expired')) {
    // Logika odświeżania tokenu lub wylogowania
  }
});
```
