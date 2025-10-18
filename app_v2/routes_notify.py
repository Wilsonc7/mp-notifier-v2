from flask import Blueprint, request, jsonify
from datetime import datetime
from app_v2.models import DB, Merchant, Payment

bp_notify = Blueprint("notify", __name__)

@bp_notify.route("/notify", methods=["POST"])
def notify_payment():
    data = request.get_json(force=True)
    token = request.headers.get("Authorization", "").replace("Bearer ", "").strip()
    serial = request.headers.get("Device-Serial", "")

    if not token or not serial:
        return jsonify({"error": "Falta token o serial"}), 400

    merchant = Merchant.query.filter_by(device_api_key=token).first()
    if not merchant:
        return jsonify({"error": "Dispositivo no autorizado"}), 403

    # 🟢 Crear un "pago" tipo notificación Android
    new_payment = Payment(
        id=f"local_{datetime.utcnow().timestamp()}",
        merchant_id=merchant.id,
        payer_name=data.get("payer_name", "Notificación Android"),
        amount=float(data.get("amount", 0.0)),
        status="notified",
        status_extra="notify_android",
        date_created=datetime.utcnow(),
        created_at=datetime.utcnow(),
    )

    DB.session.add(new_payment)
    DB.session.commit()

    print(f"📲 Notificación Android recibida: {new_payment.payer_name} - ${new_payment.amount}")
    return jsonify({"ok": True, "id": new_payment.id})
