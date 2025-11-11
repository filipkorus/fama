"""
Podpisy cyfrowe - Kryptografia post-kwantowa (ML-DSA/Dilithium)

Moduł implementujący funkcjonalność podpisów cyfrowych opartą na algorytmie ML-DSA
(Module-Lattice-Based Digital Signature Algorithm), znany jako Dilithium.
Zatwierdzony przez NIST jako standard post-kwantowy.

Stanowi gwarancję:
    - Autentyczności: Wiadomo kto wysłał
    - Integralności: Wiadomo czy dane nie zostały zmienione
    - Niezaprzeczalności: Nadawca nie może zaprzeczyć wysłaniu

Standardy:
    - NIST FIPS 204 (ML-DSA)
    - liboqs-python 0.14.0+

Przykład użycia:
    >>> sig = DigitalSignature('Dilithium3')
    >>> pub_key, priv_key = sig.generate_keypair()
    >>> signature = sig.sign(priv_key, b'Moja wiadomość')
    >>> is_valid = sig.verify(pub_key, b'Moja wiadomość', signature)
    >>> assert is_valid
"""

import base64
import hashlib
from typing import Tuple, Dict, Optional
from datetime import datetime


class DigitalSignature:
    """Interfejs do operacji podpisów cyfrowych ML-DSA/Dilithium.
    
    Wrapper wokół liboqs-python zapewniający wysokopoziomowy interfejs
    do operacji podpisywania i weryfikacji.
    
    Attributes:
        ALGORITHMS: Dostępne algorytmy Dilithium
        DEFAULT_ALGORITHM: Domyślny algorytm (Dilithium3)
        HASH_ALGORITHMS: Dostępne algorytmy haszowania
    """
    
    ALGORITHMS = {
        'Dilithium2': 'Dilithium2',
        'Dilithium3': 'Dilithium3',
        'Dilithium5': 'Dilithium5'
    }
    
    DEFAULT_ALGORITHM = 'Dilithium3'
    
    HASH_ALGORITHMS = {
        'SHA256': hashlib.sha256,
        'SHA512': hashlib.sha512,
        'SHA3-256': lambda: hashlib.sha3_256(),
        'SHA3-512': lambda: hashlib.sha3_512()
    }
    
    DEFAULT_HASH = 'SHA256'
    
    def __init__(self, algorithm: str = None):
        """Inicjalizuje interfejs do podpisów cyfrowych.
        
        Args:
            algorithm: Nazwa algorytmu Dilithium. Domyślnie Dilithium3.
                    Dostępne: Dilithium2, Dilithium3, Dilithium5
        
        Raises:
            ValueError: Jeśli wybrany algorytm nie jest dostępny
            ImportError: Jeśli liboqs-python nie jest zainstalowany
        """
        self.algorithm = algorithm or self.DEFAULT_ALGORITHM
        self.hash_algorithm = self.DEFAULT_HASH
        
        if self.algorithm not in self.ALGORITHMS.values():
            available = ', '.join(self.ALGORITHMS.values())
            raise ValueError(
                f"Algorytm '{self.algorithm}' nie jest dostępny. "
                f"Dostępne algorytmy: {available}"
            )
        
        try:
            import oqs
            self.oqs = oqs
        except ImportError as e:
            raise ImportError(
                "Biblioteka liboqs-python nie jest zainstalowana. "
                "Zainstaluj CMake i uruchom: python -c \"import oqs\""
            ) from e
    
    def generate_keypair(self) -> Tuple[bytes, bytes]:
        """Generuje nową parę kluczy do podpisywania.
        
        Tworzy parę kluczy (publiczny, prywatny) dla podpisywania.
        Klucz publiczny jest rozpowszechniany, klucz prywatny pozostaje u podpisującego.
        
        Returns:
            Tuple[bytes, bytes]: Para (klucz_publiczny, klucz_prywatny)
        
        Raises:
            RuntimeError: Jeśli generowanie nie powiedzie się
        """
        try:
            sig = self.oqs.Signature(self.algorithm)
            public_key = sig.generate_keypair()
            private_key = sig.export_secret_key()
            return public_key, private_key
        except Exception as e:
            raise RuntimeError(f"Generowanie pary kluczy nie powiodło się: {e}") from e
    
    def sign(self, private_key: bytes, data: bytes) -> bytes:
        """Podpisuje dane przy użyciu klucza prywatnego.
        
        Tworzy podpis cyfrowy wiadomości. Podpis gwarantuje autentyczność
        i integralność danych.
        
        Args:
            private_key: Klucz prywatny podpisującego (bytes)
            data: Dane do podpisania (bytes)
        
        Returns:
            bytes: Podpis cyfrowy
        
        Raises:
            RuntimeError: Jeśli podpisanie nie powiedzie się
        """
        try:
            sig = self.oqs.Signature(self.algorithm)
            sig.secret_key = private_key
            signature = sig.sign(data)
            return signature
        except Exception as e:
            raise RuntimeError(f"Podpisanie danych nie powiodło się: {e}") from e
    
    def verify(self, public_key: bytes, data: bytes, signature: bytes) -> bool:
        """Weryfikuje podpis cyfrowy.
        
        Sprawdza czy podpis jest prawidłowy dla danych, używając klucza publicznego.
        
        Args:
            public_key: Klucz publiczny podpisującego (bytes)
            data: Oryginalne dane (bytes)
            signature: Podpis cyfrowy do weryfikacji (bytes)
        
        Returns:
            bool: True jeśli podpis jest prawidłowy, False w przeciwnym razie
        """
        try:
            sig = self.oqs.Signature(self.algorithm)
            return sig.verify(data, signature, public_key)
        except Exception:
            return False
    
    def hash_data(self, data: bytes, hash_algorithm: str = None) -> bytes:
        """Oblicza skrót (hash) danych.
        
        Generuje skrót kryptograficzny dla danych, który może być używany
        do weryfikacji integralności.
        
        Args:
            data: Dane do zahaszowania (bytes)
            hash_algorithm: Algorytm haszowania. Jeśli None, używa DEFAULT_HASH.
                        Dostępne: SHA256, SHA512, SHA3-256, SHA3-512
        
        Returns:
            bytes: Skrót danych (32 lub 64 bajty w zależności od algorytmu)
        
        Raises:
            ValueError: Jeśli wybrany algorytm nie jest dostępny
        """
        hash_alg = hash_algorithm or self.hash_algorithm
        
        if hash_alg not in self.HASH_ALGORITHMS:
            available = ', '.join(self.HASH_ALGORITHMS.keys())
            raise ValueError(
                f"Algorytm '{hash_alg}' nie jest dostępny. "
                f"Dostępne algorytmy: {available}"
            )
        
        hasher = self.HASH_ALGORITHMS[hash_alg]
        if callable(hasher):
            h = hasher() if hash_alg.startswith('SHA3') else hasher()
        else:
            h = hasher()
        
        if isinstance(h, type(hashlib.sha256())):
            h.update(data)
            return h.digest()
        
        return hashlib.new(
            hash_alg.replace('SHA3-', 'sha3_').lower()
        ).digest() if data else b''
    
    def create_signature_package(
        self,
        private_key: bytes,
        data: bytes,
        key_id: str,
        metadata: Optional[Dict] = None,
        hash_algorithm: str = None
    ) -> Dict[str, any]:
        """Tworzy kompletny pakiet podpisu z metadanymi.
        
        Generuje podpis wraz z metadanymi ułatwiającymi weryfikację i śledzenie.
        
        Args:
            private_key: Klucz prywatny podpisującego (bytes)
            data: Dane do podpisania (bytes)
            key_id: Identyfikator klucza (np. ID użytkownika)
            metadata: Dodatkowe metadane (opcjonalne)
            hash_algorithm: Algorytm haszowania (opcjonalne)
        
        Returns:
            Dict zawierający:
                - signature: Podpis cyfrowy (Base64)
                - hash: Skrót danych (Base64)
                - hash_algorithm: Użyty algorytm haszowania
                - signature_algorithm: Użyty algorytm podpisu
                - key_id: Identyfikator klucza
                - timestamp: Czas utworzenia podpisu
                - data_hash: Drugi skrót dla weryfikacji (Base64)
                - metadata: Dołączone metadane
        """
        hash_alg = hash_algorithm or self.DEFAULT_HASH
        signature = self.sign(private_key, data)
        data_hash = self.hash_data(data, hash_alg)
        
        return {
            'signature': base64.b64encode(signature).decode('utf-8'),
            'hash': base64.b64encode(data_hash).decode('utf-8'),
            'hash_algorithm': hash_alg,
            'signature_algorithm': self.algorithm,
            'key_id': key_id,
            'timestamp': datetime.utcnow().isoformat(),
            'data_hash': base64.b64encode(data_hash).decode('utf-8'),
            'metadata': metadata or {}
        }
    
    def verify_package(
        self,
        public_key: bytes,
        data: bytes,
        package: Dict[str, any]
    ) -> Dict[str, any]:
        """Weryfikuje kompletny pakiet podpisu.
        
        Args:
            public_key: Klucz publiczny podpisującego (bytes)
            data: Oryginalne dane (bytes)
            package: Pakiet podpisu zwrócony przez create_signature_package()
        
        Returns:
            Dict zawierający:
                - valid: Czy podpis jest prawidłowy
                - signature_valid: Czy podpis odpowiada danym
                - hash_valid: Czy hasz odpowiada danym
                - algorithm_match: Czy algorytmy się zgadzają
                - errors: Lista błędów jeśli są
        """
        errors = []
        
        try:
            signature = base64.b64decode(package['signature'])
            expected_hash = base64.b64decode(package['hash'])
        except Exception as e:
            return {
                'valid': False,
                'signature_valid': False,
                'hash_valid': False,
                'algorithm_match': False,
                'errors': [f"Błąd dekodowania: {str(e)}"]
            }
        
        actual_hash = self.hash_data(data, package.get('hash_algorithm'))
        hash_valid = actual_hash == expected_hash
        signature_valid = self.verify(public_key, data, signature)
        algorithm_match = package.get('signature_algorithm') == self.algorithm
        
        if not hash_valid:
            errors.append("Skrót danych nie zgadza się")
        if not signature_valid:
            errors.append("Podpis nie jest prawidłowy")
        if not algorithm_match:
            errors.append(f"Algorytm nie zgadza się ({package.get('signature_algorithm')} vs {self.algorithm})")
        
        return {
            'valid': hash_valid and signature_valid and algorithm_match,
            'signature_valid': signature_valid,
            'hash_valid': hash_valid,
            'algorithm_match': algorithm_match,
            'errors': errors
        }
    
    @staticmethod
    def get_available_algorithms() -> list:
        """Zwraca listę dostępnych algorytmów Dilithium.
        
        Returns:
            list: Nazwy dostępnych algorytmów
        """
        return list(DigitalSignature.ALGORITHMS.values())
    
    @staticmethod
    def get_available_hash_algorithms() -> list:
        """Zwraca listę dostępnych algorytmów haszowania.
        
        Returns:
            list: Nazwy dostępnych algorytmów
        """
        return list(DigitalSignature.HASH_ALGORITHMS.keys())