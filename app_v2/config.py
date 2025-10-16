import os
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

# Carga variables de entorno desde .env (solo local, Render ya lo maneja)
load_dotenv()


# ============================
# ⚙️ Configuración general
# ============================
class Config:
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    FERNET_KEY = os.environ.get("FERNET_KEY")
    POLLING_INTERVAL_SECONDS = int(os.environ.get("POLLING_INTERVAL_SECONDS", 30))


# ============================
# 🧩 Instancia global de DB
# ============================
DB = SQLAlchemy()
