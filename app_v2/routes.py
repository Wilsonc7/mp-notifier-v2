from flask import Blueprint, request, jsonify
from sqlalchemy import select
from app_v2.models import DB, Device, Payment
from app_v2.utils import encrypt_data, decrypt_data
from app_v2.polling import run_polling_job

bp = Blueprint("api", __name__)

# ============================
# Helpers
# ============================

def get_device_from_auth():
    """Obtiene el dispositivo autenticado desde el header Authorization"""
    auth = request.headers.get("Authorization")
    if not auth:
        return None

    token = auth.replace("Bearer ", "").strip()
    try:
        with DB.session() as session:
            q = select(Device).where(Device.token == token)
            dev = session.execute(q).scalars().first()
            return dev
    except Exception as e:
        print(f"[Auth] Error obteniendo device: {e}")
        return None


# ============================
# Rutas del sistema
# ============================

@bp.get("/status")
def status():
    """Verifica que el servidor esté activo"""
    return jsonify({"ok": True, "message": "Servidor activo ✅"}), 200


@bp.get("/poll")
def manual_poll():
    """Fuerza una ejecución manual del polling"""
    try:
        run_polling_job()
        print("[Polling] Ejecutado manualmente ✅")
        return jsonify({"ok": True, "message": "Polling ejecutado manualmente ✅"}), 200
    except Exception as e:
        print(f"[Polling] Error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


# ============================
# Rutas para dispositivos
# ============================

@bp.get("/pagos")
def device_payments():
    """Devuelve los últimos pagos aprobados para el dispositivo autenticado"""
    d = get_device_from_auth()
    if not d:
        return jsonify({"error": "No autorizado"}), 401

    try:
        with DB.session() as session:
            pagos = (
                session.query(Payment)
                .filter_by(merchant_id=d.merchant_id)  # 🔹 corregido
                .filter(Payment.status == "approved")  # 🔹 opcional: solo pagos aprobados
                .order_by(Payment.created_at.desc())
                .limit(10)
                .all()
            )

            result = [{
                "id": str(p.id),
                "nombre": p.payer_name,
                "monto": float(p.amount),
                "estado": p.status,
                "fecha": p.created_at.isoformat() if p.created_at else None
            } for p in pagos]

        print(f"[Pagos] Enviando {len(result)} pagos para merchant_id={d.merchant_id}")
        return jsonify(result), 200

    except Exception as e:
        print(f"[Pagos] Error al obtener pagos: {e}")
        return jsonify({"error": str(e)}), 500


# Alias para compatibilidad con el ESP32
@bp.get("/alias_pagos")
def pagos_alias():
    """Alias de compatibilidad para /pagos"""
    return device_payments()


# ============================
# Registro de nuevo dispositivo
# ============================

@bp.post("/register")
def register_device():
    """Registra un nuevo dispositivo"""
    data = request.get_json() or {}
    name = data.get("name")
    if not name:
        return jsonify({"error": "Nombre requerido"}), 400

    try:
        with DB.session() as session:
            new_dev = Device(name=name)
            session.add(new_dev)
            session.commit()

            print(f"[Register] Nuevo dispositivo registrado: {new_dev.name} (ID={new_dev.id})")

            return jsonify({
                "ok": True,
                "id": str(new_dev.id),
                "token": new_dev.token
            }), 201

    except Exception as e:
        print(f"[Register] Error: {e}")
        return jsonify({"error": str(e)}), 500


# ============================
# Prueba de conexión cifrada
# ============================

@bp.post("/secure")
def secure_test():
    """Prueba de cifrado y descifrado de datos"""
    data = request.get_json()
    if not data or "msg" not in data:
        return jsonify({"error": "Falta parámetro 'msg'"}), 400

    encrypted = encrypt_data(data["msg"])
    decrypted = decrypt_data(encrypted)

    return jsonify({
        "ok": True,
        "original": data["msg"],
        "encrypted": encrypted,
        "decrypted": decrypted
    }), 200
