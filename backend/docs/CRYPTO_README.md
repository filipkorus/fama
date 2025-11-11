# Moduł Kryptografii Post-Kwantowej - FAMA

Biblioteka do implementacji bezpiecznej wymiany kluczy i podpisów cyfrowych.

## Struktura Projektu

```
backend/crypto/
├── __init__.py              # Inicjalizacja pakietu
├── ml_kem.py               # Wymiana kluczy ML-KEM (Kyber)
├── digital_signature.py    # Podpisy cyfrowe ML-DSA (Dilithium)
└── utils.py                # Funkcje pomocnicze (AES-GCM, Base64)
```

## Wymagania

```bash
pip install liboqs-python pycryptodome
```

## Testowanie Instalacji

Sprawdzenie czy wszystko jest zainstalowane:

```bash
python -c "import oqs; print('liboqs:', oqs.oqs_version())"
python -c "from crypto import MLKEMCrypto, DigitalSignature, CryptoUtils; print('crypto: OK')"
```

### Oczekiwane wyniki:

```
liboqs: 0.14.0
crypto: OK
```

## Szybki Start

### 1. Wymiana Kluczy (ML-KEM)

```python
from crypto import MLKEMCrypto

# Inicjalizuj
crypto = MLKEMCrypto('Kyber768')

# Generuj parę kluczy dla odbiorcy
pub_key, priv_key = crypto.generate_keypair()

# Nadawca tworzy wspólny sekret
ciphertext, shared_secret = crypto.encapsulate(pub_key)

# Odbiorca odzyskuje wspólny sekret
recovered = crypto.decapsulate(priv_key, ciphertext)

# Sekrety powinny być identyczne
assert shared_secret == recovered
```

### 2. Podpisy Cyfrowe (Dilithium)

```python
from crypto import DigitalSignature

# Inicjalizuj
sig = DigitalSignature('Dilithium3')

# Generuj parę kluczy
pub_key, priv_key = sig.generate_keypair()

# Podpisz dane
message = b"Tajna wiadomość"
signature = sig.sign(priv_key, message)

# Weryfikuj podpis
is_valid = sig.verify(pub_key, message, signature)
print(is_valid)  # True
```

### 3. Szyfrowanie Symetryczne (AES-GCM)

```python
from crypto import CryptoUtils

# Generuj klucz
key = CryptoUtils.generate_random_bytes(32)

# Szyfruj dane
plaintext = b"Tajna wiadomość"
encrypted = CryptoUtils.encrypt_symmetric(key, plaintext)

# Odszyfuj
decrypted = CryptoUtils.decrypt_symmetric(key, encrypted)
print(decrypted)  # b"Tajna wiadomość"
```

## API

### MLKEMCrypto

Wymiana kluczy post-kwantowych (ML-KEM).

**Algorytmy:** Kyber512, Kyber768, Kyber1024

**Metody:**
- `generate_keypair()` → (public_key, private_key)
- `encapsulate(public_key)` → (ciphertext, shared_secret)
- `decapsulate(private_key, ciphertext)` → shared_secret
- `export_keypair_base64(pub, priv)` → dict
- `import_keypair_base64(dict)` → (pub, priv)

### DigitalSignature

Podpisy cyfrowe post-kwantowe (ML-DSA).

**Algorytmy:** Dilithium2, Dilithium3, Dilithium5  
**Haszowanie:** SHA256, SHA512, SHA3-256, SHA3-512

**Metody:**
- `generate_keypair()` → (public_key, private_key)
- `sign(private_key, data)` → signature
- `verify(public_key, data, signature)` → bool
- `hash_data(data, hash_algorithm)` → hash
- `create_signature_package(...)` → dict z metadanymi
- `verify_package(...)` → dict z wynikami

### CryptoUtils

Funkcje pomocnicze do szyfrowania i kodowania.

**Metody:**
- `encrypt_symmetric(key, plaintext)` → dict
- `decrypt_symmetric(key, encrypted_data)` → plaintext
- `bytes_to_base64(data)` → str
- `base64_to_bytes(data_b64)` → bytes
- `generate_random_bytes(size)` → bytes

## Integracja z Backend'em

### Import w aplikacji Flask:

```python
from flask import Flask
from crypto import MLKEMCrypto, DigitalSignature

app = Flask(__name__)

@app.route('/api/keys/generate', methods=['POST'])
def generate_keys():
    crypto = MLKEMCrypto('Kyber768')
    pub_key, priv_key = crypto.generate_keypair()
    return {
        'public_key': crypto.export_keypair_base64(pub_key, priv_key)['public_key']
    }
```

## Specyfikacje

| Parametr | ML-KEM (Kyber768) | ML-DSA (Dilithium3) |
|----------|------------------|-------------------|
| Algorytm | Kyber768 | Dilithium3 |
| Standard | NIST FIPS 203 | NIST FIPS 204 |
| Klucz publiczny | 1184 bytes | 1952 bytes |
| Klucz prywatny | 2400 bytes | 4000 bytes |
| Bezpieczeństwo | 192-bit | 192-bit |

## Błędy i Rozwiązywanie

### `ImportError: No module named 'oqs'`

Zainstaluj liboqs-python:
```bash
pip install liboqs-python
```

> [!IMPORTANT]  
> Należy mieć zainstalowany CMAKE na komputerze, biblioteka python-liboqs jest nakładką na prawdziwą bibliotekę napisaną w C. Musi zostać skompilowane.

### `ValueError: Tag verification failed`

Dane zostały zmienione lub uszkodzone podczas szyfrowania.

### `RuntimeError: Decapsulate failed`

Klucz prywatny lub szyfrogram nie pasują do siebie.

## Notatki

- Wszystkie funkcje zwracają dane w formacie bytes lub Base64
- Klucze można eksportować do słownika JSON i z powrotem
- AES-GCM zapewnia zarówno szyfrowanie jak i autentyczność
- Podpisy cyfrowe gwarantują autentyczność i integralność

## Dokumentacja

Pełna dokumentacja znajduje się w docstrings każdej klasy i metody:

```python
from crypto import MLKEMCrypto
help(MLKEMCrypto.encapsulate)
```
