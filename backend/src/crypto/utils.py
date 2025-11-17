"""
Funkcje pomocnicze - Operacje kryptograficzne

Moduł zawierający funkcje niskopoziomu do szyfrowania, deszyfrowania,
kodowania i generowania losowych danych.

Szyfrowanie symetryczne:
    - AES-256-GCM

Kodowanie:
    - Base64: Reprezentacja binarna w tekście ASCII
"""

import base64
import os
from typing import Dict, Tuple
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes


class CryptoUtils:
    """Narzędzia pomocnicze do operacji kryptograficznych.
    
    Zawiera funkcje statyczne do:
    - Szyfrowania/deszyfrowania symetrycznego (AES-GCM)
    - Kodowania/dekodowania Base64
    - Generowania losowych danych
    """
    
    NONCE_SIZE = 16  # 128-bitowy nonce
    TAG_SIZE = 16    # 128-bitowy tag autentyczności
    KEY_SIZE = 32    # 256-bitowy klucz
    
    @staticmethod
    def encrypt_symmetric(key: bytes, plaintext: bytes) -> Dict[str, str]:
        """Szyfruje dane symetrycznie przy użyciu AES-256-GCM.
        
        AES-GCM (Galois/Counter Mode) to tryb szyfrowania zapewniający:
        - Poufność: Dane są zaszyfrowane
        - Autentyczność: Można wykryć modyfikacje (tag)
        - Niezaprzeczalność: Kto ma klucz, ten może odszyfrować
        
        Proces:
            1. Generuje losowy nonce (liczba używana raz)
            2. Inicjalizuje szyfrowanie AES-256-GCM
            3. Szyfruje dane
            4. Generuje tag autentyczności
            5. Koduje wszystko na Base64
        
        Args:
            key: Klucz szyfrowania (32 bajty = 256 bitów)
            plaintext: Dane do zaszyfrowania (bytes)
        
        Returns:
            Dict[str, str] zawierający:
                - ciphertext: Dane zaszyfrowane (Base64)
                - nonce: Losowy nonce (Base64)
                - tag: Tag autentyczności (Base64)
        
        Raises:
            ValueError: Jeśli klucz jest nieprawidłowego rozmiaru
        
        Przykład:
            >>> key = os.urandom(32)
            >>> plaintext = b"Tajna wiadomość"
            >>> encrypted = CryptoUtils.encrypt_symmetric(key, plaintext)
            >>> print(encrypted)
            {
                'ciphertext': 'ABC123...',
                'nonce': 'XYZ789...',
                'tag': 'DEF456...'
            }
        """
        if len(key) != CryptoUtils.KEY_SIZE:
            raise ValueError(
                f"Klucz musi mieć dokładnie {CryptoUtils.KEY_SIZE} bajtów, "
                f"otrzymano {len(key)}"
            )
        
        nonce = get_random_bytes(CryptoUtils.NONCE_SIZE)
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        ciphertext, tag = cipher.encrypt_and_digest(plaintext)
        
        return {
            'ciphertext': base64.b64encode(ciphertext).decode('utf-8'),
            'nonce': base64.b64encode(nonce).decode('utf-8'),
            'tag': base64.b64encode(tag).decode('utf-8')
        }
    
    @staticmethod
    def decrypt_symmetric(key: bytes, encrypted_data: Dict[str, str]) -> bytes:
        """Odszyfrowuje dane zaszyfrowane przy użyciu AES-256-GCM.
        
        Odwraca operację encrypt_symmetric. Weryfikuje autentyczność poprzez
        sprawdzenie tagu.
        
        Proces:
            1. Dekoduje dane z Base64
            2. Inicjalizuje deszyfrowanie z nonce
            3. Odszyfrowuje dane
            4. Weryfikuje tag autentyczności
        
        Args:
            key: Klucz szyfrowania (32 bajty)
            encrypted_data: Słownik z wynikami z encrypt_symmetric()
                zawierający: ciphertext, nonce, tag
        
        Returns:
            bytes: Oryginalne dane (plaintext)
        
        Raises:
            ValueError: Jeśli:
                - Klucz jest nieprawidłowego rozmiaru
                - Tag autentyczności jest nieprawidłowy (dane zostały zmienione)
                - Dane są uszkodzone
        
        Przykład:
            >>> plaintext_recovered = CryptoUtils.decrypt_symmetric(key, encrypted)
            >>> assert plaintext == plaintext_recovered
        """
        if len(key) != CryptoUtils.KEY_SIZE:
            raise ValueError(
                f"Klucz musi mieć dokładnie {CryptoUtils.KEY_SIZE} bajtów, "
                f"otrzymano {len(key)}"
            )
        
        try:
            ciphertext = base64.b64decode(encrypted_data['ciphertext'])
            nonce = base64.b64decode(encrypted_data['nonce'])
            tag = base64.b64decode(encrypted_data['tag'])
        except KeyError as e:
            raise ValueError(f"Brakuje wymaganego pola: {e}") from e
        except Exception as e:
            raise ValueError(f"Błąd dekodowania Base64: {e}") from e
        
        try:
            cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
            plaintext = cipher.decrypt_and_verify(ciphertext, tag)
            return plaintext
        except ValueError as e:
            raise ValueError(
                "Weryfikacja autentyczności nie powiodła się. "
                "Dane mogą być uszkodzone lub zmienione."
            ) from e
    
    @staticmethod
    def bytes_to_base64(data: bytes) -> str:
        """Koduje dane binarne na format Base64.
        
        Base64 konwertuje dane binarne na zestaw 64 znaków ASCII,
        ułatwiając transmisję przez sieci.
        
        Args:
            data: Dane binarne (bytes)
        
        Returns:
            str: Dane w formacie Base64
        
        Przykład:
            >>> b64 = CryptoUtils.bytes_to_base64(b"Hello")
            >>> print(b64)
            SGVsbG8=
        """
        return base64.b64encode(data).decode('utf-8')
    
    @staticmethod
    def base64_to_bytes(data_b64: str) -> bytes:
        """Dekoduje dane z formatu Base64.
        
        Odwraca operację bytes_to_base64.
        
        Args:
            data_b64: Dane w formacie Base64 (str)
        
        Returns:
            bytes: Oryginalne dane binarne
        
        Raises:
            ValueError: Jeśli dane nie są prawidłowym Base64
        
        Przykład:
            >>> original = CryptoUtils.base64_to_bytes(b64)
            >>> assert original == b"Hello"
        """
        try:
            return base64.b64decode(data_b64)
        except Exception as e:
            raise ValueError(f"Nieprawidłowy format Base64: {e}") from e
    
    @staticmethod
    def generate_random_bytes(size: int) -> bytes:
        """Generuje losowe dane kryptograficznie bezpieczne.
        
        Używa OS random number generator do wygenerowania danych.
        
        Args:
            size: Liczba bajtów do wygenerowania
        
        Returns:
            bytes: Losowe dane
        
        Przykład:
            >>> random_key = CryptoUtils.generate_random_bytes(32)
            >>> print(len(random_key))
            32
        """
        return get_random_bytes(size)
    
    @staticmethod
    def get_default_key() -> bytes:
        """Zwraca domyślny rozmiar klucza do szyfrowania symetrycznego.
        
        Returns:
            int: Rozmiar klucza w bajtach (32 = 256 bitów)
        """
        return CryptoUtils.KEY_SIZE