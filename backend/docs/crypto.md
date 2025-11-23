# Moduł Kryptografii Post-Kwantowej (Backend)

Biblioteka implementująca wymianę kluczy (ML-KEM) i podpisy cyfrowe (ML-DSA) zgodnie ze standardami NIST FIPS.

## Struktura Modułu

Lokalizacja: `backend/crypto/`

*   `ml_kem.py`: Implementacja ML-KEM (Kyber).
*   `digital_signature.py`: Implementacja ML-DSA (Dilithium).
*   `utils.py`: Funkcje pomocnicze (AES-GCM, Base64).
*   `__init__.py`: Ekspozycja klas publicznych.

## Instalacja i Zależności

Wymagane pakiety Python:
```bash
pip install -r requirements.txt
```

> [!IMPORTANT]
> **Ważna uwaga o instalacji liboqs-python:**
>
> Pakiet `liboqs-python` dostępny w PyPI (wersja 0.14.1) to jedynie **wrapper (nakładka) Pythona** na bibliotekę `liboqs` napisaną w C. Samo `pip install liboqs-python` **nie instaluje** biblioteki systemowej `liboqs`, którą wrapper próbuje się podłączyć.
>
> **Co to znaczy?**
> - `liboqs-python 0.14.1` — wrapper Pythona (pobierany z PyPI)
> - `liboqs 0.14.0` — rzeczywista biblioteka C, którą wrapper opakowuje (musi być zainstalowana systemowo)
>
> Wrapper próbuje znaleźć bibliotekę `liboqs` w standardowych lokalizacjach systemowych (np. `/usr/local/lib/liboqs.so`).

### 1. Instalacja na Lokalnym Systemie

Jeśli chcesz pracować lokalnie, musisz zainstalować bibliotekę `liboqs 0.14.0`:

*   Pobierz kod źródłowy biblioteki `liboqs` w wersji 0.14.0 klikając w [ten link](https://github.com/open-quantum-safe/liboqs/archive/refs/tags/0.14.0.zip). Następnie rozpakuj archiwum.
*   Po uruchomieniu backendu, biblioteka powinna zostać zainstalowana z rozpakowanego katalogu.

### 2. Instalacja w Docker

W projekcie FAMA `Dockerfile` automatycznie pobiera i kompiluje `liboqs 0.14.0` z oficjalnego repozytorium GitHub, zatem nie jest wymagana ręczna interwencja.

## Weryfikacja środowiska

```bash
python -c "import oqs; print('liboqs:', oqs.oqs_version())"
# Oczekiwane wyjście: liboqs: 0.14.0

python -c "from crypto import MLKEMCrypto, DigitalSignature; print('crypto: OK')"
# Oczekiwane wyjście: crypto: OK
```

## Przewodnik Implementacyjny

### 1. ML-KEM (Kyber) - Wymiana Kluczy

```python
from crypto import MLKEMCrypto

# 1. Inicjalizacja (Kyber768 - NIST Level 3)
kem = MLKEMCrypto('Kyber768')

# 2. Generowanie pary kluczy (Odbiorca)
public_key, private_key = kem.generate_keypair()

# 3. Enkapsulacja (Nadawca)
# Tworzy szyfrogram i wspólny sekret na podstawie klucza publicznego
ciphertext, shared_secret_sender = kem.encapsulate(public_key)

# 4. Dekapsulacja (Odbiorca)
# Odzyskuje wspólny sekret z szyfrogramu przy użyciu klucza prywatnego
shared_secret_receiver = kem.decapsulate(private_key, ciphertext)

assert shared_secret_sender == shared_secret_receiver
```

### 2. ML-DSA (Dilithium) - Podpisy Cyfrowe

```python
from crypto import DigitalSignature

# 1. Inicjalizacja (Dilithium3 - NIST Level 3)
dsa = DigitalSignature('Dilithium3')

# 2. Generowanie pary kluczy
public_key, private_key = dsa.generate_keypair()

# 3. Podpisywanie danych
data = b"Critical Payload"
signature = dsa.sign(private_key, data)

# 4. Weryfikacja podpisu
is_valid = dsa.verify(public_key, data, signature)  # True/False
```

### 3. Szyfrowanie Symetryczne (AES-GCM)

```python
from crypto import CryptoUtils

key = CryptoUtils.generate_random_bytes(32)  # 256 bitów
data = b"Secret Message"

# Szyfrowanie (zwraca słownik z 'ciphertext', 'nonce', 'tag')
encrypted = CryptoUtils.encrypt_symmetric(key, data)

# Odszyfrowywanie
decrypted = CryptoUtils.decrypt_symmetric(key, encrypted)
```

## Specyfikacja API

### Klasa `MLKEMCrypto`

Obsługiwane algorytmy: `Kyber512`, `Kyber768`, `Kyber1024`.

*   `generate_keypair()` -> `(bytes, bytes)`
*   `encapsulate(public_key: bytes)` -> `(bytes, bytes)`: Zwraca `(ciphertext, shared_secret)`.
*   `decapsulate(private_key: bytes, ciphertext: bytes)` -> `bytes`: Zwraca `shared_secret`.
*   `export_keypair_base64(pub, priv)` -> `dict`: Konwersja do Base64.

### Klasa `DigitalSignature`

Obsługiwane algorytmy: `Dilithium2`, `Dilithium3`, `Dilithium5`.

*   `generate_keypair()` -> `(bytes, bytes)`
*   `sign(private_key: bytes, data: bytes)` -> `bytes`
*   `verify(public_key: bytes, data: bytes, signature: bytes)` -> `bool`

### Klasa `CryptoUtils`

*   `encrypt_symmetric(key: bytes, plaintext: bytes)` -> `dict`: Szyfrowanie AES-GCM.
*   `decrypt_symmetric(key: bytes, encrypted_data: dict)` -> `bytes`.
*   `generate_random_bytes(size: int)` -> `bytes`.

## Parametry Kryptograficzne (NIST FIPS)

| Parametr | ML-KEM (Kyber768) | ML-DSA (Dilithium3) |
| --- | --- | --- |
| Standard | FIPS 203 | FIPS 204 |
| Poziom bezpieczeństwa | 192-bit (Level 3) | 192-bit (Level 3) |
| Klucz Publiczny | 1184 bajtów | 1952 bajtów |
| Klucz Prywatny | 2400 bajtów | 4000 bajtów |

## Rozwiązywanie Problemów

**Błąd:** `ImportError: No module named 'oqs'`
**Rozwiązanie:** Patrz sekcja "Instalacja i Zależności" (brak biblioteki systemowej `liboqs`).

**Błąd:** `ValueError: Tag verification failed`
**Rozwiązanie:** Weryfikacja integralności danych (uszkodzony szyfrogram/nonce/klucz AES).

**Błąd:** `RuntimeError: Decapsulate failed`
**Rozwiązanie:** Niezgodność pary kluczy KEM.
