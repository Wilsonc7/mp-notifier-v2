from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID, INET
import uuid
from datetime import datetime

# Instancia global de SQLAlchemy
DB = SQLAlchemy()


class Merchant(DB.Model):
    """
    Representa un comercio registrado en el sistema.
    Cada merchant tiene su token de acceso a Mercado Pago cifrado.
    """
    __tablename__ = "merchants"

    id = DB.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = DB.Column(DB.Text, nullable=False)
    mp_access_token_enc = DB.Column(DB.Text, nullable=False)
    created_at = DB.Column(DB.DateTime, default=datetime.utcnow)
    plan = DB.Column(DB.Text, default="basic")


class Device(DB.Model):
    """
    Representa un dispositivo (por ejemplo, un ESP32) asociado a un merchant.
    """
    __tablename__ = "devices"

    id = DB.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant_id = DB.Column(UUID(as_uuid=True), DB.ForeignKey("merchants.id"), nullable=False)
    device_serial = DB.Column(DB.Text, nullable=False, unique=True)
    device_api_key_hash = DB.Column(DB.Text, nullable=False)
    token = DB.Column(DB.Text, unique=True)  # 👈 compatibilidad con ESP32 (token de acceso directo)
    status = DB.Column(DB.Text, nullable=False, default="active")
    last_seen = DB.Column(DB.DateTime)
    ip_last = DB.Column(INET)

    # Relación con Merchant
    merchant = DB.relationship("Merchant", backref="devices")


class Payment(DB.Model):
    """
    Representa un pago obtenido desde la API de Mercado Pago.
    """
    __tablename__ = "payments"

    id = DB.Column(DB.Text, primary_key=True)
    merchant_id = DB.Column(UUID(as_uuid=True), DB.ForeignKey("merchants.id"), nullable=False)
    amount = DB.Column(DB.Numeric(12, 2), nullable=False)
    payer_name = DB.Column(DB.Text)
    status = DB.Column(DB.Text, nullable=False)
    date_created = DB.Column(DB.DateTime, nullable=False)
    created_at = DB.Column(DB.DateTime, default=datetime.utcnow)

    # Relación con Merchant
    merchant = DB.relationship("Merchant", backref="payments")
