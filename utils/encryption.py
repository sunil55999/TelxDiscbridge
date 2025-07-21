"""Encryption utilities for secure data handling."""

import os
import base64
from typing import Optional, Union
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from loguru import logger


class EncryptionManager:
    """Manages encryption and decryption for sensitive data."""
    
    def __init__(self, master_key: Optional[str] = None):
        """Initialize encryption manager with optional master key."""
        if master_key:
            # Derive key from password
            self.cipher = self._derive_cipher_from_password(master_key)
        else:
            # Generate or load key from environment
            key_env = os.getenv('ENCRYPTION_KEY')
            if key_env:
                try:
                    self.cipher = Fernet(key_env.encode())
                except Exception as e:
                    logger.warning(f"Invalid encryption key in environment: {e}")
                    self.cipher = self._generate_new_key()
            else:
                self.cipher = self._generate_new_key()
    
    def _generate_new_key(self) -> Fernet:
        """Generate a new encryption key."""
        key = Fernet.generate_key()
        logger.info("Generated new encryption key")
        return Fernet(key)
    
    def _derive_cipher_from_password(self, password: str, salt: Optional[bytes] = None) -> Fernet:
        """Derive encryption key from password using PBKDF2."""
        if salt is None:
            salt = b'stable_salt_for_session_encryption'  # Fixed salt for session data
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return Fernet(key)
    
    def encrypt(self, data: Union[str, bytes]) -> str:
        """Encrypt data and return base64 encoded string."""
        try:
            if isinstance(data, str):
                data = data.encode()
            
            encrypted_data = self.cipher.encrypt(data)
            return base64.urlsafe_b64encode(encrypted_data).decode()
            
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt base64 encoded data and return string."""
        try:
            # Decode from base64
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            
            # Decrypt
            decrypted_data = self.cipher.decrypt(encrypted_bytes)
            return decrypted_data.decode()
            
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise
    
    def encrypt_dict(self, data: dict) -> str:
        """Encrypt dictionary as JSON string."""
        import json
        json_str = json.dumps(data)
        return self.encrypt(json_str)
    
    def decrypt_dict(self, encrypted_data: str) -> dict:
        """Decrypt and return dictionary."""
        import json
        decrypted_str = self.decrypt(encrypted_data)
        return json.loads(decrypted_str)
    
    def get_key_string(self) -> str:
        """Get the encryption key as a string (for environment storage)."""
        # Extract key from Fernet instance
        return self.cipher._encryption_key.decode()
    
    @staticmethod
    def generate_key_string() -> str:
        """Generate a new key string."""
        return Fernet.generate_key().decode()
    
    def verify_key(self, test_data: str = "test_encryption") -> bool:
        """Verify the encryption key works correctly."""
        try:
            encrypted = self.encrypt(test_data)
            decrypted = self.decrypt(encrypted)
            return decrypted == test_data
        except Exception as e:
            logger.error(f"Key verification failed: {e}")
            return False