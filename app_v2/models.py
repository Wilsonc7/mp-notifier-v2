from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID, INET
import uuid
from datetime import datetime
import bcrypt
import secrets

DB = SQLAlchemy()


# ============================
# MERCHANT
# ============================
class Merchant(DB.Model):
    __tablename__ = "merchants"

    id = DB.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = DB.Column(DB.Text, nullable=False)
    mp_access_token_enc = DB.Column(DB.Text, nullable=False)
    created_at = DB.Column(DB.DateTime, default=datetime.utcnow)
    plan = DB.Column(DB.Text, default="basic")

    devices = DB.relationship("Device", back_populates="merchant", cascade="all, delete-orphan")
    payments = DB.relationship("Payment", back_populates="merchant", cascade="all, delete-orphan")


# ============================
# DEVICE
# ============================
class Device(DB.Model):
    __tablename__ = "devices"

    id = DB.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant_id = DB.Column(UUID(as_uuid=True), DB.ForeignKey("merchants.id"), nullable=False)

    device_serial = DB.Column(DB.Text, nullable=False, unique=True)
    device_api_key_hash = DB.Column(DB.Text, nullable=False)

    # Token individual para el ESP32
    token = DB.Column(DB.Text, nullable=False, unique=True, default=lambda: secrets.token_hex(16))

    status = DB.Column(DB.Text, nullable=False, default="active")
    last_seen = DB.Column(DB.DateTime)
    ip_last = DB.Column(INET)

    merchant = DB.relationship("Merchant", back_populates="devices")

    # ============================
    # Métodos utilitarios
    # ============================
    def set_api_key(self, plain_key: str):
        """Guarda un hash seguro del API key."""
        self.device_api_key_hash = bcrypt.hashpw(plain_key.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    def verify_api_key(self, plain_key: str) -> bool:
        """Verifica el API key recibido contra el hash almacenado."""
        try:
            return bcrypt.checkpw(plain_key.encode("utf-8"), self.device_api_key_hash.encode("utf-8"))
        except Exception:
            return False


# ============================
# PAYMENT
# ============================
class Payment(DB.Model):
    __tablename__ = "payments"

    id = DB.Column(DB.Text, primary_key=True)
    merchant_id = DB.Column(UUID(as_uuid=True), DB.ForeignKey("merchants.id"), nullable=False)
    device_id = DB.Column(UUID(as_uuid=True), DB.ForeignKey("devices.id"), nullable=True)

    amount = DB.Column(DB.Numeric(12, 2), nullable=False)
    payer_name = DB.Column(DB.Text)
    status = DB.Column(DB.Text, nullable=False)
    date_created = DB.Column(DB.DateTime, nullable=False)
    created_at = DB.Column(DB.DateTime, default=datetime.utcnow)

    merchant = DB.relationship("Merchant", back_populates="payments")
