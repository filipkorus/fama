**Socket.IO — Wiadomości (messages)**

Opis eventów odpowiedzialnych za wysyłanie i pobieranie zaszyfrowanych wiadomości.

- **Wymagania**: połączenie WebSocket z autoryzacją JWT.

- **Event (client -> server):** `send_message`
  - Payload:
    - `recipient_id`: int
    - `encrypted_content`: string (Base64 AES‑GCM / inny format klienta)
    - `capsule_mlkem`: string (Base64)
    - `nonce`: string (Base64)

  - Działanie serwera:
    - Weryfikuje autoryzację użytkownika.
    - Sprawdza, czy `recipient_id` jest aktywnym użytkownikiem.
    - Zapisuje wiadomość do bazy danych (`Message`): `sender_id`, `recipient_id`, `encrypted_content`, `capsule_mlkem`, `nonce`.
    - Jeśli odbiorca jest online, oznacza wiadomość jako dostarczoną (`is_delivered = True`) i wysyła event `receive_message` do jego sesji WebSocket.

  - `receive_message` payload:
    - `id`: int (ID wiadomości)
    - `sender`: { `id`, `username` }
    - `encrypted_content`, `capsule_mlkem`, `nonce`, `is_delivered`, `created_at`

- **Event (client -> server):** `get_messages`
  - Payload:
    - `recipient_id`: int
    - `limit`: int (opcjonalne, domyślnie 50)
    - `offset`: int (opcjonalne, domyślnie 0)

  - Działanie serwera:
    - Weryfikuje autoryzację użytkownika.
    - Pobiera historię wiadomości 1:1 między użytkownikiem a `recipient_id` (sortowane malejąco po `created_at`, zwraca chronologicznie po odwróceniu).
    - Oznacza wiadomości jako dostarczone (`is_delivered = True`) dla wiadomości, które odbiorca odczytuje.
    - Emisja: `messages_history` do requestującego.

  - `messages_history` payload:
    - `messages`: [ { `id`, `recipient_id`, `encrypted_content`, `capsule_mlkem`, `nonce`, `is_delivered`, `created_at`, `sender`: {`id`, `username`} }, ... ]

- **Event (client -> server):** `get_recent_and_available_users`
  - Payload: brak

  - Działanie serwera:
    - Weryfikuje autoryzację użytkownika.
    - Pobiera listę użytkowników, z którymi użytkownik ostatnio rozmawiał, oraz innych dostępnych użytkowników.
    - Emisja: `recent_and_available_users` do requestującego.

  - `recent_and_available_users` payload:
    - `recent_users`: [ { `id`, `username`, `last_message_date` }, ... ] (posortowane malejąco po `last_message_date`)
    - `available_users`: [ { `id`, `username` }, ... ]

- **Event (server -> client):** `message_delivered`
  - Opis: Event wysyłany do nadawcy wiadomości, gdy wiadomość zostanie oznaczona jako dostarczona.
  - Payload:
    - `message_id`: int (ID dostarczonej wiadomości)
    - `recipient_id`: int (ID odbiorcy wiadomości)

  - Uwagi:
    - Klient może użyć tego eventu do aktualizacji statusu wiadomości w interfejsie użytkownika.

- **Błędy**: `error` z `{ "message": str }` przy braku autoryzacji, nieistniejącym użytkowniku lub innych błędach serwera.

Uwagi dotyczące klienta:

- Klient odpowiada za odszyfrowanie `encrypted_content` używając właściwego klucza (otrzymanego bezpiecznie przez ML‑KEM dla danego urządzenia).
- `nonce` jest wymagane do weryfikacji integralności (AES‑GCM).
- Pole `is_delivered` wskazuje, czy wiadomość została dostarczona do odbiorcy.
