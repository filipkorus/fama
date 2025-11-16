**Socket.IO — Wiadomości (messages)**

Opis eventów odpowiedzialnych za wysyłanie i pobieranie zaszyfrowanych wiadomości.

- **Wymagania**: połączenie oraz uczestnictwo w pokoju.

- **Event (client -> server):** `send_message`
  - Payload:
    - `room_id`: int
    - `encrypted_content`: string (Base64 AES‑GCM / inny format klienta)
    - `iv`: string (Base64)
    - `tag`: string (Base64) — (opcjonalne w zależności od algorytmu)
    - `key_version`: int
  - Działanie serwera:
    - Sprawdza, czy użytkownik jest uczestnikiem pokoju.
    - Zapisuje wiadomość do bazy (`Message`): `room_id`, `sender_id`, `encrypted_content`, `iv`, `key_version`, `message_type='user'`.
    - Emisja: `new_message` do pokoju (`room_<room_id>`).
  - `new_message` payload:
    - `message_id`, `room_id`, `sender_id`, `sender_username`, `encrypted_content`, `iv`, `key_version`, `message_type`, `created_at` (ISO)

- **Event (client -> server):** `get_messages`
  - Payload:
    - `room_id`: int
    - `limit`: int (opcjonalne, domyślnie 50)
    - `offset`: int (opcjonalne, domyślnie 0)
  - Działanie serwera:
    - Weryfikuje uprawnienia użytkownika.
    - Pobiera historię wiadomości dla pokoju (sortowane malejąco po timestamp, zwraca chronologicznie po odwróceniu).
    - Emisja: `messages_history` do requestującego.
  - `messages_history` payload:
    - `room_id`, `messages`: [ { `message_id`, `room_id`, `sender_id`, `sender_username`?, `encrypted_content`, `iv`, `tag`, `key_version`, `message_type`, `timestamp` }, ... ], `count`, `offset`, `has_more`

- **Błędy**: `error` z `{ "message": str }` przy braku autoryzacji, nieistniejącym pokojem lub braku praw do odczytu.

Uwagi dotyczące klienta:
- Klient odpowiada za odszyfrowanie `encrypted_content` używając właściwego `key_version` i lokalnie przechowywanego klucza (otrzymanego bezpiecznie przez ML‑KEM dla danego urządzenia).
- `tag` może być wymagane do weryfikacji integralności (AES‑GCM). Jeśli nie występuje, serwer nadal zapisze pole, jeśli je otrzyma.
