from flask import Blueprint, jsonify, request
from app_v2.models import DB, Payment, Device
from datetime import datetime

pagos_bp = Blueprint("pagos", __name__)

@pagos_bp.get("/pagos")
def get_pagos():
    try:
        serial = request.args.get("serial")
        token = request.args.get("token")

        if not serial or not token:
            return jsonify({"error": "Faltan parámetros"}), 400

        device = Device.query.filter_by(device_serial=serial, token=token).first()
        if not device:
            return jsonify({"error": "Dispositivo no autorizado"}), 401

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
        return jsonify({"error": str(e)}), 500
