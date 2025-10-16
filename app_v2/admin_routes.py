from flask import Blueprint, request, jsonify
from sqlalchemy import select

from .models import DB, Device, Merchant
from .security import encrypt_token

admin = Blueprint("admin", __name__)

# NOTA: En producción, protegé estos endpoints con API Key admin o autenticación.


# Crear merchant con token (para flujo con activation_code)
@admin.post("/admin/merchants")
def admin_create_merchant():
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("name") or "").strip()
    token = (data.get("access_token") or "").strip()
    if not name or not token:
        return jsonify({"error": "name y access_token requeridos"}), 400

    m = Merchant(name=name, mp_access_token_enc=encrypt_token(token))
    DB.session.add(m)
    DB.session.commit()
    return jsonify({"id": str(m.id), "name": m.name}), 201


# (Opcional) Actualizar/rotar token de un merchant
@admin.post("/admin/merchants/<merchant_id>/rotate-token")
def admin_rotate_token(merchant_id):
    data = request.get_json(force=True, silent=True) or {}
    token = (data.get("access_token") or "").strip()
    if not token:
        return jsonify({"error": "access_token requerido"}), 400

    m = DB.session.get(Merchant, merchant_id)
    if not m:
        return jsonify({"error": "merchant no encontrado"}), 404

    m.mp_access_token_enc = encrypt_token(token)
    DB.session.commit()
    return jsonify({"ok": True}), 200


# Bloquear dispositivo
@admin.post("/admin/devices/<device_id>/block")
def admin_block(device_id):
    d = DB.session.get(Device, device_id)
    if not d:
        return jsonify({"error": "device no encontrado"}), 404
    d.status = "blocked"
    DB.session.commit()
    return jsonify({"ok": True, "status": d.status}), 200


# Desbloquear dispositivo
@admin.post("/admin/devices/<device_id>/unblock")
def admin_unblock(device_id):
    d = DB.session.get(Device, device_id)
    if not d:
        return jsonify({"error": "device no encontrado"}), 404
    d.status = "active"
    DB.session.commit()
    return jsonify({"ok": True, "status": d.status}), 200
