# Bezpieczny transfer plików z podpisami PQC

## Przegląd

System implementuje bezpieczny transfer załączników w czacie E2EE, oparty o:

- **Poufność** – treść pliku jest szyfrowana efemerycznym kluczem AES‑GCM, unikalnym dla każdego załącznika.
- **Autentyczność i niezaprzeczalność** – nadawca podpisuje hash pliku podpisem post‑kwantowym (CRYSTALS‑Dilithium / ML‑DSA‑65); odbiorca weryfikuje podpis wyłącznie w swojej przeglądarce.
- **Integralność** – haszowanie SHA‑256 wykrywa każdą modyfikację zarówno zaszyfrowanego bloba na serwerze, jak i odszyfrowanego pliku.
- **Silne E2EE** – serwer nigdy nie ma dostępu do kluczy plików, kluczy sesji, metadanych plików ani ich zawartości; widzi jedynie zaszyfrowane blob'y i ciphertexty metadanych.

Rozwiązanie łączy efemeryczne szyfrowanie załącznika z istniejącym E2EE czatu (Session Key negocjowany ML‑KEM), dzięki czemu pliki są traktowane jak „specjalny rodzaj wiadomości”, a nie osobny kanał o słabszym modelu zagrożeń.

---

## Model kluczy i zaufania

System używa czterech rodzajów kluczy kryptograficznych:

- **Identity key (Dilithium / ML‑DSA‑65)**  
  - Para \[publiczny, prywatny] generowana w przeglądarce użytkownika.  
  - Prywatny klucz służy wyłącznie do podpisywania hashy plików i **nigdy nie opuszcza urządzenia** (przechowywany np. w `localStorage` lub bezpiecznym storage).  
  - Publiczny klucz jest publikowany przy rejestracji i udostępniany odbiorcom w metadanych użytkownika.  

- **Session Key (AES dla czatu)**  
  - Wspólny klucz symetryczny uzgadniany 1‑razowo między rozmówcami za pomocą ML‑KEM (Kyber), a następnie przechowywany po stronie klienta.  
  - Służy do szyfrowania wszystkich wiadomości czatu (tekst + metadane załączników) przez Socket.IO.  

- **Ephemeral File Key (AES dla załącznika)**  
  - Losowy klucz AES‑256 generowany *per plik* wraz z losowym IV AES‑GCM.  
  - Służy tylko do zaszyfrowania pojedynczego RAW payloadu `[podpis | metadane | plik]` i nigdy nie jest znany serwerowi; trafia wyłącznie do odbiorcy, zaszyfrowany Session Key.  

- **Klucze serwerowe**  
  - Serwer przechowuje jedynie klucze do własnej bazy/pliku (np. TLS, klucz JWT), ale nie posiada materiału, który pozwoliłby odszyfrować pliki lub wiadomości użytkowników.  

Zaufanie opiera się na:

- poprawnym przypisaniu klucza publicznego Dilithium do konta użytkownika,  
- bezpiecznym negocjowaniu Session Key (w osobnym protokole E2EE czatu),  
- fakcie, że każdy załącznik jest podpisany i szyfrowany przez nadawcę lokalnie, a serwer pełni wyłącznie rolę magazynu ciphertextów.

---

## Architektura przepływu załącznika

### 1. Nadawca – przygotowanie i upload (frontend)

1. **Odczyt pliku i metadanych**  
   - przeglądarka wczytuje plik jako `Uint8Array` i generuje metadane: nazwa, MIME, rozmiar, timestamp.  

2. **Podpis PQC**  
   - z prywatnym kluczem Dilithium obliczany jest hash pliku (SHA‑256), a następnie podpis ML‑DSA‑65; podpis i hash pozostają wyłącznie po stronie klienta.  

3. **Pakowanie RAW payloadu**  
   - tworzony jest binarny bufor:  
     \[sigLen(4B) | metaLen(4B) | metadataJSON | signature | fileBytes] – taki format pozwala jednoznacznie odzyskać metadane, podpis i plik po odszyfrowaniu.  

4. **Efemeryczne szyfrowanie pliku**  
   - generowany jest jednorazowy `Ephemeral_File_Key` AES‑256 oraz IV; RAW payload jest szyfrowany AES‑GCM → powstaje `encryptedBlob`.  

5. **Upload na serwer**  
   - `encryptedBlob` jest wysyłany jako `multipart/form-data` na `POST /api/files/upload`.  
   - Backend zapisuje blob pod losową nazwą, liczy SHA‑256 ciphertextu i zapamiętuje go w tabeli `uploaded_files` (hash *zaszyfrowanego* pliku).  
   - Odpowiedź zawiera tylko: `{ url, filename, size, hash, uploaded_at }`.  

Na tym etapie serwer widzi wyłącznie zaszyfrowany blob i jego hash – nie zna ani metadanych, ani podpisu, ani oryginalnej zawartości.

### 2. Nadawca – przekazanie klucza i metadanych (Socket.IO)

1. **Attachment metadata**  
   - w przeglądarce powstaje obiekt metadanych:  
     `{ type: 'file', url, filename, encrypted_hash, file_key, file_iv, file_hash, signature, signer_public_key, mime_type, original_size, original_filename, uploaded_at, ... }`.  

2. **Szyfrowanie Session Key**  
   - ten JSON jest serializowany i szyfrowany kluczem sesji czatu (`Session_Key`) uzgodnionym wcześniej ML‑KEM, z własnym nonce AES‑GCM.  

3. **Wiadomość typu „attachment”**  
   - przez Socket.IO nadawca wysyła event `send_message` z:  
     `message_type: 'attachment'`, `encrypted_content` (ciphertext JSON‑a), `nonce` i `session_key_id`.  
   - Backend zapisuje ciphertext + nonce w tabeli `messages` i oznacza rekord `message_type='attachment'`, po czym przekazuje go dalej do odbiorcy.  

Serwer nie ma możliwości odszyfrowania `encrypted_content` – nie zna Session Key.

### 3. Odbiorca – odszyfrowanie, weryfikacja i pobranie (frontend)

1. **Odbiór wiadomości**  
   - klient odbiorcy nasłuchuje `receive_message`; dla `message_type='attachment'` odszyfrowuje `encrypted_content` Session Key i uzyskuje `FileAttachmentMetadata`.  

2. **Pobranie zaszyfrowanego bloba**  
   - UI pobiera plik z `meta.url` (`GET /api/files/download/...`) jako `arraybuffer`.  
   - Oblicza SHA‑256 ciphertextu i porównuje z `meta.encrypted_hash`.  
   - Jeśli hash ciphertextu się nie zgadza, zgłaszany jest błąd naruszenia („załącznik został naruszony po stronie serwera”).  

3. **Odszyfrowanie RAW payloadu**  
   - przy poprawnym hashu ciphertextu, przeglądarka importuje `meta.file_key` i `meta.file_iv` jako klucz AES‑GCM i odszyfrowuje blob, odzyskując RAW payload `[SigLen|MetaLen|Meta|Sig|File]`.  

4. **Weryfikacja integralności pliku**  
   - z RAW payloadu odzyskiwany jest JSON metadanych i surowe bajty pliku; system liczy hash pliku (SHA‑256) i porównuje z `meta.file_hash`.  
   - jakakolwiek modyfikacja pliku powoduje błąd `FILE_HASH_MISMATCH`.  

5. **Weryfikacja podpisu Dilithium**  
   - hash pliku jest weryfikowany podpisem ML‑DSA‑65 (`meta.signature`) przy użyciu publicznego klucza nadawcy (`meta.signer_public_key` lub klucza w profilu nadawcy).  
   - w razie niezgodności otrzymujemy błąd `SIGNATURE_INVALID`; przy sukcesie UI oznacza załącznik jako „podpis zweryfikowany” i dopiero wtedy oferuje użytkownikowi pobranie.  

Cały proces – od podpisu po weryfikację – odbywa się w przeglądarkach użytkowników; serwer nie ma możliwości fałszowania pliku bez wykrycia.

---

## Bezpieczeństwo i scenariusze ataków

### Atak 1 – modyfikacja wiadomości (MITM na kanale Socket.IO)

**Cel:** atakujący próbuje zmienić ciphertext metadanych (`encrypted_content`) lub `nonce` w tabeli `messages` lub w locie na łączu.

**Obrona:**

- przy odszyfrowaniu JSON‑a funkcja deszyfrująca zwróci błąd; UI pokazuje komunikat o błędnej deszyfracji i nie oferuje pobrania.  
- serwer nie posiada Session Key, więc nie jest w stanie wygenerować poprawnego ciphertextu.  

**Właściwość:** chroni przed podmianą metadanych (np. URL, klucza pliku, podpisu) oraz zapewnia, że odczytywane przez odbiorcę `FileAttachmentMetadata` jest dokładnie tym, co zaszyfrował nadawca.

### Atak 2 – modyfikacja zaszyfrowanego pliku na serwerze

**Cel:** atakujący ma dostęp do systemu plików serwera lub storage i podmienia `.enc` (np. nadpisuje go innymi bajtami lub innym zaszyfrowanym plikiem).

**Obrona:**

- klient liczy SHA‑256 ciphertextu i porównuje z `meta.encrypted_hash`;  
- przy różnicy wyrzuca `ENCRYPTED_HASH_MISMATCH` i blokuje pobranie (“Załącznik został naruszony po stronie serwera”).  

**Właściwość:** serwer nie może zmienić pliku, nie łamiąc weryfikacji integralności po stronie klienta.

### Atak 3 – modyfikacja odszyfrowanego pliku (poza systemem)

**Cel:** atakujący lokalnie rekonstruuje RAW payload, modyfikuje same dane pliku, ale próbuje zachować „ładny” ciphertext i poprawny hash zaszyfrowanego bloba.

**Obrona:**

- hash pliku (w RAW payloadzie) jest porównywany z `meta.file_hash`;  
- podpis ML‑DSA‑65 weryfikowany jest z wykorzystaniem publicznego klucza nadawcy;  
- jakakolwiek modyfikacja pliku łamie co najmniej jedno z tych sprawdzeń (`FILE_HASH_MISMATCH` lub `SIGNATURE_INVALID`).  

**Właściwość:** nadawca nie może się wyprzeć pliku, odbiorca ma silną gwarancję, że plik nie został zmieniony od chwili podpisania.

### Atak 4 – kompromitacja serwera aplikacyjnego

**Cel:** serwer aplikacyjny próbuje odczytać załączniki lub generować fałszywe.

**Obrona:**

- serwer nie zna Session Key, Ephemeral File Key ani prywatnych kluczy Dilithium;  
- nie może odszyfrować treści pliku, ani wygenerować ważnego podpisu w imieniu użytkownika;  
- każda próba podstawienia pliku zostanie wykryta przez mechanizmy z ataków 1–3.  

**Właściwość:** kompromitacja backendu nie pozwala atakującemu podsłuchać załączników ani tekstu czatu; może jedynie próbować modyfikować ciphertexty, co jest wykrywane po stronie klientów.

---

## Co faktycznie widzi i przechowuje backend

**Otrzymuje:**

- `POST /api/files/upload` – zaszyfrowany blob `[podpis | metadane | plik]` oraz wynikowy SHA‑256 ciphertextu; brak dostępu do zawartości.  
- `send_message` (Socket.IO) – ciphertext JSON‑a metadanych oraz nonce, wraz z identyfikatorem sesji i uczestników.  

**Przechowuje:**

- zaszyfrowane pliki na dysku / storage,  
- zaszyfrowane wiadomości w tabeli `messages` (wraz z `message_type='text' | 'attachment'`),  
- hash zaszyfrowanego bloba w tabeli `uploaded_files` w celach audytowych.  

**Nie posiada:**

- prywatnych kluczy Dilithium,  
- kluczy sesji czatu (Session Key),  
- efemerycznych kluczy plików i IV,  
- oryginalnej zawartości plików ani ich jawnych metadanych.  

Dzięki temu kompromitacja backendu nie pozwala atakującemu podsłuchać załączników ani tekstu czatu; może jedynie próbować modyfikować ciphertexty, co jest wykrywane po stronie klientów.
