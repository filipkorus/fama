# API Użytkowników - Dokumentacja

## Przegląd

Moduł API użytkowników zapewnia endpointy do wyszukiwania użytkowników oraz pobierania ich kluczy publicznych ML-KEM. Jest to niezbędne do:
- Znajdowania użytkowników w celu zaproszenia do pokoju
- Pobierania kluczy publicznych do szyfrowania wiadomości
- Implementacji funkcji wyszukiwania użytkowników w aplikacji

> **Uwaga:** Wszystkie endpointy wymagają autoryzacji za pomocą JWT access token.

## Endpointy API

Wszystkie endpointy znajdują się pod prefiksem `/api/users`.

### 1. Wyszukiwanie użytkowników

**Endpoint:** `GET /api/users/search`

**Opis:** Wyszukuje użytkowników po username z obsługą paginacji. Zwraca listę użytkowników wraz z ich kluczami publicznymi ML-KEM.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `query` (wymagane) - Fragment username do wyszukania (minimum 2 znaki)
- `page` (opcjonalne) - Numer strony (domyślnie 1)
- `per_page` (opcjonalne) - Liczba wyników na stronę (domyślnie 10, maksimum 50)

**Odpowiedź sukcesu (200):**

```json
{
  "users": [
    {
      "user_id": 5,
      "username": "alice",
      "public_key": "OwOc0pQrXx..."
    },
    {
      "user_id": 8,
      "username": "alice123",
      "public_key": "BwXz1mNsYy..."
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 10,
    "total_count": 2,
    "total_pages": 1,
    "has_next": false,
    "has_prev": false
  }
}
```

**Błędy:**
- `400` - Brak parametru query lub query za krótkie (< 2 znaki)
- `401` - Nieprawidłowy lub brakujący access token
- `500` - Błąd serwera

---

### 2. Pobieranie klucza publicznego użytkownika po ID

**Endpoint:** `GET /api/users/<user_id>/public-key`

**Opis:** Pobiera klucz publiczny ML-KEM konkretnego użytkownika na podstawie jego ID.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Path Parameters:**
- `user_id` - ID użytkownika (integer)

**Odpowiedź sukcesu (200):**

```json
{
  "user_id": 5,
  "username": "alice",
  "public_key": "OwOc0pQrXx..."
}
```

**Błędy:**
- `401` - Nieprawidłowy lub brakujący access token
- `404` - Użytkownik o podanym ID nie istnieje
- `500` - Błąd serwera

---

### 3. Pobieranie klucza publicznego użytkownika po username

**Endpoint:** `GET /api/users/<username>/public-key`

**Opis:** Pobiera klucz publiczny ML-KEM konkretnego użytkownika na podstawie jego username. Alternatywa do pobierania po ID.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Path Parameters:**
- `username` - Nazwa użytkownika (string)

**Odpowiedź sukcesu (200):**

```json
{
  "user_id": 5,
  "username": "alice",
  "public_key": "OwOc0pQrXx..."
}
```

**Błędy:**
- `401` - Nieprawidłowy lub brakujący access token
- `404` - Użytkownik o podanym username nie istnieje
- `500` - Błąd serwera

**Przykład użycia:**

```javascript
import axios from 'axios';

// Funkcja pomocnicza do pobierania klucza publicznego
async function getUserPublicKey(username) {
  const accessToken = localStorage.getItem('access_token');

  const response = await axios.get(
    `/api/users/${encodeURIComponent(username)}/public-key`,
    {
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    }
  );

  return response.data;
}

// Przykład: Zapraszanie użytkownika do pokoju
async function inviteUserToRoom(roomId, username) {
  try {
    // 1. Pobierz klucz publiczny użytkownika
    const userData = await getUserPublicKey(username);
    console.log(`Pobrano klucz publiczny użytkownika ${userData.username}`);

    // 2. Wygeneruj lub pobierz klucz symetryczny pokoju
    const roomSymmetricKey = getRoomSymmetricKey(roomId);

    // 3. Zaszyfruj klucz symetryczny używając klucza publicznego ML-KEM
    const encryptedKey = await mlKemEncapsulate(
      userData.public_key, 
      roomSymmetricKey
    );

    // 4. Wyślij zaproszenie przez WebSocket
    socket.emit('invite_user', {
      room_id: roomId,
      user_id: userData.user_id,
      encrypted_key: encryptedKey
    });

    console.log(`Wysłano zaproszenie do użytkownika ${username}`);
  } catch (error) {
    if (error.response?.status === 404) {
      console.error('Użytkownik nie istnieje');
    } else {
      console.error('Błąd podczas zapraszania użytkownika:', error);
    }
  }
}
```

---

## Szczegóły implementacji

### Wyszukiwanie użytkowników

- **Wyszukiwanie case-insensitive** - wielkość liter nie ma znaczenia
- **Częściowe dopasowanie** - znajduje użytkowników zawierających fragment query w username
- **Paginacja** - automatyczna obsługa stron dla dużej liczby wyników
- **Limit wyników** - maksymalnie 50 wyników na stronę dla wydajności

### Klucze publiczne

- **Format:** Base64-encoded ML-KEM public key
- **Rozmiar:** 800 bytes (Kyber512), 1184 bytes (Kyber768), lub 1568 bytes (Kyber1024) po dekodowaniu
- **Użycie:** Do enkapsulacji kluczy symetrycznych przy zapraszaniu użytkowników do pokojów
