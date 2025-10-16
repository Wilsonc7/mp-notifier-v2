import base64
from cryptography.fernet import Fernet
import os

# ==========================================
# Clave de cifrado (segura para Render)
# ==========================================

# Intentamos leer la clave desde variable de entorno
FERNET_KEY_ENV = os.environ.get("FERNET_KEY")

if FERNET_KEY_ENV:
    SECRET_KEY = FERNET_KEY_ENV.encode("utf-8")
else:
    # Solo para entorno local: genera y guarda clave en archivo
    SECRET_KEY_FILE = "fernet.key"
    if os.path.exists(SECRET_KEY_FILE):
        with open(SECRET_KEY_FILE, "rb") as f:
            SECRET_KEY = f.read()
    else:
        SECRET_KEY = Fernet.generate_key()
        with open(SECRET_KEY_FILE, "wb") as f:
            f.write(SECRET_KEY)

fernet = Fernet(SECRET_KEY)


# ==========================================
# Funciones de cifrado / descifrado
# ==========================================

def encrypt_data(data: str) -> str:
    """Cifra texto y lo devuelve codificado en base64"""
    if not data:
        return ""
    enc = fernet.encrypt(data.encode("utf-8"))
    return base64.urlsafe_b64encode(enc).decode("utf-8")


def decrypt_data(token: str) -> str:
    """Descifra texto cifrado en base64"""
    try:
        decoded = base64.urlsafe_b64decode(token.encode("utf-8"))
        dec = fernet.decrypt(decoded)
        return dec.decode("utf-8")
    except Exception:
        return ""
