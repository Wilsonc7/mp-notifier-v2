import os
import bcrypt
from cryptography.fernet import Fernet


fernet = Fernet(os.environ.get("FERNET_KEY").encode())


def encrypt_token(token: str) -> str:
    return fernet.encrypt(token.encode()).decode()


def decrypt_token(token_enc: str) -> str:
    return fernet.decrypt(token_enc.encode()).decode()


def hash_api_key(api_key: str) -> str:
    return bcrypt.hashpw(api_key.encode(), bcrypt.gensalt()).decode()


def check_api_key(api_key: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(api_key.encode(), hashed.encode())
    except Exception:
        return False
