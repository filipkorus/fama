**Socket.IO — Przegląd eventów**

Krótki przegląd wszystkich eventów Socket.IO używanych w backendzie i ich kierunek.

- **connect** (client -> server)
  - Autoryzacja: `auth.token` (Bearer)
  - Server -> client: `connected` (z danymi użytkownika i pokojów)

- **disconnect** (server event)
  - Serwer reaguje na rozłączenie i czyści `connected_users`.

- **create_room** (client -> server)
  - Server -> client/room: `room_created`

- **invite_to_room** (client -> server)
  - Server -> room: `users_invited`

- **join_room** (client -> server)
  - Server -> client: `room_joined`
  - Server -> room: `user_joined`

- **leave_room** (client -> server)
  - Server -> room: `user_left`
  - Server -> client: `room_left`
  - Server -> room (if empty): `room_deleted`
  - Server -> participant(s): `rotation_required` (targeted to a connected participant to perform key rotation)

- **send_message** (client -> server)
  - Server -> room: `new_message`

- **get_messages** (client -> server)
  - Server -> client: `messages_history`

- **rotate_room_key** (client -> server)
  - Server -> participant SID: `key_rotated` (dla każdego uczestnika indywidualnie)

- **rotation_required** (server -> client)
  - Sent when the server requires a currently connected participant to initiate key rotation (e.g., after someone left). If no participant is connected, the server sets `rotation_pending` and will notify the first participant who connects.

- **error** (server -> client)
  - Wspólny event błędów: `{ "message": str }`.

Ważne: wszystkie eventy modyfikujące listę uczestników wymagają rotacji klucza symetrycznego — serwer oczekuje od klienta dostarczenia zaszyfrowanych kluczy (`encrypted_key`) dla każdej aktualnej instancji użytkownika.
