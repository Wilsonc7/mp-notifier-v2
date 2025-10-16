import os


class Config:
    # =====================================================
    # Configuración de base de datos
    # =====================================================
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # =====================================================
    # Clave para cifrado de datos (usada en utils.py)
    # =====================================================
    FERNET_KEY = os.environ.get("FERNET_KEY")

    # =====================================================
    # Intervalo de chequeo del scheduler
    # =====================================================
    POLLING_INTERVAL_SECONDS = int(os.environ.get("POLLING_INTERVAL_SECONDS", 30))

    # =====================================================
    # Configuración de entorno
    # =====================================================
    FLASK_ENV = os.environ.get("FLASK_ENV", "production")
