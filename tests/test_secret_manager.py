"""Tests for uso.secret_manager module."""

import pytest

from uso.secret_manager import SecretManager


@pytest.fixture()
def sm():
    key = SecretManager.generate_key()
    return SecretManager(master_key=key)


def test_generate_key():
    key = SecretManager.generate_key()
    assert isinstance(key, str)
    assert len(key) == 44


def test_encrypt_decrypt_roundtrip(sm):
    plaintext = "super-secret-value-123"
    ciphertext = sm.encrypt(plaintext)
    assert isinstance(ciphertext, bytes)
    assert ciphertext != plaintext.encode()
    decrypted = sm.decrypt(ciphertext)
    assert decrypted == plaintext


def test_decrypt_wrong_key():
    sm1 = SecretManager(master_key=SecretManager.generate_key())
    sm2 = SecretManager(master_key=SecretManager.generate_key())
    ciphertext = sm1.encrypt("secret")
    with pytest.raises(ValueError, match="Decryption failed"):
        sm2.decrypt(ciphertext)


def test_no_key_raises():
    with pytest.raises(ValueError, match="Master key not provided"):
        SecretManager(master_key="")


def test_empty_string(sm):
    ct = sm.encrypt("")
    assert sm.decrypt(ct) == ""


def test_unicode_content(sm):
    text = "密码 🔑 Ключ"
    ct = sm.encrypt(text)
    assert sm.decrypt(ct) == text
