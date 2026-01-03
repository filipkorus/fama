# Socket.IO — Dokumentacja Wiadomości (E2EE Session Based)

Moduł obsługuje bezpieczną wymianę wiadomości w modelu End-to-End Encryption. Klucz szyfrujący (AES) jest generowany raz, bezpiecznie wymieniany, a następnie identyfikowany za pomocą `session_key_id`.

---

## I. Zarządzanie Kluczami Sesji (Key Management)

Zanim użytkownicy wymienią wiadomości, nadawca musi opublikować klucz sesji, a odbiorca (w razie potrzeby) musi go pobrać.

### 1. Publikacja Klucza Sesji (Client -> Server)

Nadawca generuje losowy klucz AES, szyfruje go kluczem publicznym odbiorcy (ML-KEM) i wysyła na serwer. Logika: Serwer automatycznie pobiera `sender_id` z tokenu JWT nadawcy i zapisuje go w bazie powiązanego z kluczem.

**Event:** `publish_session_key`

**Payload:**

```json
{
  "recipient_id": 5,                 // ID użytkownika, dla którego jest klucz
  "capsule_mlkem": "BASE64...",      // Kapsuła ML-KEM (do wygenerowania KEK)
  "encrypted_shared_secret": "...",  // Klucz sesji (AES) zaszyfrowany przez KEK
  "key_nonce": "BASE64..."           // IV użyty do zaszyfrowania samego klucza sesji
}
```

**Odpowiedź serwera (do nadawcy):** `session_key_published`

Serwer zwraca ID, które musi być dołączane do każdej wiadomości korzystającej z tego klucza.

```json
{
  "session_key_id": 123,
  "recipient_id": 5
}
```

### 2. Żądanie Klucza Sesji (Client -> Server)

Odbiorca, widząc wiadomość z nieznanym mu `session_key_id` (nie ma go w lokalnym storage), prosi serwer o dane tego klucza.

**Event:** `request_session_key`

**Payload:**

```json
{
  "session_key_id": 123
}
```

**Odpowiedź serwera:** `session_key_data`

Zwraca dane klucza oraz informację o tym, kto go utworzył (`sender_id`).

```json
{
  "session_key_id": 123,
  "sender_id": 3,                          // WAŻNE: ID użytkownika, który wygenerował ten klucz
  "capsule_mlkem": "BASE64...",            // Użyj klucza prywatnego do dekapsulacji
  "encrypted_shared_secret": "BASE64...",  // Zaszyfrowany klucz AES
  "key_nonce": "BASE64..."                 // IV dla klucza AES
}
```

---

## II. Wymiana Wiadomości

### 1. Wysyłanie wiadomości (Client -> Server)

Wiadomość jest szyfrowana kluczem sesji (AES) uzgodnionym wcześniej.

**Event:** `send_message`

**Payload:**

```json
{
  "recipient_id": 5,
  "session_key_id": 123,         // ID klucza użytego do szyfrowania tej wiadomości
  "message_type": "text",        // "text" lub "attachment"
  "encrypted_content": "...",    // Treść wiadomości zaszyfrowana kluczem sesji
  "nonce": "BASE64..."           // Unikalny IV dla TEJ konkretnej wiadomości
}
```

**Pole `message_type`:**

* `"text"` - zwykła wiadomość tekstowa (po odszyfrowaniu: plain text)
* `"attachment"` - załącznik (po odszyfrowaniu: JSON z metadanymi pliku)

**Logika serwera:**

* Weryfikacja czy `session_key_id` istnieje.
* Walidacja `message_type` ('text' lub 'attachment').
* Zapis wiadomości w bazie wraz z `message_type`.
* Natychmiastowe dostarczenie (jeśli odbiorca online).

### 2. Odbieranie wiadomości (Server -> Client)

Event otrzymywany przez odbiorcę w czasie rzeczywistym.

**Event:** `receive_message`

**Payload:**

```json
{
  "id": 1024,
  "sender": {
    "id": 3,
    "username": "bob",
    "dilithium_public_key": "BASE64..."  // TYLKO dla message_type="attachment"
  },
  "recipient": { "id": 5 },
  "session_key_id": 123,         // Ważne: Klient sprawdza, czy ma ten klucz
  "message_type": "text",        // "text" lub "attachment"
  "encrypted_content": "BASE64...",
  "nonce": "BASE64...",
  "is_delivered": true,
  "created_at": "ISO_DATE"
}
```

**Pole `message_type` informuje frontend jak interpretować odszyfrowaną zawartość:**

* `"text"` → Po odszyfrowaniu wyświetl jako zwykły tekst
* `"attachment"` → Po odszyfrowaniu parsuj jako JSON i obsłuż jako załącznik

**WAŻNE:** Pole `sender.dilithium_public_key` jest dołączane **tylko** gdy `message_type="attachment"`. Klucz publiczny Dilithium jest wymagany do weryfikacji podpisu cyfrowego pliku przez odbiorcę.

### 3. Potwierdzenie dostarczenia (Server -> Client)

Informacja dla nadawcy.

**Event:** `message_delivered`

**Payload:**

```json
{
  "message_id": 1024,
  "recipient_id": 5
}
```

---

## III. Historia i Kontakty

### 1. Pobieranie historii czatu (Client -> Server)

**Event:** `get_messages`

**Payload:**

```json
{
  "recipient_id": 5,
  "limit": 50,
  "offset": 0
}
```

**Odpowiedź serwera:** `messages_history`

**Payload odpowiedzi:**

```json
{
  "recipient_id": 5,
  "messages": [
    {
      "id": 998,
      "message_type": "text",      // "text" lub "attachment"
      "session_key_id": 123,       // Klient używa tego ID do deszyfracji
      "encrypted_content": "...",
      "nonce": "...",
      "is_delivered": true,
      "created_at": "...",
      "sender": {
        "id": 3,
        "username": "bob",
        "dilithium_public_key": "BASE64..."  // TYLKO dla message_type="attachment"
      }
    }
  ]
}
```

**WAŻNE:** Pole `sender.dilithium_public_key` w historii wiadomości jest dołączane **tylko** gdy `message_type="attachment"`.

### 2. Lista kontaktów (Client -> Server)

Pobiera listę ostatnich rozmówców oraz dostępnych użytkowników. Ważne: Zwraca również `public_key`, który jest wymagany do rozpoczęcia szyfrowanej konwersacji.

**Event:** `get_recent_and_available_users`

**Payload:** brak (pusty obiekt `{}`)

**Odpowiedź serwera:** `recent_and_available_users`

**Payload odpowiedzi:**

```json
{
  "recent_users": [
    {
      "id": 5,
      "username": "alice",
      "public_key": "BASE64_KEY...",            // Klucz publiczny ML-KEM (do key exchange)
      "dilithium_public_key": "BASE64_KEY...",  // Klucz publiczny Dilithium (do weryfikacji podpisów)
      "last_message_date": "ISO_DATE"
    }
  ],
  "available_users": [
    { 
      "id": 8, 
      "username": "charlie",
      "public_key": "BASE64_KEY...",            // Klucz publiczny ML-KEM
      "dilithium_public_key": "BASE64_KEY..."   // Klucz publiczny Dilithium
    }
  ]
}
```

**Uwaga:** Lista kontaktów zawiera oba klucze publiczne użytkowników:

* `public_key` (ML-KEM) - do uzgadniania kluczy sesji
* `dilithium_public_key` (ML-DSA) - do weryfikacji podpisów cyfrowych plików

---

## IV. Workflow Implementacji (Client-Side)

### Scenariusz A: Nadawca wysyła wiadomość

1. Pobierz dane odbiorcy: Znajdź odbiorcę na liście kontaktów i pobierz jego `public_key`.
2. Sprawdź lokalny magazyn: Czy mam aktywny `session_key_id` dla tego `recipient_id`?
   - **TAK:** Szyfruj treść tym kluczem -> Wyślij `send_message` z tym ID.
   - **NIE:**
     1. Wygeneruj nowy klucz AES (32 bajty).
     2. Zaszyfruj klucz AES używając `public_key` odbiorcy (powstaje kapsuła ML-KEM).
     3. Wyślij `publish_session_key`.
     4. Czekaj na odpowiedź `session_key_published` z nowym ID.
     5. Zapisz niezaszyfrowany klucz AES pod otrzymanym ID w pamięci lokalnej.
     6. Wyślij wiadomość używając nowego ID.

### Scenariusz B: Odbiorca otrzymuje wiadomość

1. Otrzymujesz obiekt wiadomości z `session_key_id` (np. 123).
2. Sprawdź lokalny magazyn: Czy mam klucz AES o ID 123?
   - **TAK:** Użyj klucza oraz `nonce` (z wiadomości) do odszyfrowania `encrypted_content`.
   - **NIE:**
     1. Wyślij `request_session_key` z `{ session_key_id: 123 }`.
     2. Odbierz `session_key_data`.
     3. Sprawdź `sender_id`: Upewnij się, że klucz pochodzi od użytkownika, z którym rozmawiasz.
     4. Użyj swojego Klucza Prywatnego (ML-KEM) do dekapsulacji i odzyskania klucza AES.
     5. Zapisz odzyskany klucz AES w magazynie pod ID 123.
     6. Odszyfruj treść wiadomości.
