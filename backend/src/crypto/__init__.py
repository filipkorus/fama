"""
Moduł kryptograficzny FAMA

- ml_kem: Wymiana kluczy ML-KEM (Kyber)
- digital_signature: Podpisy cyfrowe ML-DSA (Dilithium)
- utils: Funkcje pomocnicze (AES-GCM, Base64)
"""

from .ml_kem import MLKEMCrypto
from .digital_signature import DigitalSignature
from .utils import CryptoUtils

__all__ = [
    'MLKEMCrypto',
    'DigitalSignature',
    'CryptoUtils'
]

__version__ = '1.0.0'