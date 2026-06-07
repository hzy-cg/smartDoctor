import base64
import hashlib
from cryptography.fernet import Fernet

from app.config import get_settings

_settings = get_settings()
_key = base64.urlsafe_b64encode(
    hashlib.pbkdf2_hmac('sha256', _settings.secret_key.encode(), b'smart-doctor-salt', 100000)
)
_cipher = Fernet(_key)


def encrypt(plaintext: str) -> str:
    return _cipher.encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    return _cipher.decrypt(ciphertext.encode()).decode()
