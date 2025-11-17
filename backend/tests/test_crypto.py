"""
Testy jednostkowe modułu kryptografii post-kwantowej

Ten plik zawiera testy dla:
- MLKEMCrypto: Wymiana kluczy ML-KEM (Kyber)
- DigitalSignature: Podpisy cyfrowe ML-DSA (Dilithium)
- CryptoUtils: Funkcje pomocnicze (AES-GCM, Base64)

Uruchomienie:
    python -m pytest tests/test_crypto.py -v
    
======================== Testy Jednostkowe ========================
Co jest testowane:
  ML-KEM Crypto (Wymiana Kluczy)
    Inicjalizacja i konfiguracja
    Generowanie pary kluczy
    Enkapsulacja (tworzenie wspólnego sekretu)
    Dekapsulacja (odzyskiwanie wspólnego sekretu)
    Export/Import kluczy w Base64
    Informacje o algorytmie
    Różne rozmiary algorytmów (Kyber512, 768, 1024)

  Dilithium (Podpisy Cyfrowe)
    Inicjalizacja i konfiguracja
    Generowanie pary kluczy
    Podpisywanie danych
    Weryfikacja podpisów
    Haszowanie danych
    Różne algorytmy haszowania (SHA256, SHA512, SHA3)
    Pakiety podpisów z metadanymi
    Weryfikacja pakietów
    Detekcja zmienionego dokumentu

  CryptoUtils (Funkcje Pomocnicze)
    Szyfrowanie AES-256-GCM
    Deszyfrowanie i weryfikacja autentyczności
    Kodowanie Base64
    Dekodowanie Base64
    Generowanie losowych bajtów
    Odrzucenie klucza niewłaściwego rozmiaru
    Odrzucenie zmienionego szyfrogramu

  Testy Integracyjne
    Pełny przepływ komunikacji (ML-KEM → Dilithium → AES)
    Wymiana kluczy między dwoma stronami
    Podpisywanie i weryfikacja
    Szyfrowanie i deszyfrowanie
"""

import unittest
import base64

from src.crypto.ml_kem import MLKEMCrypto
from src.crypto.digital_signature import DigitalSignature
from src.crypto.utils import CryptoUtils


class TestMLKEMCrypto(unittest.TestCase):
    """Testy dla modułu ML-KEM (wymiana kluczy).
    
    Testuje wszystkie operacje wymiany kluczy:
    - Inicjalizacja
    - Generowanie kluczy
    - Enkapsulacja
    - Dekapsulacja
    - Export/Import kluczy
    """
    
    def setUp(self):
        """Przygotowanie do każdego testu.
        
        Uruchamia się przed każdym testem.
        Tworzy instancje klas do testowania.
        """
        self.crypto = MLKEMCrypto('Kyber768')
    
    def test_ml_kem_initialization(self):
        """Test inicjalizacji ML-KEM.
        
        Sprawdza czy:
        - Obiekt się tworzy
        - Algorytm jest ustawiony na Kyber768
        """
        self.assertEqual(self.crypto.algorithm, 'Kyber768')
    
    def test_ml_kem_invalid_algorithm(self):
        """Test rejektowania niewłaściwego algorytmu.
        
        Sprawdza czy próba użycia nieznanego algorytmu
        rzuca ValueError.
        """
        with self.assertRaises(ValueError):
            MLKEMCrypto('InvalidAlgorithm')
    
    def test_ml_kem_available_algorithms(self):
        """Test dostępnych algorytmów.
        
        Sprawdza czy lista dostępnych algorytmów zawiera
        oczekiwane wartości: Kyber512, Kyber768, Kyber1024
        """
        algorithms = MLKEMCrypto.get_available_algorithms()
        self.assertIn('Kyber512', algorithms)
        self.assertIn('Kyber768', algorithms)
        self.assertIn('Kyber1024', algorithms)
        self.assertEqual(len(algorithms), 3)
    
    def test_ml_kem_generate_keypair(self):
        """Test generowania pary kluczy.
        
        Sprawdza czy:
        - Zwracane są dokładnie dwa elementy (public_key, private_key)
        - Oba są bytesami
        - Mają oczekiwane rozmiary (1184, 2400 dla Kyber768)
        """
        pub_key, priv_key = self.crypto.generate_keypair()
        
        # Sprawdź typy
        self.assertIsInstance(pub_key, bytes)
        self.assertIsInstance(priv_key, bytes)
        
        # Sprawdź rozmiary dla Kyber768
        self.assertEqual(len(pub_key), 1184)
        self.assertEqual(len(priv_key), 2400)
        
        # Klucze powinny być różne
        self.assertNotEqual(pub_key, priv_key)
    
    def test_ml_kem_generate_different_keypairs(self):
        """Test generowania różnych par kluczy.
        
        Sprawdza czy każde generowanie tworzy różne klucze.
        (Brak determinizmu między generowaniami)
        """
        pub_key1, priv_key1 = self.crypto.generate_keypair()
        pub_key2, priv_key2 = self.crypto.generate_keypair()
        
        # Każde generowanie powinno dać inne klucze
        self.assertNotEqual(pub_key1, pub_key2)
        self.assertNotEqual(priv_key1, priv_key2)
    
    def test_ml_kem_encapsulate(self):
        """Test enkapsulacji (tworzenia wspólnego sekretu).
        
        Sprawdza czy:
        - Zwracane są ciphertext i shared_secret
        - Mają oczekiwane rozmiary
        - shared_secret ma 32 bajty
        """
        pub_key, _ = self.crypto.generate_keypair()
        ciphertext, shared_secret = self.crypto.encapsulate(pub_key)
        
        # Sprawdź typy
        self.assertIsInstance(ciphertext, bytes)
        self.assertIsInstance(shared_secret, bytes)
        
        # Sprawdź rozmiary
        self.assertEqual(len(ciphertext), 1088)  # Rozmiar dla Kyber768
        self.assertEqual(len(shared_secret), 32)  # 256-bitowy sekret
    
    def test_ml_kem_decapsulate(self):
        """Test dekapsulacji (odzyskiwania wspólnego sekretu).
        
        Sprawdza czy odbiorca może odzyskać identyczny
        wspólny sekret używając swojego klucza prywatnego.
        
        IMPORTANT: To jest KRYTYCZNY test - potwierdza że ML-KEM działa
        """
        # Krok 1: Odbiorca generuje klucze
        pub_key, priv_key = self.crypto.generate_keypair()
        
        # Krok 2: Nadawca tworzy wspólny sekret
        ciphertext, sender_secret = self.crypto.encapsulate(pub_key)
        
        # Krok 3: Odbiorca odzyskuje wspólny sekret
        recipient_secret = self.crypto.decapsulate(priv_key, ciphertext)
        
        # Krok 4: Sekrety powinny być identyczne!
        self.assertEqual(sender_secret, recipient_secret)
    
    def test_ml_kem_export_import_keypair(self):
        """Test eksportu i importu pary kluczy.
        
        Sprawdza czy klucze można:
        - Eksportować do Base64
        - Importować z powrotem
        - Otrzymana para działa identycznie
        """
        # Wygeneruj i eksportuj
        pub_key, priv_key = self.crypto.generate_keypair()
        exported = self.crypto.export_keypair_base64(pub_key, priv_key)
        
        # Sprawdź strukturę eksportowanego słownika
        self.assertIn('public_key', exported)
        self.assertIn('private_key', exported)
        self.assertIn('algorithm', exported)
        self.assertEqual(exported['algorithm'], 'Kyber768')
        
        # Importuj z powrotem
        imported_pub, imported_priv = self.crypto.import_keypair_base64(exported)
        
        # Powinne być identyczne
        self.assertEqual(pub_key, imported_pub)
        self.assertEqual(priv_key, imported_priv)
        
        # Przetestuj że importowane klucze działają
        ciphertext, secret1 = self.crypto.encapsulate(imported_pub)
        secret2 = self.crypto.decapsulate(imported_priv, ciphertext)
        self.assertEqual(secret1, secret2)
    
    def test_ml_kem_algorithm_info(self):
        """Test pobierania informacji o algorytmie.
        
        Sprawdza czy get_algorithm_info zwraca prawidłowe
        metadane dla algorytmu.
        """
        info = self.crypto.get_algorithm_info()
        
        self.assertEqual(info['name'], 'Kyber768')
        self.assertEqual(info['security_level'], 192)
        self.assertEqual(info['public_key_size'], 1184)
        self.assertEqual(info['private_key_size'], 2400)
        self.assertEqual(info['ciphertext_size'], 1088)
    
    def test_ml_kem_kyber512(self):
        """Test z algorytmem Kyber512 (rozmiary inne niż 768).
        
        Sprawdza czy różne algorytmy mają różne rozmiary kluczy.
        """
        crypto512 = MLKEMCrypto('Kyber512')
        pub_key, priv_key = crypto512.generate_keypair()
        
        # Kyber512 ma inne rozmiary niż Kyber768
        self.assertEqual(len(pub_key), 800)
        self.assertEqual(len(priv_key), 1632)


class TestDigitalSignature(unittest.TestCase):
    """Testy dla modułu podpisów cyfrowych.
    
    Testuje wszystkie operacje podpisywania:
    - Inicjalizacja
    - Generowanie kluczy
    - Podpisywanie
    - Weryfikacja
    - Haszowanie
    - Pakiety z metadanymi
    """
    
    def setUp(self):
        """Przygotowanie do każdego testu."""
        self.sig = DigitalSignature('Dilithium3')
        self.test_data = b"Test message for signing"
    
    def test_signature_initialization(self):
        """Test inicjalizacji podpisów cyfrowych."""
        self.assertEqual(self.sig.algorithm, 'Dilithium3')
        self.assertEqual(self.sig.hash_algorithm, 'SHA256')
    
    def test_signature_invalid_algorithm(self):
        """Test rejektowania niewłaściwego algorytmu podpisu."""
        with self.assertRaises(ValueError):
            DigitalSignature('InvalidAlgorithm')
    
    def test_signature_available_algorithms(self):
        """Test dostępnych algorytmów Dilithium."""
        algorithms = DigitalSignature.get_available_algorithms()
        self.assertIn('Dilithium2', algorithms)
        self.assertIn('Dilithium3', algorithms)
        self.assertIn('Dilithium5', algorithms)
    
    def test_signature_available_hash_algorithms(self):
        """Test dostępnych algorytmów haszowania."""
        algorithms = DigitalSignature.get_available_hash_algorithms()
        self.assertIn('SHA256', algorithms)
        self.assertIn('SHA512', algorithms)
        self.assertIn('SHA3-256', algorithms)
        self.assertIn('SHA3-512', algorithms)
    
    def test_signature_generate_keypair(self):
        """Test generowania pary kluczy do podpisywania.
        
        Sprawdza czy:
        - Zwracane są publiczny i prywatny klucz
        - Mają oczekiwane rozmiary
        """
        pub_key, priv_key = self.sig.generate_keypair()
        
        self.assertIsInstance(pub_key, bytes)
        self.assertIsInstance(priv_key, bytes)
        
        # Dilithium3 ma te rozmiary
        self.assertEqual(len(pub_key), 1952)
        self.assertEqual(len(priv_key), 4000)
    
    def test_signature_sign_and_verify(self):
        """Test podpisywania i weryfikacji.
        
        IMPORTANT: To jest KRYTYCZNY test - potwierdza że podpisy cyfrowe działają
        """
        # Generuj klucze
        pub_key, priv_key = self.sig.generate_keypair()
        
        # Podpisz dane
        signature = self.sig.sign(priv_key, self.test_data)
        self.assertIsInstance(signature, bytes)
        
        # Weryfikuj podpis
        is_valid = self.sig.verify(pub_key, self.test_data, signature)
        self.assertTrue(is_valid)
    
    def test_signature_verify_tampered_data(self):
        """Test weryfikacji zmienionego dokumentu.
        
        Sprawdza czy zmiana danych powoduje odrzucenie podpisu.
        """
        pub_key, priv_key = self.sig.generate_keypair()
        signature = self.sig.sign(priv_key, self.test_data)
        
        # Zmień dane
        tampered_data = b"Different message"
        
        # Podpis nie powinien być ważny dla zmienionych danych
        is_valid = self.sig.verify(pub_key, tampered_data, signature)
        self.assertFalse(is_valid)
    
    def test_signature_hash_data(self):
        """Test haszowania danych.
        
        Sprawdza czy:
        - Skrót ma prawidłowy rozmiar (32 dla SHA256)
        - Ten sam tekst daje ten sam skrót (determinizm)
        - Różny tekst daje inny skrót
        """
        # Skrót danych
        hash1 = self.sig.hash_data(self.test_data, 'SHA256')
        
        # Sprawdź rozmiar (256-bitowy = 32 bajty)
        self.assertEqual(len(hash1), 32)
        self.assertIsInstance(hash1, bytes)
        
        # Ten sam tekst daje ten sam skrót
        hash2 = self.sig.hash_data(self.test_data, 'SHA256')
        self.assertEqual(hash1, hash2)
        
        # Inny tekst daje inny skrót
        other_data = b"Different data"
        hash3 = self.sig.hash_data(other_data, 'SHA256')
        self.assertNotEqual(hash1, hash3)
    
    def test_signature_different_hash_algorithms(self):
        """Test różnych algorytmów haszowania.
        
        Sprawdza czy różne algorytmy dają różne rozmiary.
        """
        # SHA256 = 32 bajty
        h256 = self.sig.hash_data(self.test_data, 'SHA256')
        self.assertEqual(len(h256), 32)
        
        # SHA512 = 64 bajty
        h512 = self.sig.hash_data(self.test_data, 'SHA512')
        self.assertEqual(len(h512), 64)
        
        # SHA3-256 = 32 bajty
        h3_256 = self.sig.hash_data(self.test_data, 'SHA3-256')
        self.assertEqual(len(h3_256), 32)
    
    def test_signature_create_package(self):
        """Test tworzenia pakietu podpisu z metadanymi.
        
        Sprawdza czy pakiet zawiera:
        - Podpis
        - Skrót
        - Metadane
        - Timestamp
        """
        pub_key, priv_key = self.sig.generate_keypair()
        metadata = {'filename': 'document.pdf', 'user_id': 123}
        
        package = self.sig.create_signature_package(
            priv_key,
            self.test_data,
            key_id='user_001',
            metadata=metadata
        )
        
        # Sprawdź strukturę
        self.assertIn('signature', package)
        self.assertIn('hash', package)
        self.assertIn('hash_algorithm', package)
        self.assertIn('signature_algorithm', package)
        self.assertIn('key_id', package)
        self.assertIn('timestamp', package)
        self.assertIn('metadata', package)
        
        # Sprawdź wartości
        self.assertEqual(package['key_id'], 'user_001')
        self.assertEqual(package['signature_algorithm'], 'Dilithium3')
        self.assertEqual(package['hash_algorithm'], 'SHA256')
        self.assertEqual(package['metadata'], metadata)
    
    def test_signature_verify_package(self):
        """Test weryfikacji pakietu podpisu.
        
        Sprawdza czy verify_package prawidłowo weryfikuje
        kompletny pakiet zawierający metadane.
        """
        pub_key, priv_key = self.sig.generate_keypair()
        
        # Stwórz pakiet
        package = self.sig.create_signature_package(
            priv_key,
            self.test_data,
            key_id='user_001'
        )
        
        # Weryfikuj prawidłowy pakiet
        result = self.sig.verify_package(pub_key, self.test_data, package)
        
        self.assertTrue(result['valid'])
        self.assertTrue(result['signature_valid'])
        self.assertTrue(result['hash_valid'])
        self.assertTrue(result['algorithm_match'])
        self.assertEqual(len(result['errors']), 0)
    
    def test_signature_verify_package_tampered(self):
        """Test weryfikacji zmienionego pakietu.
        
        Sprawdza czy weryfikacja wykryje zmienione dane.
        """
        pub_key, priv_key = self.sig.generate_keypair()
        package = self.sig.create_signature_package(
            priv_key,
            self.test_data,
            key_id='user_001'
        )
        
        # Weryfikuj z inną wiadomością
        tampered_data = b"Different message"
        result = self.sig.verify_package(pub_key, tampered_data, package)
        
        self.assertFalse(result['valid'])
        self.assertGreater(len(result['errors']), 0)


class TestCryptoUtils(unittest.TestCase):
    """Testy dla funkcji pomocniczych.
    
    Testuje operacje:
    - Szyfrowanie/deszyfrowanie AES-GCM
    - Kodowanie/dekodowanie Base64
    - Generowanie losowych danych
    """
    
    def setUp(self):
        """Przygotowanie do każdego testu."""
        self.test_data = b"Test message"
        self.key = CryptoUtils.generate_random_bytes(32)
    
    def test_utils_generate_random_bytes(self):
        """Test generowania losowych bajtów.
        
        Sprawdza czy:
        - Generuje prawidłową ilość bajtów
        - Każde generowanie daje inne dane
        """
        random1 = CryptoUtils.generate_random_bytes(32)
        random2 = CryptoUtils.generate_random_bytes(32)
        
        self.assertEqual(len(random1), 32)
        self.assertEqual(len(random2), 32)
        
        # Nie powinny być identyczne
        self.assertNotEqual(random1, random2)
    
    def test_utils_encrypt_decrypt_roundtrip(self):
        """Test szyfrowania i deszyfrowania AES-GCM.
        
        IMPORTANT: To jest KRYTYCZNY test - potwierdza że szyfrowanie działa
        """
        # Szyfruj
        encrypted = CryptoUtils.encrypt_symmetric(self.key, self.test_data)
        
        # Sprawdź strukturę
        self.assertIn('ciphertext', encrypted)
        self.assertIn('nonce', encrypted)
        self.assertIn('tag', encrypted)
        
        # Odszyfuj
        decrypted = CryptoUtils.decrypt_symmetric(self.key, encrypted)
        
        # Powinno być identyczne
        self.assertEqual(self.test_data, decrypted)
    
    def test_utils_encrypt_wrong_key_size(self):
        """Test odrzucenia klucza niewłaściwego rozmiaru."""
        wrong_key = b"short_key"  # Zbyt krótko
        
        with self.assertRaises(ValueError):
            CryptoUtils.encrypt_symmetric(wrong_key, self.test_data)
    
    def test_utils_decrypt_tampered_ciphertext(self):
        """Test odrzucenia zmienionego szyfrogramu.
        
        Sprawdza czy zmiana szyfrogramu powoduje błąd weryfikacji.
        """
        encrypted = CryptoUtils.encrypt_symmetric(self.key, self.test_data)
        
        # Zmień ciphertext (pierwsze znaki)
        tampered = encrypted.copy()
        tampered['ciphertext'] = base64.b64encode(
            base64.b64decode(tampered['ciphertext'])[:-1] + b'X'
        ).decode()
        
        # Deszyfrowanie powinno nie powieść się
        with self.assertRaises(ValueError):
            CryptoUtils.decrypt_symmetric(self.key, tampered)
    
    def test_utils_bytes_to_base64(self):
        """Test kodowania na Base64."""
        encoded = CryptoUtils.bytes_to_base64(b"Hello World")
        
        self.assertIsInstance(encoded, str)
        self.assertEqual(encoded, "SGVsbG8gV29ybGQ=")
    
    def test_utils_base64_to_bytes(self):
        """Test dekodowania z Base64."""
        decoded = CryptoUtils.base64_to_bytes("SGVsbG8gV29ybGQ=")
        
        self.assertIsInstance(decoded, bytes)
        self.assertEqual(decoded, b"Hello World")
    
    def test_utils_base64_roundtrip(self):
        """Test kodowania i dekodowania Base64.
        
        Sprawdza czy data survives roundtrip.
        """
        data = b"Test data with special chars: \x00\x01\x02"
        
        encoded = CryptoUtils.bytes_to_base64(data)
        decoded = CryptoUtils.base64_to_bytes(encoded)
        
        self.assertEqual(data, decoded)
    
    def test_utils_valid_base64_encoding(self):
        """Test prawidłowego kodowania/dekodowania Base64."""
        valid_data = b"Hello World 123!"
        valid_b64 = base64.b64encode(valid_data).decode()
        decoded = CryptoUtils.base64_to_bytes(valid_b64)
        self.assertEqual(decoded, valid_data)
        self.assertIsInstance(decoded, bytes)
        
    def test_utils_get_default_key_size(self):
        """Test pobierania domyślnego rozmiaru klucza."""
        key_size = CryptoUtils.get_default_key()
        
        self.assertEqual(key_size, 32)  # 256-bitowy klucz


class TestIntegration(unittest.TestCase):
    """Testy integracyjne - testują współpracę modułów.
    
    Te testy symulują rzeczywiste scenariusze użytku.
    """
    
    def test_full_communication_flow(self):
        """Test pełnego przepływu komunikacji.
        
        Symuluje:
        1. Alicja i Bob wymieniają klucze za pomocą ML-KEM
        2. Ustalają wspólny sekret
        3. Podpisują dane za pomocą Dilithium
        4. Szyfrują wiadomość za pomocą AES-GCM
        """
        # Krok 1: Alicja i Bob wymieniają klucze ML-KEM
        crypto = MLKEMCrypto('Kyber768')
        bob_pub, bob_priv = crypto.generate_keypair()
        
        # Krok 2: Alicja tworzy wspólny sekret
        ciphertext, shared_secret = crypto.encapsulate(bob_pub)
        
        # Krok 3: Bob odzyskuje wspólny sekret
        recovered_secret = crypto.decapsulate(bob_priv, ciphertext)
        self.assertEqual(shared_secret, recovered_secret)
        
        # Krok 4: Bob podpisuje wiadomość
        sig = DigitalSignature('Dilithium3')
        sig_pub, sig_priv = sig.generate_keypair()
        
        message = b"Hello Alice, this is Bob"
        signature = sig.sign(sig_priv, message)
        
        # Krok 5: Alicja weryfikuje podpis
        is_valid = sig.verify(sig_pub, message, signature)
        self.assertTrue(is_valid)
        
        # Krok 6: Bob szyfruje wiadomość przy użyciu wspólnego sekretu
        encrypted = CryptoUtils.encrypt_symmetric(shared_secret, message)
        
        # Krok 7: Alicja odszyfrowuje
        decrypted = CryptoUtils.decrypt_symmetric(shared_secret, encrypted)
        self.assertEqual(decrypted, message)


if __name__ == '__main__':
    unittest.main(verbosity=2)