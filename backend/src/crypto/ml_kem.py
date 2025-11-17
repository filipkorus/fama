"""
ML-KEM (Kyber) - Kryptografia post-kwantowa

Moduł implementujący mechanizm wymiany kluczy ML-KEM (Known Intermediate Value KEM),
zatwierdzony przez NIST jako standard post-kwantowy. Zapewnia bezpieczną wymianę
kluczy między stronami komunikacji, odporną na ataki komputerów kwantowych.

Standardy:
    - NIST FIPS 203 (ML-KEM)
    - liboqs-python 0.14.0+

Przykład użycia:
    >>> crypto = MLKEMCrypto('Kyber768')
    >>> pub_key, priv_key = crypto.generate_keypair()
    >>> ciphertext, shared_secret = crypto.encapsulate(pub_key)
    >>> recovered_secret = crypto.decapsulate(priv_key, ciphertext)
    >>> assert shared_secret == recovered_secret
"""

import base64
from typing import Tuple, Dict


class MLKEMCrypto:
    """Interfejs do operacji kryptografii ML-KEM.
    
    Wrapper wokół liboqs-python zapewniający wysokopoziomowy interfejs
    do operacji wymiany kluczy post-kwantowych.
    
    Attributes:
        ALGORITHMS: Dostępne algorytmy ML-KEM
        DEFAULT_ALGORITHM: Domyślny algorytm (Kyber768)
    """
    
    ALGORITHMS = {
        'Kyber512': 'Kyber512',
        'Kyber768': 'Kyber768',
        'Kyber1024': 'Kyber1024'
    }
    
    DEFAULT_ALGORITHM = 'Kyber768'
    
    def __init__(self, algorithm: str = None):
        """Inicjalizuje interfejs do ML-KEM.
        
        Args:
            algorithm: Nazwa algorytmu ML-KEM. Domyślnie Kyber768.
                    Dostępne: Kyber512, Kyber768, Kyber1024
        
        Raises:
            ValueError: Jeśli wybrany algorytm nie jest dostępny
            ImportError: Jeśli liboqs-python nie jest zainstalowany
        """
        self.algorithm = algorithm or self.DEFAULT_ALGORITHM
        
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
        """Generuje nową parę kluczy ML-KEM.
        
        Tworzy parę kluczy (publiczny, prywatny) dla odbiorcy wiadomości.
        Klucz publiczny jest przekazywany nadawcy, klucz prywatny pozostaje
        u odbiorcy.
        
        Returns:
            Tuple[bytes, bytes]: Para (klucz_publiczny, klucz_prywatny)
            
        Raises:
            RuntimeError: Jeśli generowanie nie powiedzie się
        """
        try:
            kem = self.oqs.KeyEncapsulation(self.algorithm)
            public_key = kem.generate_keypair()
            private_key = kem.export_secret_key()
            return public_key, private_key
        except Exception as e:
            raise RuntimeError(f"Generowanie pary kluczy nie powiodło się: {e}") from e
    
    def encapsulate(self, public_key: bytes) -> Tuple[bytes, bytes]:
        """Enkapsulacja klucza - tworzy wspólny sekret dla nadawcy.
        
        Nadawca wykorzystuje klucz publiczny odbiorcy do stworzenia:
        - ciphertext: zaszyfrowany szyfrogram (wysyłany do odbiorcy)
        - shared_secret: wspólny sekret do szyfrowania wiadomości
        
        Proces:
            1. Nadawca otrzymuje klucz publiczny odbiorcy
            2. Tworzy szyfrogram i wspólny sekret
            3. Wysyła szyfrogram do odbiorcy
            4. Wspólny sekret używa do szyfrowania wiadomości
        
        Args:
            public_key: Klucz publiczny odbiorcy (bytes)
        
        Returns:
            Tuple[bytes, bytes]: (szyfrogram, wspólny_sekret)
        
        Raises:
            RuntimeError: Jeśli enkapsulacja nie powiedzie się
        """
        try:
            kem = self.oqs.KeyEncapsulation(self.algorithm)
            ciphertext, shared_secret = kem.encap_secret(public_key)
            return ciphertext, shared_secret
        except Exception as e:
            raise RuntimeError(f"Enkapsulacja nie powiodła się: {e}") from e
    
    def decapsulate(self, private_key: bytes, ciphertext: bytes) -> bytes:
        """Dekapsulacja klucza - odzyskuje wspólny sekret dla odbiorcy.
        
        Odbiorca wykorzystuje swój klucz prywatny oraz szyfrogram od nadawcy
        do odzyskania tego samego wspólnego sekretu.
        
        Proces:
            1. Odbiorca otrzymuje szyfrogram od nadawcy
            2. Używa swojego klucza prywatnego do dekapsulacji
            3. Odzyskuje identyczny wspólny sekret
            4. Dekoduje wiadomość używając sekretu
        
        Args:
            private_key: Klucz prywatny odbiorcy (bytes)
            ciphertext: Szyfrogram od nadawcy (bytes)
        
        Returns:
            bytes: Wspólny sekret (identyczny z sekretami nadawcy)
        
        Raises:
            RuntimeError: Jeśli dekapsulacja nie powiedzie się
        """
        try:
            kem = self.oqs.KeyEncapsulation(self.algorithm)
            kem.secret_key = private_key
            shared_secret = kem.decap_secret(ciphertext)
            return shared_secret
        except Exception as e:
            raise RuntimeError(f"Dekapsulacja nie powiodła się: {e}") from e
    
    def export_keypair_base64(self, public_key: bytes, private_key: bytes) -> Dict[str, str]:
        """Koduje parę kluczy na format Base64 do przechowywania/transmisji.
        
        Args:
            public_key: Klucz publiczny (bytes)
            private_key: Klucz prywatny (bytes)
        
        Returns:
            Dict[str, str]: Słownik z zakodowanymi kluczami:
                - 'public_key': Klucz publiczny (Base64)
                - 'private_key': Klucz prywatny (Base64)
                - 'algorithm': Nazwa algorytmu
        """
        return {
            'public_key': base64.b64encode(public_key).decode('utf-8'),
            'private_key': base64.b64encode(private_key).decode('utf-8'),
            'algorithm': self.algorithm
        }
    
    def import_keypair_base64(self, keys_dict: Dict[str, str]) -> Tuple[bytes, bytes]:
        """Dekoduje parę kluczy z formatu Base64.
        
        Args:
            keys_dict: Słownik zawierający:
                - 'public_key': Klucz publiczny (Base64)
                - 'private_key': Klucz prywatny (Base64)
                - 'algorithm' (opcjonalnie): Nazwa algorytmu
        
        Returns:
            Tuple[bytes, bytes]: Para (klucz_publiczny, klucz_prywatny)
        
        Raises:
            ValueError: Jeśli brakuje wymaganych kluczy
        """
        required = {'public_key', 'private_key'}
        if not required.issubset(keys_dict.keys()):
            raise ValueError(
                f"Słownik musi zawierać klucze: {', '.join(required)}"
            )
        
        public_key = base64.b64decode(keys_dict['public_key'])
        private_key = base64.b64decode(keys_dict['private_key'])
        
        if 'algorithm' in keys_dict:
            self.algorithm = keys_dict['algorithm']
        
        return public_key, private_key
    
    @staticmethod
    def get_available_algorithms() -> list:
        """Zwraca listę dostępnych algorytmów ML-KEM.
        
        Returns:
            list: Nazwy dostępnych algorytmów
        """
        return list(MLKEMCrypto.ALGORITHMS.values())
    
    def get_algorithm_info(self) -> Dict[str, any]:
        """Zwraca szczegółowe informacje o aktualnym algorytmie.
        
        Returns:
            Dict: Zawiera:
                - name: Nazwa algorytmu
                - security_level: Poziom bezpieczeństwa (bity)
                - public_key_size: Rozmiar klucza publicznego (bytes)
                - private_key_size: Rozmiar klucza prywatnego (bytes)
                - ciphertext_size: Rozmiar szyfrogramu (bytes)
                - description: Opis charakterystyki
        """
        info_map = {
            'Kyber512': {
                'name': 'Kyber512',
                'security_level': 128,
                'public_key_size': 800,
                'private_key_size': 1632,
                'ciphertext_size': 768,
                'description': 'Najmniejszy rozmiar, najszybszy'
            },
            'Kyber768': {
                'name': 'Kyber768',
                'security_level': 192,
                'public_key_size': 1184,
                'private_key_size': 2400,
                'ciphertext_size': 1088,
                'description': 'Zbalansowany - rekomendowany dla większości przypadków'
            },
            'Kyber1024': {
                'name': 'Kyber1024',
                'security_level': 256,
                'public_key_size': 1568,
                'private_key_size': 3168,
                'ciphertext_size': 1568,
                'description': 'Najwyższy poziom bezpieczeństwa'
            }
        }
        
        return info_map.get(self.algorithm, {})