from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID, INET
from datetime import datetime
import uuid

DB = SQLAlchemy()


# ========================================
# MERCHANTS (Comerciantes / Cuentas MP)
# ========================================
class Merchant(DB.Model):
    __tablename__ = "merchants"

    id = DB.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = DB.Column(DB.Text, nullable=False)
    mp_access_token_enc = DB.Column(DB.Text, nullable=False)  # 🔒 token cifrado con Fernet
    created_at = DB.Column(DB.DateTime, default=datetime.utcnow)
    plan = DB.Column(DB.Text, default="basic")

    # Relación: un merchant tiene varios devices
    devices = DB.relationship("Device", back_populates="merchant", cascade="all, delete-orphan")
    payments = DB.relationship("Payment", back_populates="merchant", cascade="all, delete-orphan")


# ========================================
# DEVICES (Dispositivos físicos - ESP32)
# ========================================
class Device(DB.Model):
    __tablename__ = "devices"

    id = DB.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant_id = DB.Column(UUID(as_uuid=True), DB.ForeignKey("merchants.id"), nullable=False)
    device_serial = DB.Column(DB.Text, nullable=False, unique=True)
    device_api_key_hash = DB.Column(DB.Text, nullable=False)
    status = DB.Column(DB.Text, nullable=False, default="active")
    last_seen = DB.Column(DB.DateTime)
    ip_last = DB.Column(INET)
    token = DB.Column(DB.Text, unique=True, default=lambda: str(uuid.uuid4()))  # 🔥 token único

    merchant = DB.relationship("Merchant", back_populates="devices")


# ========================================
# PAYMENTS (Pagos detectados por polling)
# ========================================
class Payment(DB.Model):
    __tablename__ = "payments"

    id = DB.Column(DB.Text, primary_key=True)  # id MercadoPago
    merchant_id = DB.Column(UUID(as_uuid=True), DB.ForeignKey("merchants.id"), nullable=False)
    amount = DB.Column(DB.Numeric(12, 2), nullable=False)
    payer_name = DB.Column(DB.Text)
    status = DB.Column(DB.Text, nullable=False)
    date_created = DB.Column(DB.DateTime, nullable=False)
    created_at = DB.Column(DB.DateTime, default=datetime.utcnow)

    merchant = DB.relationship("Merchant", back_populates="payments")
