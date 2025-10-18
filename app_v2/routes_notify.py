from flask import Blueprint, request, jsonify
from datetime import datetime
from app_v2.models import DB, Payment, Merchant

bp_notify = Blueprint("notify", __name__)

@bp_notify.route("/notify", methods=["POST"])
def notify():
    """
    📩 Recibe notificaciones desde el dispositivo Android.
    Espera un JSON con: package, title, text
    """
    try:
        data = request.get_json(force=True)
        package = data.get("package")
        title = data.get("title")
        text = data.get("text")

        print(f"📥 Notificación recibida desde Android:")
        print(f"   🧩 App: {package}")
        print(f"   🏷️ Título: {title}")
        print(f"   💬 Texto: {text}")

        # ✅ Detectar si parece una transferencia o pago recibido
        if any(word in text.lower() for word in ["recibiste", "transferencia", "enviaron", "acreditado", "pagaron"]):
            new_payment = Payment(
                id=f"local_{datetime.utcnow().timestamp()}",
                merchant_id=None,  # O podés vincularlo a un Merchant si querés
                payer_name="Notificación Android",
                amount=0.0,  # No siempre se sabe el monto exacto
                status="notified",
                date_created=datetime.utcnow(),
                created_at=datetime.utcnow(),
            )
            DB.session.add(new_payment)
            DB.session.commit()
            print("💾 Guardado en DB como 'transferencia detectada'.")

        return jsonify({"status": "ok", "message": "Notificación recibida"}), 200

    except Exception as e:
        print(f"❌ Error procesando notificación: {e}")
        return jsonify({"error": str(e)}), 500
