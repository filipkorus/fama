# Dokumentacja API Użytkowników

Moduł API użytkowników umożliwia wyszukiwanie kont oraz pobieranie ich kluczy publicznych ML-KEM, niezbędnych do procesu szyfrowania komunikacji.

**Wymagana autoryzacja:**
Token JWT (Access Token) w nagłówku `Authorization`.

Base URL: `/api/users`

## Specyfikacja Endpointów

### 1. Wyszukiwanie użytkowników

**Endpoint:** `GET /api/users/search`

Wyszukuje użytkowników na podstawie fragmentu nazwy. Obsługuje paginację.

**Parametry (Query):**
*   `query` (string, wymagane): Fragment nazwy użytkownika (min. 2 znaki).
*   `page` (int, opcjonalne): Numer strony (domyślnie 1).
*   `per_page` (int, opcjonalne): Wyników na stronę (domyślnie 10, max 50).

**Odpowiedź (200 OK):**
```json
{
  "users": [
    {
      "user_id": 5,
      "username": "alice",
      "public_key": "BASE64_STRING..."
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 10,
    "total_count": 1,
    "total_pages": 1,
    "has_next": false,
    "has_prev": false
  }
}
```

**Błędy:**
*   `400`: Parametr `query` pusty lub krótszy niż 2 znaki.
*   `401`: Brak autoryzacji.

### 2. Pobieranie klucza (przez ID)

**Endpoint:** `GET /api/users/<user_id>/public-key`

Pobiera klucz publiczny użytkownika na podstawie numerycznego identyfikatora.

**Parametry (Path):**
*   `user_id` (int): ID użytkownika.

**Odpowiedź (200 OK):**
```json
{
  "user_id": 5,
  "username": "alice",
  "public_key": "BASE64_STRING..."
}
```

**Błędy:**
*   `404`: Użytkownik nie istnieje.

### 3. Pobieranie klucza (przez Username)

**Endpoint:** `GET /api/users/<username>/public-key`

Pobiera klucz publiczny użytkownika na podstawie nazwy.

**Parametry (Path):**
*   `username` (string): Nazwa użytkownika.

**Odpowiedź (200 OK):**
```json
{
  "user_id": 5,
  "username": "alice",
  "public_key": "BASE64_STRING..."
}
```

**Błędy:**
*   `404`: Użytkownik nie istnieje.

## Przykład Implementacji (Client-Side)

Poniższy kod demonstruje pobranie klucza publicznego i wykorzystanie go do zaszyfrowania klucza sesji (KEM Encapsulation).

```javascript
import axios from 'axios';

// Pobieranie danych użytkownika
async function getUserPublicKey(username) {
  const accessToken = localStorage.getItem('access_token');
  const response = await axios.get(
    `/api/users/${encodeURIComponent(username)}/public-key`,
    { headers: { 'Authorization': `Bearer ${accessToken}` } }
  );
  return response.data;
}

// Scenariusz: Zaproszenie do szyfrowanego pokoju
async function inviteUserToRoom(roomId, username) {
  try {
    // 1. Pobierz klucz publiczny odbiorcy
    const { user_id, public_key } = await getUserPublicKey(username);

    // 2. Pobierz klucz symetryczny pokoju (lokalny kontekst)
    const roomKey = getRoomSymmetricKey(roomId);

    // 3. ML-KEM Encapsulation (Szyfrowanie klucza pokoju)
    const encryptedKey = await mlKemEncapsulate(public_key, roomKey);

    // 4. Wyślij zaproszenie (WebSocket)
    socket.emit('invite_user', {
      room_id: roomId,
      user_id: user_id,
      encrypted_key: encryptedKey
    });

  } catch (error) {
    console.error('Encryption/Invite error:', error);
  }
}
```

## Charakterystyka Techniczna

**Wyszukiwanie:**
*   Case-insensitive (nie rozróżnia wielkości liter).
*   Dopasowanie częściowe (substring match).
*   Limit paginacji: 50 rekordów.

**Klucze Publiczne:**
*   Format: Base64.
*   Zgodność: ML-KEM (Kyber).
*   Rozmiary (po dekodowaniu):
    *   Kyber512: 800 bajtów
    *   Kyber768: 1184 bajty
    *   Kyber1024: 1568 bajtów
