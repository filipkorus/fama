# Socket.IO — Dokumentacja Wiadomości

Moduł obsługuje wymianę szyfrowanych wiadomości (E2EE) pomiędzy użytkownikami w czasie rzeczywistym. Mechanizm opiera się na protokole Socket.IO i wymaga wcześniejszej autoryzacji połączenia.

**Wymagania:** Aktywne połączenie WebSocket z ważnym tokenem JWT.

## Interfejs Zdarzeń (Events)

### 1. Wysyłanie wiadomości (Client -> Server)

Użytkownik wysyła zaszyfrowany payload do odbiorcy.

**Event:** `send_message`

**Payload:**
```json
{
  "recipient_id": 5,                 // ID odbiorcy
  "encrypted_content": "BASE64...",  // Treść zaszyfrowana (AES-GCM)
  "capsule_mlkem": "BASE64...",      // Kapsuła klucza sesji (ML-KEM)
  "nonce": "BASE64..."               // Initialization Vector (IV) dla AES
}
```

**Logika serwera:**
1.  Weryfikacja sesji nadawcy.
2.  Weryfikacja istnienia odbiorcy (`recipient_id`).
3.  Zapis wiadomości w bazie danych (`Message`).
4.  Sprawdzenie statusu odbiorcy:
    *   Jeśli **online**: Oznaczenie jako dostarczona (`is_delivered=True`) i natychmiastowa wysyłka (`receive_message`).
    *   Jeśli **offline**: Wiadomość oczekuje w bazie na pobranie.

### 2. Odbieranie wiadomości (Server -> Client)

Zdarzenie otrzymywane przez odbiorcę w czasie rzeczywistym.

**Event:** `receive_message`

**Payload:**
```json
{
  "id": 1024,
  "sender": {
    "id": 3,
    "username": "bob"
  },
  "encrypted_content": "BASE64...",
  "capsule_mlkem": "BASE64...",
  "nonce": "BASE64...",
  "is_delivered": true,
  "created_at": "ISO_DATE"
}
```

### 3. Pobieranie historii czatu (Client -> Server)

Pobiera historię konwersacji z konkretnym użytkownikiem.

**Event:** `get_messages`

**Payload:**
```json
{
  "recipient_id": 5,
  "limit": 50,       // Opcjonalne (domyślnie 50)
  "offset": 0        // Opcjonalne (domyślnie 0)
}
```

**Odpowiedź serwera:** `messages_history`

**Logika serwera:**
*   Pobranie wiadomości posortowanych chronologicznie.
*   Automatyczne oznaczenie nieprzeczytanych wiadomości jako dostarczone (`is_delivered=True`).

**Payload odpowiedzi:**
```json
{
  "messages": [
    {
      "id": 998,
      "sender": { "id": 3, "username": "bob" },
      "recipient_id": 5,
      "encrypted_content": "...",
      "capsule_mlkem": "...",
      "nonce": "...",
      "is_delivered": true,
      "created_at": "..."
    },
    // ...
  ]
}
```

### 4. Lista kontaktów (Client -> Server)

Pobiera listę ostatnich rozmówców oraz dostępnych użytkowników.

**Event:** `get_recent_and_available_users`

**Payload:** `brak`

**Odpowiedź serwera:** `recent_and_available_users`

**Payload odpowiedzi:**
```json
{
  "recent_users": [
    {
      "id": 5,
      "username": "alice",
      "last_message_date": "ISO_DATE"
    }
  ],
  "available_users": [
    { "id": 8, "username": "charlie" }
  ]
}
```

### 5. Potwierdzenie dostarczenia (Server -> Client)

Informacja zwrotna dla nadawcy o skutecznym dostarczeniu wiadomości do odbiorcy (lub pobraniu jej z historii).

**Event:** `message_delivered`

**Payload:**
```json
{
  "message_id": 1024,
  "recipient_id": 5
}
```

## Obsługa Błędów

W przypadku niepowodzenia operacji (np. błędny odbiorca, błąd bazy danych), serwer emituje zdarzenie `error`.

**Payload:**
```json
{
  "message": "Recipient not found"
}
```

## Uwagi Implementacyjne (Client-Side)

1.  **Kryptografia**: Serwer jest "agnostyczny" względem treści. Przekazuje zaszyfrowane payloady (`encrypted_content`, `capsule_mlkem`, `nonce`) bez ich analizy.
2.  **Odszyfrowywanie**:
    *   Klient musi użyć swojego klucza prywatnego ML-KEM do decapsulacji klucza sesji z `capsule_mlkem`.
    *   Następnie używa klucza sesji i `nonce` do odszyfrowania `encrypted_content` (AES-GCM).
3.  **Status dostarczenia**: Pole `is_delivered` oraz event `message_delivered` służą do aktualizacji UI (np. "ptaszki" przy wiadomości).
