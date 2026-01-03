# Bezpieczny Transfer Plików z Podpisami Cyfrowymi

## Przegląd

System transferu plików wykorzystuje schemat "Encrypted Attachment" z podpisami cyfrowymi CRYSTALS-Dilithium (ML-DSA) zapewniając:

* **Poufność**: Pliki szyfrowane efemerycznymi kluczami AES
* **Autentyczność**: Pliki podpisane kluczem prywatnym nadawcy Dilithium
* **Integralność**: Haszowanie SHA-256 zapewnia integralność pliku
* **Niezaprzeczalność**: Podpisy Dilithium dowodzą tożsamości nadawcy

---

## Definicje Kluczy

**Identity_Priv_Key (Dilithium)**: Prywatny klucz Alice. Służy do podpisywania plików. **NIGDY nie opuszcza urządzenia.**

**Identity_Pub_Key (Dilithium)**: Publiczny klucz Alice (Bob go ma). Służy do weryfikacji podpisów.

**Session_Key (AES)**: Klucz, który Alice i Bob już mają uzgodniony (z Kybera). Służy do szyfrowania wiadomości na czacie (Socket.IO).

**Ephemeral_File_Key (AES)**: Nowy, losowy klucz generowany tylko dla jednego pliku. Po jednorazowym użyciu.

---

## Pełny Przepływ Danych - Krok po Kroku

### FAZA 1: Nadawca (Alice) - Przygotowanie i Upload

**Krok 1: Wczytaj plik**
* **Gdzie:** Frontend (przeglądarka Alice)
* **Co:** Użytkownik wybiera plik przez `<input type="file">`
* **Dane wejściowe:** Plik z dysku użytkownika
* **Dane wyjściowe:** `fileBytes` (Uint8Array)

**Krok 2: Stwórz metadane pliku**
* **Gdzie:** Frontend (przeglądarka Alice)
* **Co:** Utwórz JSON z nazwą pliku, typem MIME, rozmiarem, timestamp
* **Dane wyjściowe:** `metadataBytes` (Uint8Array z zakodowanym JSON)
* **Przykład Metadata JSON:**
  ```json
  {
    "filename": "dokument.pdf",
    "mime_type": "application/pdf",
    "size": 1048576,
    "timestamp": "2025-12-01T12:34:56Z"
  }
  ```

**Krok 3: Podpisz plik kluczem Dilithium**
* **Gdzie:** Frontend (przeglądarka Alice)
* **Co:** Użyj prywatnego klucza Dilithium (z localStorage) do podpisania `fileBytes`
* **Dane wejściowe:** `fileBytes`, `dilithium_private_key`
* **Dane wyjściowe:** `signatureBytes` (Uint8Array ~2420 bajtów dla Dilithium3)
* **⚠️ WAŻNE:** Klucz prywatny NIGDY nie opuszcza urządzenia!

**Krok 4: Spakuj binarnie (Binary Packing)**
* **Gdzie:** Frontend (przeglądarka Alice)
* **Co:** Połącz w jeden bufor: `[Sig_Len(4B)][Meta_Len(4B)][Metadata][Signature][File]`
* **Dane wejściowe:** `signatureBytes`, `metadataBytes`, `fileBytes`
* **Dane wyjściowe:** `RAW_PAYLOAD` (Uint8Array)
* **Format binarny:**
  ```
  ┌─────────────────────────────────────────────┐
  │ Signature_Length (4 bajty, uint32, BE)      │
  ├─────────────────────────────────────────────┤
  │ Metadata_Length (4 bajty, uint32, BE)       │
  ├─────────────────────────────────────────────┤
  │ Metadata_JSON (UTF-8)                       │
  ├─────────────────────────────────────────────┤
  │ Dilithium_Signature (~2420B dla Dilithium3) │
  ├─────────────────────────────────────────────┤
  │ File_Bytes (pozostałe bajty)                │
  └─────────────────────────────────────────────┘
  ```

**Krok 5: Generuj efemeryczny klucz AES**
* **Gdzie:** Frontend (przeglądarka Alice)
* **Co:** Wygeneruj losowy klucz AES-256 (32 bajty) i IV (12 bajtów)
* **Dane wyjściowe:** `ephemeralFileKey`, `fileIV`
* **⚠️ WAŻNE:** Klucz używany tylko dla TEGO jednego pliku!

**Krok 6: Zaszyfruj RAW_PAYLOAD**
* **Gdzie:** Frontend (przeglądarka Alice)
* **Co:** Zaszyfruj `RAW_PAYLOAD` używając AES-GCM z `ephemeralFileKey` i `fileIV`
* **Dane wejściowe:** `RAW_PAYLOAD`, `ephemeralFileKey`, `fileIV`
* **Dane wyjściowe:** `encryptedBlob` (Uint8Array)
* **⚠️ Co jest zaszyfrowane:** Podpis + Metadane + Plik

**Krok 7: Upload do serwera**
* **Gdzie:** Frontend → Backend
* **Co:** Wyślij `encryptedBlob` przez HTTP POST
* **Endpoint:** `POST /api/files/upload`
* **Format:** `multipart/form-data`
* **Nagłówki:** `Authorization: Bearer <jwt_token>`
* **Payload:** `file: encryptedBlob` (jako Blob)
* **⚠️ Serwer otrzymuje:** Tylko zaszyfrowany blob (nie może go odszyfrować!)

**Krok 8: Serwer przetwarza upload**
* **Gdzie:** Backend
* **Co:**
  1. Zapisz `encryptedBlob` na dysku z losową nazwą UUID
  2. Oblicz SHA-256 hash zaszyfrowanego blob'a
  3. Zwróć URL, filename, size, hash
* **Dane wyjściowe (JSON):**
  ```json
  {
    "url": "/api/files/download/abc123def456.enc",
    "filename": "abc123def456.enc",
    "size": 1234567,
    "hash": "sha256_hex_hash_of_encrypted_blob",
    "uploaded_at": "2025-12-01T12:34:56Z"
  }
  ```
* **⚠️ Serwer NIE MA dostępu do:** Podpisu, metadanych, pliku, klucza

### FAZA 2: Nadawca (Alice) - Wysłanie Klucza przez Socket.IO

**Krok 9: Utwórz Attachment Metadata**
* **Gdzie:** Frontend (przeglądarka Alice)
* **Co:** Utwórz JSON z informacjami potrzebnymi do odszyfrowania
* **Struktura JSON:**
  ```json
  {
    "url": "/api/files/download/abc123.enc",
    "key": "base64_encoded_ephemeral_key",
    "iv": "base64_encoded_iv",
    "hash": "sha256_hex",
    "metadata": {
      "filename": "dokument.pdf",
      "size": 1048576,
      "mime_type": "application/pdf"
    }
  }
  ```
* **Dane wyjściowe:** `attachmentMetadata` (JSON object)

**Krok 10: Zaszyfruj Attachment Metadata z Session Key**
* **Gdzie:** Frontend (przeglądarka Alice)
* **Co:** Zaszyfruj `attachmentMetadata` używając Session_Key (uzgodniony wcześniej przez Kyber)
* **Dane wejściowe:** `attachmentMetadata`, `sessionKey`, `sessionNonce` (losowy)
* **Dane wyjściowe:** `encryptedContent` (Base64)
* **⚠️ Session_Key:** To klucz AES już uzgodniony między Alice i Bobem przez ML-KEM (Kyber)

**Krok 11: Wyślij wiadomość przez Socket.IO**
* **Gdzie:** Frontend → Backend
* **Co:** Wyślij zaszyfrowaną wiadomość typu "attachment"
* **Event:** `send_message`
* **Payload (wysłany do backendu):**
  ```javascript
  {
    recipient_id: 2,                    // ID odbiorcy (Bob)
    session_key_id: 123,                // ID klucza sesji w bazie
    message_type: "attachment",         // Typ: "text" lub "attachment"
    encrypted_content: "base64...",     // Zaszyfrowany JSON (Session_Key)
    nonce: "base64..."                  // IV użyty do szyfrowania
  }
  ```
* **⚠️ Backend otrzymuje:** Zaszyfrowaną wiadomość (nie może jej odszyfrować!)
* **⚠️ Co jest w encrypted_content:** Zaszyfrowany `attachmentMetadata` z kroku 9

**Krok 12: Backend zapisuje i przekazuje**
* **Gdzie:** Backend
* **Co:**
  1. Zapisz wiadomość w bazie danych (z polem `message_type = 'attachment'`)
  2. Przekaż przez WebSocket do Boba (jeśli online)
* **Event wysłany do Boba:** `receive_message`
* **Payload (otrzymany przez Boba):**
  ```javascript
  {
    id: 456,                              // ID wiadomości w bazie
    sender: {
      id: 1,
      username: "alice",
      dilithium_public_key: "base64..."   // Klucz do weryfikacji podpisu!
    },
    recipient: { id: 2 },
    session_key_id: 123,
    message_type: "attachment",           // Typ wiadomości
    encrypted_content: "base64...",       // Ten sam co w kroku 11
    nonce: "base64...",                   // Ten sam co w kroku 11
    created_at: "2025-12-01T12:34:56Z"
  }
  ```
* **⚠️ WAŻNE:** Pole `sender.dilithium_public_key` potrzebne do weryfikacji podpisu (krok 20)

### FAZA 3: Odbiorca (Bob) - Odbiór i Weryfikacja

**Krok 13: Odbierz wiadomość Socket.IO**
* **Gdzie:** Frontend (przeglądarka Boba)
* **Co:** Nasłuchuj na event `receive_message`
* **Dane wejściowe:** Payload z kroku 12
* **Co sprawdzić:** `message_type === 'attachment'`

**Krok 14: Odszyfruj encrypted_content z Session Key**
* **Gdzie:** Frontend (przeglądarka Boba)
* **Co:** Użyj Session_Key do odszyfrowania `encrypted_content`
* **Dane wejściowe:** `encryptedContent`, `sessionKey`, `sessionNonce`
* **Dane wyjściowe:** `attachmentMetadata` (JSON z kroku 9)
* **⚠️ Teraz Bob ma:** `{ url, key, iv, hash, metadata }`

**Krok 15: Pobierz zaszyfrowany blob z serwera**
* **Gdzie:** Frontend → Backend
* **Co:** Pobierz plik z URL otrzymanego w `attachmentMetadata.url`
* **Endpoint:** `GET /api/files/download/<filename>`
* **Nagłówki:** `Authorization: Bearer <jwt_token>`
* **Dane wyjściowe:** `encryptedBlob` (Uint8Array)

**Krok 16: Weryfikuj hash integralności (opcjonalnie)**
* **Gdzie:** Frontend (przeglądarka Boba)
* **Co:** Oblicz SHA-256 hash pobranego `encryptedBlob` i porównaj z `attachmentMetadata.hash`
* **Jeśli różne:** Rzuć błąd - plik został zmodyfikowany podczas transferu!

**Krok 17: Odszyfruj blob z Ephemeral File Key**
* **Gdzie:** Frontend (przeglądarka Boba)
* **Co:** Użyj klucza i IV z `attachmentMetadata` do odszyfrowania blob'a
* **Dane wejściowe:** `encryptedBlob`, `fileKey` (z Base64), `fileIV` (z Base64)
* **Dane wyjściowe:** `RAW_PAYLOAD` (Uint8Array)
* **⚠️ Teraz Bob ma:** Rozpakowany payload `[SigLen|MetaLen|Meta|Sig|File]`

**Krok 18: Rozpakuj dane binarne**
* **Gdzie:** Frontend (przeglądarka Boba)
* **Co:** Wyciągnij z `RAW_PAYLOAD` poszczególne części (najpierw długości, potem metadane, podpis i plik)
* **Dane wyjściowe:**
  * `signatureBytes` - Podpis Dilithium
  * `metadata` - JSON z nazwą pliku, typem, rozmiarem
  * `fileBytes` - Surowe bajty pliku

**Krok 19: Pobierz publiczny klucz Dilithium nadawcy**
* **Gdzie:** Frontend (przeglądarka Boba)
* **Co:** Pobierz `dilithium_public_key` Alice z obiektu `sender`
* **Skąd:** Z danych użytkownika (zwrócone przez backend w `receive_message`)
* **⚠️ WAŻNE:** To klucz publiczny Alice zapisany podczas rejestracji

**Krok 20: Weryfikuj podpis Dilithium**
* **Gdzie:** Frontend (przeglądarka Boba)
* **Co:** Zweryfikuj czy podpis pasuje do pliku używając publicznego klucza Alice
* **Dane wejściowe:** `dilithium_public_key` (Alice), `fileBytes`, `signatureBytes`
* **Dane wyjściowe:** `isValid` (boolean)
* **Algorytm:** Dilithium3 (lub inny wariant)

**Krok 21: Decyzja na podstawie weryfikacji**
* **Gdzie:** Frontend (przeglądarka Boba)
* **Jeśli `isValid === true`:**
  * Podpis prawidłowy - plik autentyczny
  * Wyświetl/pobierz plik
  * Utwórz Blob URL i pokaż użytkownikowi
* **Jeśli `isValid === false`:**
  * Podpis nieprawidłowy - plik sfałszowany lub zmodyfikowany
  * Pokaż błąd użytkownikowi
  * NIE wyświetlaj pliku

---

## Podsumowanie: Co trafia do serwera?

**Backend OTRZYMUJE (zaszyfrowane, nie może odszyfrować):**

1. **POST /api/files/upload:**
   * `encryptedBlob` - zaszyfrowany `[SigLen|MetaLen|Meta|Sig|File]`
   * Serwer NIE widzi: podpisu, metadanych, pliku

2. **Socket.IO send_message:**
   * `encrypted_content` - zaszyfrowany JSON `{url, key, iv, hash, metadata}`
   * Serwer NIE widzi: klucza do pliku, nazwy pliku, rozmiaru

**Backend PRZECHOWUJE:**
* Zaszyfrowane blob'y na dysku
* Zaszyfrowane wiadomości w bazie danych
* Hash zaszyfrowanych blob'ów (do weryfikacji integralności)

**Backend NIE MA DOSTĘPU DO:**
* Podpisów Dilithium (zaszyfrowane w blob'ie)
* Kluczy do odszyfrowania plików (`ephemeralFileKey`)
* Zawartości plików
* Metadanych plików (nazwa, typ)
* Klucza sesji (`Session_Key`)

---

## ETAP 1: Przygotowanie Payloadu (Frontend Nadawcy)

Przygotowanie danych do wysłania w pamięci przeglądarki (JavaScript).

### Krok 1.1: Wczytaj plik

```javascript
const file = event.target.files[0];
const fileBytes = new Uint8Array(await file.arrayBuffer());
```

### Krok 1.2: Stwórz metadane

```javascript
const metadata = {
  filename: file.name,           // "foto.jpg"
  mime_type: file.type,          // "image/jpeg"
  size: file.size,               // 1048576
  timestamp: new Date().toISOString()
};

// Zamień JSON na bajty UTF-8
const metadataJson = JSON.stringify(metadata);
const metadataBytes = new TextEncoder().encode(metadataJson);
```

### Krok 1.3: Podpisz plik

```javascript
import { DigitalSignature } from './crypto/digital_signature';

// Pobierz swój prywatny klucz Dilithium z localStorage
const myDilithiumPrivateKey = localStorage.getItem('dilithium_private_key');

// Oblicz hash pliku (SHA-256 lub SHAKE)
const fileHash = await crypto.subtle.digest('SHA-256', fileBytes);

// Wygeneruj podpis Dilithium
const signer = new DigitalSignature('Dilithium3');
const signatureBytes = await signer.sign(myDilithiumPrivateKey, fileBytes);

// signatureBytes to Uint8Array o długości ~2420 bajtów dla Dilithium3
```

### Krok 1.4: Pakowanie binarne (Binary Packing)

Połącz wszystkie komponenty w jeden bufor binarny w określonej kolejności. Użyj formatu **Big-Endian** dla długości.

```javascript
/**
 * Format RAW_PAYLOAD:
 * [4 bajty: Długość Podpisu (uint32, big-endian)]
 * [4 bajty: Długość Metadanych (uint32, big-endian)]
 * [Metadane (MetadataBytes)]
 * [Podpis (SignatureBytes)]
 * [Plik (FileBytes)]
 */

function packBinaryData(signatureBytes, metadataBytes, fileBytes) {
  const sigLen = signatureBytes.length;
  const metaLen = metadataBytes.length;
  
  // Całkowity rozmiar bufora
  const totalSize = 4 + 4 + metaLen + sigLen + fileBytes.length;
  const buffer = new Uint8Array(totalSize);
  
  let offset = 0;
  
  // 1. Długość podpisu (4 bajty, big-endian)
  const sigLenView = new DataView(buffer.buffer, offset, 4);
  sigLenView.setUint32(0, sigLen, false); // false = big-endian
  offset += 4;
  
  // 2. Długość metadanych (4 bajty, big-endian)
  const metaLenView = new DataView(buffer.buffer, offset, 4);
  metaLenView.setUint32(0, metaLen, false);
  offset += 4;
  
  // 3. Metadane
  buffer.set(metadataBytes, offset);
  offset += metaLen;
  
  // 4. Podpis
  buffer.set(signatureBytes, offset);
  offset += sigLen;
  
  // 5. Plik
  buffer.set(fileBytes, offset);
  
  return buffer; // To jest RAW_PAYLOAD
}

const rawPayload = packBinaryData(signatureBytes, metadataBytes, fileBytes);
```

---

## ETAP 2: Szyfrowanie Pliku (Frontend Nadawcy)

Zaszyfrowanie payloadu przy użyciu efemerycznego klucza AES-GCM.

### Krok 2.1: Generuj klucz efemeryczny

```javascript
// Generuj losowy 32-bajtowy klucz AES-256
const ephemeralFileKey = crypto.getRandomValues(new Uint8Array(32));

// Generuj losowe 12 bajtów IV (dla AES-GCM)
const fileIV = crypto.getRandomValues(new Uint8Array(12));
```

### Krok 2.2: Szyfruj z AES-GCM

```javascript
async function encryptPayload(key, iv, data) {
  // Import klucza do Web Crypto API
  const cryptoKey = await crypto.subtle.importKey(
    'raw',
    key,
    { name: 'AES-GCM' },
    false,
    ['encrypt']
  );
  
  // Zaszyfruj dane
  const encryptedBuffer = await crypto.subtle.encrypt(
    { name: 'AES-GCM', iv: iv },
    cryptoKey,
    data
  );
  
  return new Uint8Array(encryptedBuffer);
}

const encryptedBlob = await encryptPayload(ephemeralFileKey, fileIV, rawPayload);
```

**Wynik:** `encryptedBlob` to `Uint8Array` zawierający zaszyfrowane dane.

---

## ETAP 3: Upload na Serwer (HTTP REST)

Wyślij zaszyfrowany blob na serwer przez HTTP.

### Krok 3.1: Wyślij POST request

```javascript
async function uploadEncryptedFile(encryptedBlob) {
  const formData = new FormData();
  
  // Zamień Uint8Array na Blob
  const blob = new Blob([encryptedBlob], { type: 'application/octet-stream' });
  formData.append('file', blob, 'encrypted.bin');
  
  // Wyślij z JWT tokenem
  const response = await fetch('/api/files/upload', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('access_token')}`
    },
    body: formData
  });
  
  if (!response.ok) {
    throw new Error('Upload failed');
  }
  
  return await response.json();
}

const uploadResult = await uploadEncryptedFile(encryptedBlob);
// uploadResult = { url, filename, size, hash, uploaded_at }
```

### Krok 3.2: Odpowiedź serwera

Serwer zwraca:

```json
{
  "url": "/api/files/download/abc123def456.enc",
  "filename": "abc123def456.enc",
  "size": 1234567,
  "hash": "sha256_hex_hash_of_encrypted_blob",
  "uploaded_at": "2025-12-01T12:34:56Z"
}
```

---

## ETAP 4: Przekazanie Klucza Szyfrowania (Socket.IO)

Przekaz odbiorcy zaszyfrowane informacje niezbędne do odszyfrowania pliku.

### Krok 4.1: Stwórz obiekt wiadomości (Attachment Metadata)

```javascript
import { toBase64 } from './services/message';

// Zakoduj klucz i IV do Base64 (dla łatwiejszego przesyłania)
const base64FileKey = toBase64(ephemeralFileKey);
const base64FileIV = toBase64(fileIV);

// Attachment metadata - to będzie zaszyfrowane Session_Key
const attachmentMetadata = {
  url: uploadResult.url,           // URL do pobrania pliku
  key: base64FileKey,              // Klucz do odszyfrowania
  iv: base64FileIV,                // IV do odszyfrowania
  hash: uploadResult.hash,         // Hash dla weryfikacji integralności
  metadata: {
    filename: metadata.filename,
    size: metadata.size,
    mime_type: metadata.mime_type
  }
};
```

### Krok 4.2: Zaszyfruj wiadomość z Session Key

```javascript
import { encryptMessage } from './services/message';

/**
 * Session Key to klucz AES uzgodniony między Alice i Bobem
 * za pomocą Kyber (ML-KEM) podczas inicjalizacji sesji czatu.
 */

// Pobierz Session Key dla danego odbiorcy (wcześniej uzgodniony przez Kyber)
const sessionKeyBase64 = getSessionKeyForRecipient(recipientId);

// Zamień attachmentMetadata na JSON string
const messageJson = JSON.stringify(attachmentMetadata);

// Zaszyfruj używając encryptMessage (zwraca { encryptedContent, nonce })
const { encryptedContent, nonce } = await encryptMessage(
  sessionKeyBase64,
  messageJson
);
```

### Krok 4.3: Wyślij przez Socket.IO

```javascript
socket.emit('send_message', {
  recipient_id: recipientId,
  session_key_id: sessionKeyId,
  message_type: 'attachment',  // Typ wiadomości: 'text' lub 'attachment'
  encrypted_content: encryptedContent,  // Zaszyfrowany JSON z attachment metadata
  nonce: nonce  // IV użyty do szyfrowania (już w Base64)
});
```

**Pole `message_type`:**
* `'attachment'` - wiadomość zawiera załącznik (plik)
* `'text'` - wiadomość zawiera zwykły tekst

**Backend zapisuje `message_type` w bazie i przekazuje do odbiorcy przez WebSocket.**

---

## ETAP 5: Odbiór i Weryfikacja (Frontend Odbiorcy)

Bob otrzymuje wiadomość na Socket.IO i musi ją przetworzyć.

### Krok 5.1: Odbierz wiadomość Socket.IO

```javascript
import { decryptMessage } from './services/message';

socket.on('receive_message', async (data) => {
  const { 
    sender, 
    message_type,
    encrypted_content, 
    nonce, 
    session_key_id 
  } = data;
  
  // Pobierz Session Key dla tej sesji (Base64)
  const sessionKeyBase64 = getSessionKeyById(session_key_id);
  
  // Odszyfruj zawartość wiadomości (nonce już w Base64)
  const decryptedMessage = await decryptMessage(
    sessionKeyBase64,
    encrypted_content,
    nonce
  );
  
  // Parse JSON (tylko jeśli message_type === 'attachment')
  // Dla 'text' można bezpośrednio wyświetlić decryptedMessage
  
  if (message_type === 'attachment') {
    const attachmentData = JSON.parse(decryptedMessage);
    await handleAttachment(attachmentData, sender);
  } else if (message_type === 'text') {
    displayTextMessage(decryptedMessage, sender);
  }
});
```

### Krok 5.2: Odszyfruj Socket message

```javascript
import { decryptMessage } from './services/message';

// Użyj decryptMessage z message.ts
// Zwraca odszyfrowany string (JSON)
async function decryptSocketMessage(sessionKeyBase64, encryptedContentBase64, nonceBase64) {
  return await decryptMessage(sessionKeyBase64, encryptedContentBase64, nonceBase64);
}
```

### Krok 5.3: Pobierz zaszyfrowany blob

```javascript
import { fromBase64 } from './services/message';

async function handleAttachment(attachmentData, sender) {
  const { url, key, iv, hash, metadata } = attachmentData;
  
  // Pobierz zaszyfrowany plik z serwera
  const response = await fetch(url, {
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('access_token')}`
    }
  });
  
  if (!response.ok) {
    throw new Error('Failed to download file');
  }
  
  const encryptedBlob = new Uint8Array(await response.arrayBuffer());
  
  // Weryfikuj hash integralności (opcjonalnie)
  const downloadedHash = await computeSHA256(encryptedBlob);
  if (downloadedHash !== hash) {
    throw new Error('File integrity check failed');
  }
  
  // Odszyfruj blob
  const fileKey = fromBase64(key);
  const fileIV = fromBase64(iv);
  
  const rawPayload = await decryptPayload(fileKey, fileIV, encryptedBlob);
  
  // Rozpakuj i zweryfikuj
  await unpackAndVerify(rawPayload, sender, metadata);
}
```

### Krok 5.4: Odszyfruj payload

```javascript
async function decryptPayload(key, iv, encryptedData) {
  const cryptoKey = await crypto.subtle.importKey(
    'raw',
    key,
    { name: 'AES-GCM' },
    false,
    ['decrypt']
  );
  
  const decryptedBuffer = await crypto.subtle.decrypt(
    { name: 'AES-GCM', iv: iv },
    cryptoKey,
    encryptedData
  );
  
  return new Uint8Array(decryptedBuffer);
}
```

### Krok 5.5: Rozpakuj dane binarne

```javascript
function unpackBinaryData(buffer) {
  let offset = 0;
  
  // 1. Czytaj długość podpisu (4 bajty, big-endian)
  const sigLenView = new DataView(buffer.buffer, offset, 4);
  const sigLen = sigLenView.getUint32(0, false); // false = big-endian
  offset += 4;

  // 2. Czytaj długość metadanych (4 bajty, big-endian)
  const metaLenView = new DataView(buffer.buffer, offset, 4);
  const metaLen = metaLenView.getUint32(0, false);
  offset += 4;

  // 3. Wytnij metadane
  const metadataBytes = buffer.slice(offset, offset + metaLen);
  const metadataJson = new TextDecoder().decode(metadataBytes);
  const metadata = JSON.parse(metadataJson);
  offset += metaLen;

  // 4. Wytnij podpis
  const signatureBytes = buffer.slice(offset, offset + sigLen);
  offset += sigLen;

  // 5. Reszta to plik
  const fileBytes = buffer.slice(offset);

  return {
    signature: signatureBytes,
    metadata: metadata,
    file: fileBytes
  };
}
```

### Krok 5.6: Weryfikuj podpis Dilithium

```javascript
async function unpackAndVerify(rawPayload, sender, expectedMetadata) {
  // Rozpakuj dane
  const { signature, metadata, file } = unpackBinaryData(rawPayload);
  
  // Pobierz publiczny klucz Dilithium nadawcy
  const senderDilithiumPublicKey = sender.dilithium_public_key;
  
  if (!senderDilithiumPublicKey) {
    throw new Error('Sender Dilithium public key not found');
  }
  
  // Weryfikuj podpis
  const verifier = new DigitalSignature('Dilithium3');
  const isValid = await verifier.verify(
    senderDilithiumPublicKey,
    file,
    signature
  );
  
  if (!isValid) {
    // PODPIS NIEPRAWIDŁOWY - PLIK FAŁSZYWY LUB ZMODYFIKOWANY
    alert('BŁĄD: Podpis cyfrowy nieprawidłowy! Plik może być fałszywy.');
    console.error('Signature verification failed for file:', metadata.filename);
    return;
  }
  
  // PODPIS PRAWIDŁOWY - można zaufać plikowi
  console.log('Signature verified successfully');
  
  // Wyświetl/pobierz plik
  displayFile(file, metadata);
}
```

### Krok 5.7: Wyświetl plik

```javascript
function displayFile(fileBytes, metadata) {
  // Utwórz Blob z odpowiednim typem MIME
  const blob = new Blob([fileBytes], { type: metadata.mime_type });
  const blobUrl = URL.createObjectURL(blob);
  
  // Jeśli to obrazek, wyświetl
  if (metadata.mime_type.startsWith('image/')) {
    const img = document.createElement('img');
    img.src = blobUrl;
    document.getElementById('chat-container').appendChild(img);
  } else {
    // Dla innych plików, stwórz link do pobrania
    const link = document.createElement('a');
    link.href = blobUrl;
    link.download = metadata.filename;
    link.textContent = `${metadata.filename} (${formatFileSize(metadata.size)})`;
    document.getElementById('chat-container').appendChild(link);
  }
}

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}
```

---

## Kompletna Funkcja: `uploadAndSendFile`

Oto pełna implementacja funkcji łączącej wszystkie etapy:

```javascript
import { DigitalSignature } from './crypto/digital_signature';
import { encryptMessage, toBase64 } from './services/message';

/**
 * Przesyła plik z podpisem cyfrowym do odbiorcy
 * @param {File} file - Plik wybrany przez użytkownika
 * @param {string} sessionKey - Klucz sesji AES w Base64 (uzgodniony przez Kyber)
 * @param {string} myDilithiumPrivateKey - Prywatny klucz Dilithium nadawcy (Base64)
 * @param {number} recipientId - ID odbiorcy
 * @param {number} sessionKeyId - ID klucza sesji w bazie danych
 */
async function uploadAndSendFile(
  file,
  sessionKey,
  myDilithiumPrivateKey,
  recipientId,
  sessionKeyId
) {
  try {
    // === ETAP 1: Przygotowanie danych ===
    
    // 1.1 Wczytaj plik
    const fileBytes = new Uint8Array(await file.arrayBuffer());
    
    // 1.2 Stwórz metadane
    const metadata = {
      filename: file.name,
      mime_type: file.type,
      size: file.size,
      timestamp: new Date().toISOString()
    };
    const metadataBytes = new TextEncoder().encode(JSON.stringify(metadata));
    
    // 1.3 Podpisz plik Dilithium
    const signer = new DigitalSignature('Dilithium3');
    const signatureBytes = await signer.sign(myDilithiumPrivateKey, fileBytes);
    
    // 1.4 Spakuj binarnie
    const rawPayload = packBinaryData(signatureBytes, metadataBytes, fileBytes);
    
    // === ETAP 2: Szyfrowanie ===
    
    // 2.1 Generuj efemeryczny klucz
    const ephemeralFileKey = crypto.getRandomValues(new Uint8Array(32));
    const fileIV = crypto.getRandomValues(new Uint8Array(12));
    
    // 2.2 Zaszyfruj payload
    const encryptedBlob = await encryptPayload(ephemeralFileKey, fileIV, rawPayload);
    
    // === ETAP 3: Upload na serwer ===
    
    const uploadResult = await uploadEncryptedFile(encryptedBlob);
    console.log('File uploaded:', uploadResult.url);
    
    // === ETAP 4: Wyślij metadata przez Socket.IO ===
    
    // 4.1 Przygotuj attachment metadata (bez pola 'type')
    const attachmentMetadata = {
      url: uploadResult.url,
      key: toBase64(ephemeralFileKey),
      iv: toBase64(fileIV),
      hash: uploadResult.hash,
      metadata: {
        filename: metadata.filename,
        size: metadata.size,
        mime_type: metadata.mime_type
      }
    };
    
    // 4.2 Zaszyfruj z Session Key
    const messageJson = JSON.stringify(attachmentMetadata);
    const { encryptedContent, nonce } = await encryptMessage(
      sessionKey,
      messageJson
    );
    
    // 4.3 Wyślij przez Socket.IO z message_type
    socket.emit('send_message', {
      recipient_id: recipientId,
      session_key_id: sessionKeyId,
      message_type: 'attachment',  // <-- Określa typ wiadomości
      encrypted_content: encryptedContent,
      nonce: nonce  // Już w Base64
    });
    
    console.log('File sent successfully');
    
  } catch (error) {
    console.error('Error sending file:', error);
    throw error;
  }
}
```
