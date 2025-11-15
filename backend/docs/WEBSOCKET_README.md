# WebSocket API

Komunikacja real-time z uwierzytelnianiem JWT i end-to-end encryption z forward/backward secrecy.

## Quick Start

```javascript
import { io } from 'socket.io-client';

// Połącz z Access Tokenem
const socket = io('http://localhost:8080', {
  auth: { token: `Bearer ${accessToken}` }
});

// Sukces połączenia
socket.on('connected', ({ username, user_id }) => {
  console.log(`Connected as ${username}`);
});

// Błąd (brak/nieprawidłowy token)
socket.on('connect_error', (error) => {
  console.error('Auth failed:', error.message);
});
```

## Typy wiadomości

System rozróżnia dwa typy wiadomości:

### Wiadomości użytkownika (`message_type='user'`)

- Wysyłane przez użytkowników za pomocą `send_message`
- **Szyfrowane** po stronie klienta (AES-256)
- Zawierają `sender_id` i `sender_username`
- Wymagają deszyfrowania odpowiednią wersją klucza symetrycznego

### Wiadomości systemowe (`message_type='system'`)

- Automatycznie generowane przez serwer podczas zdarzeń:
  - Użytkownik dołączył do pokoju (`"X joined the room"`)
  - Użytkownik opuścił pokój (`"X left the room"`)
- **Nieszyfrowane** - plain text zakodowany w base64
- `sender_id` jest `NULL`
- Nie zawierają `sender_username` w `to_dict()`
- Klient powinien je wyświetlać bezpośrednio (po zdekodowaniu base64) bez próby deszyfrowania


**Przykład obsługi po stronie klienta**:

```javascript
function displayMessage(message) {
  if (message.message_type === 'system') {
    // System message - decode base64, no decryption
    const content = atob(message.content);
    displaySystemNotification(content);
  } else {
    // User message - decrypt with appropriate key version
    const decrypted = await decryptMessage(
      message.content,
      message.iv,
      symmetricKeys[message.key_version]
    );
    displayUserMessage(message.sender_username, decrypted);
  }
}
```

## Forward & Backward Secrecy

System implementuje **forward secrecy** i **backward secrecy** poprzez rotację kluczy symetrycznych przy zmianach uczestników pokoju.

### Kluczowe koncepcje

#### Forward Secrecy
Użytkownicy, którzy opuszczają pokój, **nie mogą odszyfrować** nowych wiadomości wysłanych po ich wyjściu.

**Implementacja**: Gdy użytkownik opuszcza pokój, generowany jest nowy klucz symetryczny i dystrybuowany do pozostałych uczestników. Stary klucz jest oznaczany jako unieważniony (`revoked_at`).

#### Backward Secrecy
Użytkownicy, którzy dołączają do pokoju, **nie mogą odszyfrować** wiadomości wysłanych przed ich dołączeniem.

**Implementacja**: Gdy użytkownik dołącza, generowany jest nowy klucz symetryczny. Stare wiadomości pozostają zaszyfrowane poprzednimi wersjami kluczy, których nowi użytkownicy nie posiadają.

### Schemat bazy danych

#### Tabela `rooms`

- `current_key_version` (Integer): Aktualna wersja klucza symetrycznego w pokoju

#### Tabela `messages`

- `key_version` (Integer): Wersja klucza użyta do zaszyfrowania tej wiadomości
- `message_type` (String(20)): Typ wiadomości - `'user'` (wysłana przez użytkownika, zaszyfrowana) lub `'system'` (informacyjna, plain text w base64)
- `sender_id` (Integer, nullable): ID użytkownika dla wiadomości typu `'user'`, `NULL` dla wiadomości systemowych

#### Tabela `symmetric_keys`

- `key_version` (Integer): Numer wersji klucza
- `revoked_at` (DateTime, nullable): Timestamp unieważnienia klucza
- **Unique constraint**: `(room_id, user_id, device_id, key_version)` - użytkownicy mogą mieć wiele wersji kluczy

### Rotacja kluczy

#### Zapraszanie użytkownika do pokoju

```javascript
// 1. Wygeneruj nowy klucz AES-256
const newSymmetricKey = generateAES256Key();

// 2. Pobierz klucze publiczne WSZYSTKICH uczestników (obecnych + zaproszonych)
const participantKeys = await getRoomKeys(room_id);

// 3. Zaszyfruj nowy klucz ML-KEM dla każdego urządzenia każdego uczestnika
const encryptedKeys = [];
for (const participant of participantKeys) {
  const encrypted = await mlKemEncrypt(participant.public_key, newSymmetricKey);
  encryptedKeys.push({
    user_id: participant.user_id,
    device_id: participant.device_id,
    encrypted_key: btoa(encrypted)
  });
}

// 4. Wyślij zaproszenie ze wszystkimi zaszyfrowanymi kluczami
socket.emit('invite_to_room', {
  room_id: room_id,
  invited_user_ids: [new_user_id],
  new_encrypted_keys: encryptedKeys  // Klucze dla WSZYSTKICH uczestników
});
```

**Proces serwera**:
1. Weryfikacja, czy zapraszający jest uczestnikiem
2. Dodanie nowych użytkowników do `room.participants`
3. Inkrementacja `room.current_key_version`
4. Oznaczenie starych kluczy jako unieważnione
5. Zapisanie nowych kluczy dla WSZYSTKICH uczestników z nową wersją
6. Emisja zdarzenia `key_rotated` do wszystkich uczestników

**Rezultat**:
- Zaproszeni użytkownicy otrzymują tylko nowy klucz → **nie mogą odszyfrować starych wiadomości**
- Istniejący użytkownicy zachowują dostęp do wszystkich wersji kluczy → **mogą odszyfrować wszystkie wiadomości**

#### Opuszczanie pokoju (z rotacją kluczy)

```javascript
// 1. Wygeneruj nowy klucz AES-256
const newSymmetricKey = generateAES256Key();

// 2. Pobierz klucze pozostałych uczestników (bez siebie)
const remainingParticipants = await getRoomKeys(room_id);
const filteredParticipants = remainingParticipants.filter(p => p.user_id !== my_user_id);

// 3. Zaszyfruj dla pozostałych uczestników
const encryptedKeys = [];
for (const participant of filteredParticipants) {
  const encrypted = await mlKemEncrypt(participant.public_key, newSymmetricKey);
  encryptedKeys.push({
    user_id: participant.user_id,
    device_id: participant.device_id,
    encrypted_key: btoa(encrypted)
  });
}

// 4. Opuść pokój
socket.emit('leave_room', {
  room_id: room_id
});

// 5. Pozostali uczestnicy nasłuchują na user_left_room
socket.on('user_left_room', (data) => {
  if (data.requires_key_rotation) {
    // Jeden z pozostałych uczestników rotuje klucz
    rotateRoomKey(data.room_id);
  }
});

async function rotateRoomKey(room_id) {
  // 1. Wygeneruj nowy klucz symetryczny
  const newSymmetricKey = generateAESKey();

  // 2. Pobierz klucze publiczne WSZYSTKICH obecnych uczestników
  const participants = await getRoomParticipants(room_id);

  // 3. Zaszyfruj nowy klucz dla każdego uczestnika
  const encryptedKeys = [];
  for (const participant of participants) {
    const encrypted = await mlKemEncrypt(participant.public_key, newSymmetricKey);
    encryptedKeys.push({
      user_id: participant.user_id,
      device_id: participant.device_id,
      encrypted_key: btoa(encrypted)
    });
  }

  // 4. Wyślij nowe klucze
  socket.emit('rotate_room_key', {
    room_id: room_id,
    new_encrypted_keys: encryptedKeys
  });
}
```

**Rezultat**:
- Opuszczający użytkownik zachowuje stare klucze → **może odszyfrować stare wiadomości**
- Opuszczający użytkownik NIE otrzymuje nowego klucza → **nie może odszyfrować nowych wiadomości**
- Rotacja kluczy wykonana przez pozostałych uczestników → **bezpieczniejsze**

### Wysyłanie i odbieranie wiadomości

#### Wysyłanie zaszyfrowanej wiadomości

```javascript
// Pobierz aktualny klucz symetryczny dla pokoju
const currentKeyVersion = room.current_key_version;
const encryptedSymmetricKey = room.encrypted_symmetric_keys[currentKeyVersion];

// Odszyfruj klucz symetryczny używając ML-KEM
const symmetricKey = await mlKemDecrypt(myPrivateKey, atob(encryptedSymmetricKey));

// Wygeneruj IV i zaszyfruj wiadomość AES-256
const iv = generateRandomIV();
const encryptedContent = await aesEncrypt(symmetricKey, messageText, iv);

// Wyślij zaszyfrowaną wiadomość
socket.emit('send_message', {
  room_id: room_id,
  encrypted_content: btoa(encryptedContent),
  iv: btoa(iv),
  key_version: currentKeyVersion  // Opcjonalne, domyślnie current_key_version
});
```

#### Odbieranie i deszyfrowanie wiadomości

```javascript
// Pobierz historię wiadomości
socket.emit('get_room_messages', { room_id: room_id, limit: 50 });

socket.on('room_messages', async (data) => {
  const { messages, encrypted_symmetric_keys, current_key_version } = data;

  // Odszyfruj wszystkie wersje kluczy symetrycznych
  const decryptedKeys = {};
  for (const [version, encryptedKey] of Object.entries(encrypted_symmetric_keys)) {
    decryptedKeys[version] = await mlKemDecrypt(myPrivateKey, atob(encryptedKey));
  }

  // Odszyfruj wiadomości
  for (const message of messages) {
    const symmetricKey = decryptedKeys[message.key_version];
    if (!symmetricKey) {
      console.warn(`No key for version ${message.key_version}`);
      continue;  // Nie mamy klucza - wiadomość sprzed naszego dołączenia
    }

    const decryptedText = await aesDecrypt(
      symmetricKey,
      atob(message.encrypted_content),
      atob(message.iv)
    );

    displayMessage(message.sender_username, decryptedText);
  }
});
```

#### Obsługa rotacji kluczy

```javascript
// Nasłuchuj na zdarzenia rotacji kluczy
socket.on('key_rotated', async (data) => {
  const { room_id, new_key_version, reason } = data;
  console.log(`Key rotated in room ${room_id} to version ${new_key_version}, reason: ${reason}`);

  // Pobierz nowe klucze
  socket.emit('get_room_messages', { room_id: room_id, limit: 0 });  // Tylko klucze, bez wiadomości
});
```

## Events API

### Zarządzanie pokojami

#### `create_room`
Tworzy nowy pokój z opcjonalnym E2E encryption.

**Client → Server**:
```json
{
  "name": "Mój pokój",
  "participant_ids": [2, 3],
  "is_group": true,
  "encrypted_keys": [
    {
      "user_id": 1,
      "device_id": 1,
      "encrypted_key": "base64_encrypted_aes_key_for_user1_device1"
    },
    {
      "user_id": 2,
      "device_id": 2,
      "encrypted_key": "base64_encrypted_aes_key_for_user2_device2"
    }
  ]
}
```

**Server → Client**:
```json
{
  "room": {
    "id": 123,
    "name": "Mój pokój",
    "is_group": true,
    "current_key_version": 1,
    "participants": [...]
  }
}
```

#### `invite_to_room`
Zaprasza użytkowników do pokoju. **WYMAGA** nowych kluczy dla WSZYSTKICH uczestników (forward/backward secrecy).

**Client → Server**:
```json
{
  "room_id": 123,
  "invited_user_ids": [5, 6],
  "new_encrypted_keys": [
    // Klucze dla WSZYSTKICH uczestników (istniejących + zaproszonych)
    { "user_id": 1, "device_id": 1, "encrypted_key": "..." },
    { "user_id": 2, "device_id": 2, "encrypted_key": "..." },
    { "user_id": 5, "device_id": 3, "encrypted_key": "..." }
  ]
}
```

**Server → Client**:
```json
{
  "room_id": 123,
  "invited_users": [
    { "id": 5, "username": "user5" }
  ],
  "new_key_version": 2
}
```

**Emitowane zdarzenia**:
- `key_rotated` - do wszystkich uczestników
- `user_joined_room` - dla każdego nowego użytkownika

#### `leave_room`
Opuszcza pokój. Po wyjściu użytkownika, pozostali uczestnicy powinni wywołać `rotate_room_key` dla forward secrecy.

**Client → Server**:
```json
{
  "room_id": 123
}
```

**Server → Client** (do pozostałych uczestników):
```json
{
  "room_id": 123,
  "user_id": 1,
  "username": "jan",
  "requires_key_rotation": true  // Sygnał, że rotacja kluczy jest zalecana
}
```

#### `rotate_room_key`
Rotuje klucz symetryczny w pokoju (forward secrecy). Może być wywołane przez dowolnego obecnego uczestnika po tym, jak ktoś opuści pokój, lub przez pierwszego uczestnika, który się połączy, jeśli rotacja jest oczekująca.

**Client → Server**:
```json
{
  "room_id": 123,
  "new_encrypted_keys": [  // Nowe klucze dla WSZYSTKICH obecnych uczestników
    { "user_id": 2, "device_id": 2, "encrypted_key": "..." },
    { "user_id": 3, "device_id": 3, "encrypted_key": "..." }
  ]
}
```

**Server → Client** (broadcast do wszystkich w pokoju):
```json
{
  "room_id": 123,
  "new_key_version": 3,
  "reason": "manual_rotation",
  "rotated_by": "jan"
}
```

#### `get_rooms`
Pobiera listę pokoi użytkownika.

**Client → Server**:
```json
{}
```

**Server → Client** (callback response):
```json
{
  "rooms": [
    {
      "id": 123,
      "name": "Pokój 1",
      "is_group": true,
      "current_key_version": 3,
      "created_at": "2025-01-15T10:00:00",
      "participants": [
        {
          "id": 1,
          "username": "user1"
        }
      ]
    }
  ]
}
```

**Uwagi**:
- Endpoint używa callback pattern - response zwracany jest jako return value, nie przez emit
- Zwraca tylko pokoje, w których użytkownik jest uczestnikiem

#### `get_room_keys`
Pobiera klucze publiczne wszystkich uczestników pokoju (do szyfrowania nowych kluczy symetrycznych).

**Client → Server**:
```json
{
  "room_id": 123
}
```

**Server → Client** (callback response):
```json
{
  "room_id": 123,
  "participant_keys": [
    {
      "user_id": 1,
      "username": "user1",
      "device_id": 1,
      "device_name": "Chrome on Windows",
      "public_key": "base64_ml_kem_public_key"
    },
    {
      "user_id": 2,
      "username": "user2",
      "device_id": 3,
      "device_name": "Firefox on Linux",
      "public_key": "base64_ml_kem_public_key"
    }
  ]
}
```

**Uwagi**:
- Endpoint używa callback pattern
- Tylko uczestnicy pokoju mogą pobrać klucze
- Zwraca wszystkie urządzenia wszystkich uczestników

### Wiadomości

#### `send_message`
Wysyła zaszyfrowaną wiadomość do pokoju.

**Client → Server**:
```json
{
  "room_id": 123,
  "encrypted_content": "base64_aes_encrypted_message",
  "iv": "base64_initialization_vector",
  "key_version": 2  // Opcjonalne, domyślnie current_key_version
}
```

**Server → Client** (event `new_message` - broadcast do wszystkich w pokoju):
```json
{
  "id": 456,
  "room_id": 123,
  "sender_id": 1,
  "sender_username": "user1",
  "message_type": "user",
  "encrypted_content": "base64_aes_encrypted_message",
  "iv": "base64_initialization_vector",
  "key_version": 2,
  "created_at": "2025-01-15T10:30:00"
}
```

**Uwagi**:
- Tylko uczestnicy pokoju mogą wysyłać wiadomości
- Jeśli `key_version` nie jest podane, używa `room.current_key_version`
- Wiadomość jest zapisywana w bazie danych i broadcastowana do wszystkich uczestników
- Nadawca również otrzymuje kopię wiadomości (echo)

#### `get_room_messages`
Pobiera historię wiadomości z pokoju wraz z WSZYSTKIMI wersjami kluczy symetrycznych użytkownika.

**Client → Server**:
```json
{
  "room_id": 123,
  "limit": 50,      // Opcjonalne, domyślnie 50
  "offset": 0       // Opcjonalne, domyślnie 0
}
```

**Server → Client** (callback response):
```json
{
  "room_id": 123,
  "messages": [
    {
      "id": 1,
      "message_type": "user",
      "encrypted_content": "...",
      "iv": "...",
      "key_version": 1,
      "sender_id": 1,
      "sender_username": "user1",
      "created_at": "2025-01-15T10:00:00"
    },
    {
      "id": 2,
      "message_type": "system",
      "encrypted_content": "dXNlcjIgam9pbmVkIHRoZSByb29t",  // base64: "user2 joined the room"
      "iv": "MDAwMDAwMDAwMDAwMDAwMA==",
      "key_version": 2,
      "sender_id": null,
      "created_at": "2025-01-15T10:30:00"
    },
    {
      "id": 3,
      "message_type": "user",
      "encrypted_content": "...",
      "iv": "...",
      "key_version": 2,
      "sender_id": 2,
      "sender_username": "user2",
      "created_at": "2025-01-15T11:00:00"
    }
  ],
  "encrypted_symmetric_keys": {
    "1": "base64_encrypted_key_version_1",
    "2": "base64_encrypted_key_version_2",
    "3": "base64_encrypted_key_version_3"
  },
  "current_key_version": 3,
  "has_more": true
}
```

**Uwagi**:
- Endpoint używa callback pattern
- Tylko uczestnicy pokoju mogą pobrać wiadomości
- Użytkownik otrzymuje tylko te wersje kluczy, które posiadał (był uczestnikiem podczas ich ważności)
- Brak klucza dla danej wersji = wiadomość sprzed dołączenia użytkownika (backward secrecy)
- `encrypted_symmetric_keys` są zwracane jako dict z key_version jako kluczem
- Wiadomości systemowe (`message_type='system'`):
  - Mają `sender_id=null` i nie zawierają `sender_username`
  - Content jest plain text zakodowany w base64 (nie wymaga deszyfrowania)
  - Generowane automatycznie dla zdarzeń: user joined, user left

#### `exchange_key`
Wymienia zaszyfrowane klucze symetryczne między uczestnikami (np. dodanie nowego urządzenia).

**Client → Server**:
```json
{
  "room_id": 123,
  "encrypted_keys": [
    {
      "user_id": 1,
      "device_id": 2,
      "encrypted_key": "base64_encrypted_key",
      "key_version": 2  // Opcjonalne, domyślnie current_key_version
    }
  ]
}
```

**Server → Client** (event `key_exchanged`):
```json
{
  "room_id": 123,
  "key_version": 2,
  "from_user_id": 1,
  "from_username": "user1"
}
```

**Uwagi**:
- Tylko uczestnicy pokoju mogą wymieniać klucze
- Jeśli klucz dla danej kombinacji (user_id, device_id, key_version) już istnieje, zostanie zaktualizowany
- Event `key_exchanged` jest emitowany do nadawcy i broadcastowany do innych uczestników pokoju

### Zdarzenia serwera (Server-to-Client Events)

#### `connected`
Emitowane po udanym połączeniu.

```json
{
  "username": "user1",
  "user_id": 1,
  "device_id": 1
}
```

#### `connected`
Emitowane po udanym połączeniu WebSocket z uwierzytelnieniem JWT.

```json
{
  "username": "user1",
  "user_id": 1,
  "device_id": 1
}
```

#### `new_message`
Emitowane gdy nowa wiadomość jest wysłana do pokoju (broadcast do wszystkich uczestników).

```json
{
  "id": 456,
  "room_id": 123,
  "sender_id": 1,
  "sender_username": "user1",
  "message_type": "user",
  "encrypted_content": "base64_aes_encrypted_message",
  "iv": "base64_initialization_vector",
  "key_version": 2,
  "created_at": "2025-01-15T10:30:00"
}
```

#### `room_created`
Emitowane po utworzeniu pokoju.

```json
{
  "room": {
    "id": 123,
    "name": "Nowy pokój",
    "is_group": true,
    "current_key_version": 1,
    "participants": [...]
  },
  "created_by": "user1",
  "encryption_setup": true
}
```

#### `users_invited`
Emitowane po zaproszeniu użytkowników do pokoju.

```json
{
  "room_id": 123,
  "invited_users": [
    { "id": 5, "username": "user5" }
  ],
  "new_key_version": 2
}
```

#### `key_rotated`
Emitowane gdy klucz symetryczny pokoju został zrotowany (broadcast do wszystkich uczestników).

```json
{
  "room_id": 123,
  "new_key_version": 3,
  "reason": "new_participants" | "manual_rotation",
  "rotated_by": "user1"  // Tylko dla manual_rotation
}
```

**Akcja klienta**: Pobierz nowe klucze poprzez `get_room_messages`.

#### `user_joined_room`
Emitowane gdy nowy użytkownik dołącza do pokoju (broadcast do wszystkich uczestników).

```json
{
  "room_id": 123,
  "user_id": 5,
  "username": "newuser"
}
```

**Uwaga**: Dodatkowo tworzona jest automatyczna wiadomość systemowa "newuser joined the room".

#### `user_left_room`
Emitowane gdy użytkownik opuszcza pokój (broadcast do pozostałych uczestników).

```json
{
  "room_id": 123,
  "user_id": 5,
  "username": "user5",
  "requires_key_rotation": true
}
```

**Uwagi**:
- `requires_key_rotation=true` sygnalizuje, że pozostali uczestnicy powinni wywołać `rotate_room_key` dla forward secrecy
- Automatycznie tworzona jest wiadomość systemowa "user5 left the room"

#### `room_left`
Emitowane do użytkownika, który właśnie opuścił pokój (potwierdzenie operacji).

```json
{
  "room_id": 123,
  "message": "Successfully left room 123"
}
```

#### `key_exchanged`
Emitowane po wymianie kluczy symetrycznych.

```json
{
  "room_id": 123,
  "key_version": 2,
  "from_user_id": 1,
  "from_username": "user1"
}
```

#### `error`
Emitowane w przypadku błędu operacji.

```json
{
  "message": "Error description"
}
```

**Przykładowe błędy**:
- "Not authenticated"
- "Room not found"
- "Not a participant of this room"
- "Only participants can invite others to the room"
- "Must provide keys for ALL current participants"

## Gwarancje bezpieczeństwa

**Forward Secrecy**: Użytkownik opuszczający pokój nie może odszyfrować przyszłych wiadomości

**Backward Secrecy**: Nowy użytkownik nie może odszyfrować wiadomości wysłanych przed jego dołączeniem

**Zachowanie historii**: Istniejący użytkownicy mogą odszyfrować wszystkie swoje historyczne wiadomości

**Szyfrowanie per-urządzenie**: Każde urządzenie ma osobno zaszyfrowany klucz

**Wersjonowanie kluczy**: Wszystkie klucze są śledzone z numerami wersji dla prawidłowego deszyfrowania

**Autoryzacja**: Wszystkie operacje wymagają uwierzytelnienia JWT i weryfikacji członkostwa w pokoju

## Obsługa błędów i odświeżanie tokena

```javascript
socket.on('error', async (data) => {
  if (data.message.includes('Not authenticated')) {
    const newToken = await refreshAccessToken();
    socket.auth.token = `Bearer ${newToken}`;
    socket.connect();
  }
});
```
