**Socket.IO — Połączenia**

Opis zdarzeń związanych z nawiązywaniem i zrywaniem połączeń WebSocket (Socket.IO).

- **Autoryzacja**: Połączenie wymaga tokena JWT. Klient musi podać w parametrze `auth` obiektu połączenia pole `token` o postaci `Bearer <access_token>` lub samego tokena.

- **Event (client -> server):** `connect`
  - Payload (auth param): `{ "token": "Bearer <access_token>" }`
  - Działanie serwera:
    - Weryfikuje token za pomocą `decode_token`.
    - Ładuje użytkownika i listę pokoi, w których uczestniczy.
    - Przygotowuje zaszyfrowane klucze symetryczne (wersje) dla danego użytkownika.
    - Rejestruje połączenie w `connected_users` pod `request.sid`.
    - Wysyła event `connected` do klienta.
    - Po wysłaniu `connected` serwer może również wysłać event `rotation_required` dla pokoi, które mają ustawioną flagę `rotation_pending` — wskazuje to, że klient powinien przeprowadzić rotację klucza dla danego pokoju.
  - Response (server -> client): `connected`
    - Payload:
      {
        "message": "Successfully connected",
        "user": {...},                # pełne dane użytkownika (z `to_dict()`)
        "rooms": [                    # lista pokoi użytkownika
          {
            "room": {...},            # room.to_dict(include_participants=False)
            "participants": [        # lista uczestników z public_key
              {"user_id": int, "username": str, "public_key": str}, ...
            ],
            "encrypted_symmetric_keys": { key_version: encrypted_key, ... }
          }, ...
        ]
      }

- **Event (server side):** `disconnect`
  - Działanie serwera: usuwa wpis `connected_users[request.sid]` i loguje rozłączenie.
  - Nie wysyła specjalnego potwierdzenia do klienta (jest to zakończenie połączenia).

- **Wspólne błędy:** Serwer używa eventu `error` do zwracania problemów związanych z autoryzacją lub innymi błędami podczas obsługi połączeń. Payload: `{ "message": str }`.

Uwagi bezpieczeństwa:
- Token powinien być krótkożyjący (access token). Po stronie klienta odświeżanie tokenów powinno następować przed wygaśnięciem.
- Serwer nie odsłania prywatnych danych urządzeń — jedynie `public_key` każdego uczestnika.
