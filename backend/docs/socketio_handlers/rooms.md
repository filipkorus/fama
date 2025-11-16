# Socket.IO — Pokoje (rooms)

Opis eventów odpowiadających za tworzenie pokoi, zapraszanie, dołączanie i opuszczanie.

**Autoryzacja**: wszystkie eventy wymagają uprzedniego połączenia i rejestracji w `connected_users`.

**Event (client -> server):** `create_room`

- Payload:
  - `name`: string (opcjonalne)
  - `participant_ids`: [int] lista user_id do zaproszenia
  - `is_group`: bool (opcjonalne)
  - `encrypted_keys`: [{ "user_id": int, "encrypted_key": str }] (opcjonalne)

- Działanie serwera:
  - Tworzy rekord `Room`, dodaje uczestników.
  - Jeśli podano `encrypted_keys`, zapisuje `SymmetricKey` (wersja 1) dla każdego uczestnika.
  - Dołącza socket do namespace/room: `join_room('room_<id>')`.
  - Emituje `room_created` do twórcy i (opcjonalnie) do pozostałych uczestników.

**Event (client -> server):** `invite_to_room`

- Payload:
  - `room_id`: int
  - `invited_user_ids`: [int]
  - `new_encrypted_keys`: [{ "user_id": int, "encrypted_key": str }] (encrypted keys dla wszystkich uczestników, wymagane do rotacji)

- Działanie serwera:
  - Sprawdza, czy nadawca jest uczestnikiem.
  - Dodaje nowych użytkowników do `Room`.
  - Zwiększa `room.current_key_version` (rotacja klucza).
  - Oznacza stare klucze jako `revoked_at` i zapisuje nowe `SymmetricKey` dla dostarczonych danych.
  - Tworzy systemową wiadomość informującą o dołączeniu nowych użytkowników.
  - Emituje `users_invited` do pokoju (`room_<id>`).
  - Dodatkowo: serwer emituje `invited_to_room` indywidualnie do aktywnych sesji zaproszonych użytkowników (jeśli są połączeni). Ten event dostarcza szczegóły pokoju i — jeśli podano — `encrypted_key` przeznaczony dla zaproszonego.

**Event (server -> client):** `invited_to_room`

- Payload:
  - `room`: obiekt pokoju (`room.to_dict(include_participants=True)`).
  - `invited_by`: string (username inicjatora).
  - `encrypted_key`: string | null (zaszyfrowany klucz symetryczny przeznaczony dla tego użytkownika, jeśli dostarczono).
  - `new_key_version`: int (nowa wersja klucza po rotacji).

- Cel: zapewnić natychmiastowe powiadomienie zaproszonego użytkownika (jeżeli ma aktywne połączenie), nawet jeśli jeszcze nie dołączył do socket.io room.

**Event (client -> server):** `join_room`

- Payload: `{ "room_id": int }`

- Działanie serwera:
  - Sprawdza uprawnienia (użytkownik musi być w `room.participants`).
  - Dołącza socket do pokoju (`join_room`).
  - Wysyła `room_joined` do dołączającego z danymi pokoju.
  - Wysyła `user_joined` do pozostałych uczestników (include_self=False).

**Event (client -> server):** `leave_room`

- Payload:
  - `room_id`: int
  - `new_encrypted_keys`: [{ "user_id": int, "encrypted_key": str }] (opcjonalne, dla pozostałych uczestników — wymagane do bezpiecznej rotacji)

- Działanie serwera:
  - Usuwa użytkownika z `room.participants`.
  - Jeżeli po usunięciu nie ma uczestników — usuwa pokój i emituje `room_deleted`.
  - Usuwa zaszyfrowane klucze symetryczne przypisane do wychodzącego użytkownika.
  - **Nie wykonuje rotacji klucza natychmiast.** Zamiast tego serwer ustawia flagę `rotation_pending` na pokoju i:
    - próbuje od razu powiadomić jednego z pozostałych, aktywnie połączonych uczestników eventem `rotation_required` (aby to on wykonał rotację),
    - jeśli żaden pozostały uczestnik nie ma aktywnego połączenia, flaga `rotation_pending` pozostaje ustawiona — serwer powiadomi pierwszego uczestnika, który się połączy (w handlerze `connect`).
  - Tworzy systemową wiadomość o opuszczeniu (wersja klucza nie jest zmieniana przez serwer).
  - Socket opuszcza pokój (`leave_room`).
  - Emity:
    - `user_left` do pozostałych uczestników (z polem `rotation_required: true`).
    - `room_left` do użytkownika, który opuścił.
    - `room_deleted` jeśli pokój został skasowany.

**Event (server -> client):** `rotation_required`

- Payload:
  - `room_id`: int
  - `reason`: string (np. `user_left`)
  - `left_user`: { `id`, `username` } (opcjonalne)

- Cel: poinformować wybranego, połączonego uczestnika, że musi przeprowadzić rotację klucza dla pokoju (wygenerować nowy symetryczny klucz i wyśle zaszyfrowane wersje dla wszystkich aktualnych uczestników przy użyciu `rotate_room_key`).


**Błędy**: Serwer emituje `error` z payloadem `{ "message": str }` w przypadku braku autoryzacji, nieistniejącego pokoju, braku uprawnień lub nieprawidłowych danych.

Uwagi implementacyjne:

- Socket.IO używa nazw pokoi w formacie `room_<id>`; klient powinien używać powiadomień emitowanych do tego pokoju.
- Wszystkie operacje zmieniające skład uczestników (invite, leave) powinny wiązać się z rotacją klucza symetrycznego, aby zachować forward/backward secrecy — serwer wymaga od klienta dostarczenia nowych zaszyfrowanych kluczy dla wszystkich uczestników.
