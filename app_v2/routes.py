import os
import secrets
from datetime import datetime
from typing import Optional

from flask import Blueprint, request, jsonify
from sqlalchemy import select, desc

from .models import DB, Merchant, Device, Payment
from .security import encrypt_token, hash_api_key, check_api_key

bp = Blueprint("api", __name__)

# =========================
# Helpers
# =========================
def _get_bearer_token() -> Optional[str]:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    return auth.split(" ", 1)[1].strip()


def _get_client_ip() -> Optional[str]:
    fwd = request.headers.get("X-Forwarded-For")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.remote_addr


def get_device_from_auth() -> Optional[Device]:
    """
    Autenticación por device_api_key (Bearer).
    """
    api_key = _get_bearer_token()
    if not api_key:
        return None

    serial_hint = request.headers.get("X-Device-Serial")
    session = DB.session
    devices = []

    if serial_hint:
        q = select(Device).where(Device.device_serial == serial_hint)
        dev = session.execute(q).scalars().first()
        if dev:
            devices = [dev]

    if not devices:
        devices = session.execute(select(Device)).scalars().all()

    for d in devices:
        if check_api_key(api_key, d.device_api_key_hash):
            d.last_seen = datetime.utcnow()
            ip = _get_client_ip()
            try:
                d.ip_last = ip
            except Exception:
                pass
            session.commit()
            return d
    return None


# =========================
# Health
# =========================
@bp.get("/health")
def health():
    return jsonify({"ok": True, "ts": datetime.utcnow().isoformat()}), 200


# =========================
# Registro de dispositivo
# =========================
@bp.post("/devices/register")
def register_device():
    data = request.get_json(force=True, silent=True) or {}
    device_serial = (data.get("device_serial") or "").strip()
    merchant_name = (data.get("merchant_name") or "").strip()
    access_token = (data.get("access_token") or "").strip()
    activation_code = (data.get("activation_code") or "").strip()

    if not device_serial:
        return jsonify({"error": "device_serial requerido"}), 400

    session = DB.session
    existing = session.execute(
        select(Device).where(Device.device_serial == device_serial)
    ).scalars().first()

    # Flujo A: access_token directo
    if access_token:
        if existing:
            m = existing.merchant
            if not m:
                m = Merchant(
                    name=merchant_name or f"Merchant-{device_serial}",
                    mp_access_token_enc=encrypt_token(access_token),
                )
                session.add(m)
                session.flush()
                existing.merchant_id = m.id
            else:
                m.mp_access_token_enc = encrypt_token(access_token)

            api_key = secrets.token_urlsafe(32)
            existing.device_api_key_hash = hash_api_key(api_key)
            existing.status = "active"
            session.commit()
            return jsonify({
                "device_id": str(existing.id),
                "device_api_key": api_key,
                "merchant_id": str(existing.merchant_id),
            }), 200

        m = Merchant(
            name=merchant_name or f"Merchant-{device_serial}",
            mp_access_token_enc=encrypt_token(access_token),
        )
        session.add(m)
        session.flush()

        api_key = secrets.token_urlsafe(32)
        d = Device(
            merchant_id=m.id,
            device_serial=device_serial,
            device_api_key_hash=hash_api_key(api_key),
            status="active",
        )
        session.add(d)
        session.commit()
        return jsonify({
            "device_id": str(d.id),
            "device_api_key": api_key,
            "merchant_id": str(m.id)
        }), 201

    # Flujo B: activation_code
    if not activation_code:
        return jsonify({"error": "access_token o activation_code requerido"}), 400

    m = session.execute(
        select(Merchant).where(Merchant.name == activation_code)
    ).scalars().first()

    if not m:
        return jsonify({"error": "activation_code inválido"}), 400
    if not m.mp_access_token_enc:
        return jsonify({"error": "merchant sin token configurado"}), 400

    if existing:
        existing.merchant_id = m.id
        api_key = secrets.token_urlsafe(32)
        existing.device_api_key_hash = hash_api_key(api_key)
        existing.status = "active"
        session.commit()
        return jsonify({
            "device_id": str(existing.id),
            "device_api_key": api_key,
            "merchant_id": str(m.id)
        }), 200

    api_key = secrets.token_urlsafe(32)
    d = Device(
        merchant_id=m.id,
        device_serial=device_serial,
        device_api_key_hash=hash_api_key(api_key),
        status="active",
    )
    session.add(d)
    session.commit()
    return jsonify({
        "device_id": str(d.id),
        "device_api_key": api_key,
        "merchant_id": str(m.id)
    }), 201


# =========================
# Status del dispositivo
# =========================
@bp.get("/devices/status")
def device_status():
    d = get_device_from_auth()
    if not d:
        return jsonify({"error": "no autorizado"}), 401

    msg = "OK" if d.status == "active" else "Dispositivo bloqueado. Contactese con BlackDog"
    return jsonify({
        "status": d.status,
        "message": msg,
        "device_id": str(d.id),
        "merchant_id": str(d.merchant_id),
        "last_seen": d.last_seen.isoformat() if d.last_seen else None,
    }), 200


# =========================
# Pagos del merchant
# =========================
@bp.get("/devices/payments")
def device_payments():
    d = get_device_from_auth()
    if not d:
        return jsonify({"error": "no autorizado"}), 401
    if d.status != "active":
        return jsonify({
            "status": d.status,
            "message": "Dispositivo bloqueado. Contactese con BlackDog"
        }), 403

    try:
        limit = int(request.args.get("limit", "20"))
    except ValueError:
        limit = 20
    limit = max(1, min(limit, 50))

    q = (
        select(Payment)
        .where(Payment.merchant_id == d.merchant_id)
        .order_by(desc(Payment.date_created))
        .limit(limit)
    )
    pays = DB.session.execute(q).scalars().all()

    out = [{
        "id": p.id,
        "estado": p.status,
        "monto": float(p.amount),
        "fecha": p.date_created.isoformat() if hasattr(p.date_created, "isoformat") else str(p.date_created),
        "nombre": p.payer_name or "Desconocido",
    } for p in pays]

    return jsonify(out), 200


# =========================
# Heartbeat
# =========================
@bp.post("/devices/heartbeat")
def device_heartbeat():
    d = get_device_from_auth()
    if not d:
        return jsonify({"error": "no autorizado"}), 401
    d.last_seen = datetime.utcnow()
    ip = _get_client_ip()
    try:
        d.ip_last = ip
    except Exception:
        pass
    DB.session.commit()
    return jsonify({"ok": True, "status": d.status}), 200


# =========================
# Alias /pagos
# =========================
@bp.get("/pagos")
def pagos_alias():
    return device_payments()


# =========================
# Endpoint /status (corregido)
# =========================
@bp.get("/status")
def system_status():
    """
    Muestra resumen general del sistema.
    """
    try:
        with DB.session() as session:
            merchants_count = session.query(Merchant).count()
            devices_count = session.query(Device).count()
            active_devices = session.query(Device).filter_by(status="active").count()
            blocked_devices = session.query(Device).filter_by(status="blocked").count()
            last_payment = (
                session.query(Payment)
                .order_by(desc(Payment.date_created))
                .limit(1)
                .first()
            )
            last_payment_ts = (
                last_payment.date_created.isoformat() if last_payment else None
            )

        return jsonify({
            "ok": True,
            "merchants": merchants_count,
            "devices_total": devices_count,
            "devices_active": active_devices,
            "devices_blocked": blocked_devices,
            "last_payment": last_payment_ts,
            "timestamp": datetime.utcnow().isoformat(),
        }), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
