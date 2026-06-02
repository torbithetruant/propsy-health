import base64
from cryptography.fernet import Fernet
from app.config import get_settings
import logging

settings = get_settings()
logger = logging.getLogger(__name__)

def _get_fernet() -> Fernet:
    key = settings.encryption_key.encode()
    if len(key) < 32: key = key.ljust(32, b'0')
    return Fernet(base64.urlsafe_b64encode(key[:32]))

def encrypt(data: str) -> str:
    return _get_fernet().encrypt(data.encode()).decode()

def decrypt(encrypted: str) -> str:
    try:
        return _get_fernet().decrypt(encrypted.encode()).decode()
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        raise ValueError("Invalid token decryption")