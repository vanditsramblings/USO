"""Fernet-based secret manager for encrypting environment variable values."""

import os

from cryptography.fernet import Fernet, InvalidToken

_ENV_KEY = "USO_MASTER_KEY"


class SecretManager:
    """Encrypts and decrypts secret values using Fernet symmetric encryption."""

    def __init__(self, master_key: str | bytes | None = None):
        if master_key is None:
            master_key = os.environ.get(_ENV_KEY, "")
        if not master_key:
            raise ValueError(f"Master key not provided. Set {_ENV_KEY} env var or pass master_key.")
        if isinstance(master_key, str):
            master_key = master_key.encode()
        self._fernet = Fernet(master_key)

    def encrypt(self, plaintext: str) -> bytes:
        """Encrypt a plaintext string, return ciphertext bytes."""
        return self._fernet.encrypt(plaintext.encode())

    def decrypt(self, ciphertext: bytes) -> str:
        """Decrypt ciphertext bytes, return plaintext string."""
        try:
            return self._fernet.decrypt(ciphertext).decode()
        except InvalidToken:
            raise ValueError("Decryption failed — wrong key or corrupted data.")

    @staticmethod
    def generate_key() -> str:
        """Generate a new Fernet key."""
        return Fernet.generate_key().decode()
