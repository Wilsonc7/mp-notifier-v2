from flask import Blueprint, request, jsonify
from app_v2.models import DB, Merchant, Payment
from app_v2.security import decrypt_token

pagos_bp = Blueprint("pagos", __name__)

@pagos_bp.route("/pagos", methods=["GET"])
def get_pagos():
    """Devuelve los pagos + transferencias registradas"""
    auth_header = request.headers.get("Authorization", "")
    serial = request.headers.get("Device-Serial", "")
    token = auth_header.replace("Bearer ", "").strip()

    if not token or not serial:
        return jsonify({"error": "Falta token o serial"}), 400

    # Buscar merchant por token
    merchant = Merchant.query.filter_by(device_api_key=token).first()
    if not merchant:
        return jsonify({"error": "Dispositivo no autorizado"}), 403

    # 🔹 Buscar pagos aprobados recientes
    pagos = (
        Payment.query.filter_by(merchant_id=merchant.id)
        .order_by(Payment.date_created.desc())
        .limit(20)
        .all()
    )

    resultados = []
    for p in pagos:
        resultados.append({
            "id": p.id,
            "payer_name": p.payer_name,
            "amount": float(p.amount or 0),
            "status": p.status,
            "type": p.status_extra or "qr_payment",  # puede venir de Android
            "date_created": p.date_created.isoformat() if p.date_created else None,
        })

    return jsonify(resultados), 200
