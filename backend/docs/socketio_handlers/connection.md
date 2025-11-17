**Socket.IO — Połączenia**

Opis zdarzeń związanych z nawiązywaniem i zrywaniem połączeń WebSocket (Socket.IO).

- **Autoryzacja**: Połączenie wymaga tokena JWT. Klient musi podać w parametrze `auth` obiektu połączenia pole `token` o postaci `Bearer <access_token>` lub samego tokena.

- **Event (client -> server):** `connect`
  - Payload (auth param): `{ "token": "Bearer <access_token>" }`
  - Działanie serwera:
    - Weryfikuje token za pomocą `decode_token`.
    - Ładuje użytkownika i rejestruje połączenie w `connected_users` pod `request.sid`.
    - Wysyła event `connected` do klienta.
  - Response (server -> client): `connected`
    - Payload:
      {
        "message": "Successfully connected",
        "user": { "user_id": int, "username": str }
      }

- **Wspólne błędy:** Serwer używa eventu `error` do zwracania problemów związanych z autoryzacją lub innymi błędami podczas obsługi połączeń. Payload: `{ "message": str }`.
