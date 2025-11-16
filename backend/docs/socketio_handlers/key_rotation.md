**Socket.IO — Rotacja kluczy (key rotation)**

Eventy i zachowania związane z rotacją symetrycznych kluczy używanych do E2E szyfrowania w pokojach.

**Cel**: zapewnić forward i backward secrecy — po dodaniu lub usunięciu uczestnika należy zwiększyć `key_version` i rozesłać nowe zaszyfrowane klucze tylko aktualnym uczestnikom.

**Pomocnicze funkcje serwera**:
- `rotate_room_keys_for_user(user_id)` — inkrementuje `current_key_version` dla pokoi użytkownika i oznacza stare klucze jako zrevokowane; NIE zapisuje nowych zaszyfrowanych kluczy (to pozostawiono klientowi/serverowi wywołującemu operację rotacji).

Nota o inicjacji rotacji:
- Serwer może ustawić flagę `rotation_pending` na `Room` (np. gdy użytkownik opuści pokój). W takim przypadku serwer nie wykonuje rotacji automatycznie — informuje jednego z aktywnie połączonych uczestników (event `rotation_required`) albo, jeśli żaden nie jest podłączony, powiadomi pierwszego uczestnika, który się połączy.

**Event (client -> server):** `rotate_room_key`

- Payload:
  - `room_id`: int
  - `new_encrypted_keys`: [{ "user_id": int, "encrypted_key": str }]  # wymagane — klucze dla wszystkich aktualnych uczestników

- Działanie serwera:
  - Weryfikuje, że nadawca jest uczestnikiem pokoju.
  - Sprawdza, że `new_encrypted_keys` zawiera wpisy dla wszystkich bieżących uczestników.
  - Zwiększa `room.current_key_version`.
  - Oznacza stare klucze jako `revoked_at`.
  - Zapisuje nowe `SymmetricKey` (dla każdego `user_id` z `new_encrypted_keys`).
  - Emituje `key_rotated` indywidualnie do sesji każdego uczestnika (wysyłane do SID klienta), payload zawiera `encrypted_key` przeznaczony dla tego uczestnika.

**`key_rotated` payload:**
- `room_id`, `new_key_version`, `reason` (np. `manual_rotation`), `rotated_by` (username inicjatora), `encrypted_key` (Base64 dla tej sesji/użytkownika)

**Błędy**: `error` gdy brak autoryzacji, brak `new_encrypted_keys`, brak pokoju lub gdy nie dostarczono kluczy dla wszystkich uczestników.

Uwagi:
- Rotacja powinna być koordynowana po stronie klientów: uczestnicy generują nowy symetryczny klucz i każda instancja szyfruje go osobno dla klucza publicznego urządzenia pozostałych uczestników (ML‑KEM). Serwer tylko przechowuje zaszyfrowane wersje klucza i przekazuje odpowiedni kawałek do każdego urządzenia.
