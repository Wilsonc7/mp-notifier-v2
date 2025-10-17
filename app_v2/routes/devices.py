from flask import Blueprint, jsonify, request
from app_v2.models import DB, Device
from app_v2.security import hash_api_key

devices_bp = Blueprint("devices", __name__)

@devices_bp.post("/register_device")
def register_device():
    try:
        data = request.get_json()
        if not data or "serial" not in data or "api_key" not in data or "merchant_id" not in data:
            return jsonify({"error": "Faltan parámetros"}), 400

        device = Device(
            merchant_id=data["merchant_id"],
            device_serial=data["serial"],
            device_api_key_hash=hash_api_key(data["api_key"])
        )
        DB.session.add(device)
        DB.session.commit()
        return jsonify({"ok": True, "device_token": device.token}), 201

    except Exception as e:
        DB.session.rollback()
        return jsonify({"error": str(e)}), 500
