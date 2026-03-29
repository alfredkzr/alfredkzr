from cryptography.fernet import Fernet

from app.config import settings


def get_fernet() -> Fernet:
    key = settings.encryption_key.encode() if settings.encryption_key else Fernet.generate_key()
    return Fernet(key)


def encrypt(value: str) -> str:
    return get_fernet().encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    return get_fernet().decrypt(value.encode()).decode()
