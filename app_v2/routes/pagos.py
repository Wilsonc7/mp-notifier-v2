from flask import Blueprint, jsonify, request
from app_v2.models import DB, Payment, Device

pagos_bp = Blueprint("pagos", __name__)

@pagos_bp.get("/pagos")
def get_pagos():
    """
    Endpoint amigable para el ESP32.
    Acepta serial y token tanto en query params como en headers.
    Compatible con Render (sin usar headers X- personalizados).
    """
    try:
        # --- Recibir datos de forma flexible ---
        serial = (
            request.args.get("serial")
            or request.headers.get("Device-Serial")  # 🔁 antes era X-Device-Serial
        )
        token = (
            request.args.get("token")
            or request.headers.get("Authorization", "").replace("Bearer ", "").strip()
        )

        # --- Log para depuración ---
        print("📥 Headers recibidos:")
        print(f"Device-Serial: {serial}")
        print(f"Authorization (token): {token[:10]}..." if token else "❌ Sin token")

        if not serial or not token:
            return jsonify({"error": "Faltan parámetros: serial o token"}), 400

        # --- Verificar dispositivo autorizado ---
        device = Device.query.filter_by(device_serial=serial, token=token).first()
        if not device:
            return jsonify({"error": "Dispositivo no autorizado"}), 401

        # --- Obtener pagos del merchant asociado ---
        payments = (
            Payment.query.filter_by(merchant_id=device.merchant_id)
            .order_by(Payment.created_at.desc())
            .limit(10)
            .all()
        )

        pagos_data = [
            {
                "id": p.id,
                "amount": float(p.amount),
                "payer_name": p.payer_name,
                "status": p.status,
                "date_created": p.date_created.isoformat() if p.date_created else None,
            }
            for p in payments
        ]

        print(f"[Pagos] Enviando {len(pagos_data)} pagos para merchant_id={device.merchant_id}")
        return jsonify(pagos_data), 200

    except Exception as e:
        print(f"❌ Error en /pagos: {e}")
        return jsonify({"error": str(e)}), 500
