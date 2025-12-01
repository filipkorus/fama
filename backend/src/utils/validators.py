"""
Validation utilities for API inputs
"""

import re
import base64
from flask import current_app


def validate_username(username):
    """
    Validate username format
    - Length: 3-80 characters
    - Allowed: letters, numbers, underscore, hyphen
    """
    if not username or len(username) < 3 or len(username) > 80:
        return False, "Username must be between 3 and 80 characters"

    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        return False, "Username can only contain letters, numbers, _ and -"

    return True, ""


def validate_password(password, validate_strength=None):
    """
    Validate password
    - Minimum 8 characters (always)
    - If validate_strength=True:
      - At least one uppercase letter
      - At least one lowercase letter
      - At least one digit
    """
    if validate_strength is None:
        validate_strength = current_app.config.get('VALIDATE_PASSWORD_STRENGTH', False)

    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters long"

    if validate_strength:
        if not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"

        if not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"

        if not re.search(r'\d', password):
            return False, "Password must contain at least one digit"

    return True, ""


def validate_public_key(public_key):
    """
    Validate ML-KEM public key format
    - Must be valid Base64 string
    - Expected sizes: ~800 bytes (Kyber512), ~1184 bytes (Kyber768), ~1568 bytes (Kyber1024)
    """
    if not public_key or not isinstance(public_key, str):
        return False, "Public key is required and must be a string"

    try:
        decoded = base64.b64decode(public_key)
        key_size = len(decoded)

        # Valid ML-KEM public key sizes
        valid_sizes = [800, 1184, 1568]  # Kyber512, Kyber768, Kyber1024

        if key_size not in valid_sizes:
            return False, f"Invalid public key size: {key_size} bytes. Expected: {valid_sizes}"

        return True, ""
    except Exception as e:
        return False, f"Invalid Base64 format: {str(e)}"


def validate_dilithium_public_key(public_key):
    """
    Validate ML-DSA/Dilithium public key format
    - Must be valid Base64 string
    - Expected sizes: ~1312 bytes (Dilithium2), ~1952 bytes (Dilithium3), ~2592 bytes (Dilithium5)
    """
    if not public_key or not isinstance(public_key, str):
        return False, "Dilithium public key is required and must be a string"

    try:
        decoded = base64.b64decode(public_key)
        key_size = len(decoded)

        # Valid ML-DSA/Dilithium public key sizes
        valid_sizes = [1312, 1952, 2592]  # Dilithium2, Dilithium3, Dilithium5

        if key_size not in valid_sizes:
            return False, f"Invalid Dilithium public key size: {key_size} bytes. Expected: {valid_sizes}"

        return True, ""
    except Exception as e:
        return False, f"Invalid Base64 format: {str(e)}"
