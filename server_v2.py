import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime
from app_v2.models import DB, Merchant, Device, Payment
from app_v2.security import check_api_key
from app_v2.polling import start_scheduler

# ==============================
# CONFIGURACIÓN FLASK
# ==============================
app = Flask(__name__)
CORS(app)

# Configuración base de datos
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///local.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Inicializar DB
DB.init_app(app)

with app.app_context():
    DB.create_all()
    print("📦 Tablas creadas o verificadas correctamente.")

# ==============================
# ENDPOINTS
# ==============================

@app.route("/")
def index():
    return jsonify({
        "message": "API MP Notifier v2 funcionando correctamente 🚀",
        "endpoints": ["/health", "/pagos", "/register_device"]
    }), 200


@app.route("/health")
def health():
    """Endpoint de monitoreo para Render (mantiene el servicio activo)."""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat()
    }), 200


@app.route("/register_device", methods=["POST"])
def register_device():
    """Registra un nuevo dispositivo asociado a un merchant."""
    data = request.json
    merchant_name = data.get("merchant_name")
    device_serial = data.get("device_serial")
    device_api_key = data.get("device_api_key")

    if not all([merchant_name, device_serial, device_api_key]):
        return jsonify({"error": "Faltan datos obligatorios"}), 400

    merchant = Merchant.query.filter_by(name=merchant_name).first()
    if not merchant:
        return jsonify({"error": "Merchant no encontrado"}), 404

    if Device.query.filter_by(device_serial=device_serial).first():
        return jsonify({"error": "El dispositivo ya está registrado"}), 400

    from app_v2.security import hash_api_key
    new_device = Device(
        merchant_id=merchant.id,
        device_serial=device_serial,
        device_api_key_hash=hash_api_key(device_api_key),
        status="active"
    )

    DB.session.add(new_device)
    DB.session.commit()

    return jsonify({
        "message": "Dispositivo registrado exitosamente",
        "device_token": new_device.token
    }), 201


@app.route("/pagos", methods=["GET"])
def get_pagos():
    """Obtiene los pagos recientes para un dispositivo autorizado."""
    auth_header = request.headers.get("Authorization", "")
    serial = request.headers.get("X-Device-Serial", "")
    if not auth_header.startswith("Bearer ") or not serial:
        return jsonify({"error": "Faltan encabezados de autenticación"}), 401

    token = auth_header.replace("Bearer ", "").strip()
    device = Device.query.filter_by(device_serial=serial).first()

    if not device:
        return jsonify({"error": "Dispositivo no encontrado"}), 404

    if device.token != token:
        return jsonify({"error": "Token inválido"}), 401

    device.last_seen = datetime.utcnow()
    device.ip_last = request.remote_addr
    DB.session.commit()

    payments = Payment.query.filter_by(merchant_id=device.merchant_id)\
        .order_by(Payment.created_at.desc())\
        .limit(10).all()

    pagos_list = [
        {
            "id": p.id,
            "amount": float(p.amount),
            "payer_name": p.payer_name,
            "status": p.status,
            "created_at": p.created_at.isoformat()
        } for p in payments
    ]

    print(f"[Pagos] Enviando {len(pagos_list)} pagos para merchant_id={device.merchant_id}")
    return jsonify(pagos_list), 200

# ==============================
# INICIO DE POLLING / APP
# ==============================
if __name__ == "__main__":
    start_scheduler(app)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
else:
    # Si lo arranca gunicorn (Render)
    start_scheduler(app)
    print("✅ Flask App v2 inicializada correctamente con SQLAlchemy.")
