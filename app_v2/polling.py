import requests
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from app_v2.models import DB, Merchant, Payment
from app_v2.security import decrypt_token

# Intervalo de consulta (en segundos)
POLL_INTERVAL_SECONDS = 30  # 🔄 Ahora consulta cada 30 segundos
MP_API_URL = "https://api.mercadopago.com/merchant_orders/search"

scheduler = BackgroundScheduler()


def run_polling_job(app):
    """Consulta órdenes recientes desde Mercado Pago (QR, transferencias CVU, etc.)"""
    print("🔄 Ejecutando job de polling...")
    try:
        # Contexto Flask para acceso a la base
        with app.app_context():
            with DB.session() as session:
                merchants = session.query(Merchant).all()
                for m in merchants:
                    try:
                        access_token = decrypt_token(m.mp_access_token_enc)
                        if not access_token:
                            print(f"⚠️ Token vacío o inválido para {m.name}")
                            continue

                        # Parámetros de búsqueda
                        now = datetime.utcnow()
                        date_from = (now - timedelta(hours=3)).isoformat() + "Z"
                        params = {"sort": "date_created", "criteria": "desc", "limit": 10}
                        headers = {"Authorization": f"Bearer {access_token}"}

                        # 🔍 Llamada al nuevo endpoint
                        r = requests.get(MP_API_URL, headers=headers, params=params, timeout=20)
                        if r.status_code != 200:
                            print(f"⚠️ Error {r.status_code} desde MP: {r.text[:200]}")
                            continue

                        data = r.json()
                        results = data.get("elements", [])
                        print(f"📥 {len(results)} órdenes recibidas para {m.name}")

                        for order in results:
                            # Solo procesar órdenes cerradas (pagadas)
                            if order.get("status") != "closed":
                                continue

                            payments = order.get("payments", [])
                            for p in payments:
                                if p.get("status") != "approved":
                                    continue

                                pid = str(p.get("id"))
                                if session.query(Payment).filter_by(id=pid).first():
                                    continue  # Ya existe

                                payer_info = order.get("payer", {}) or {}
                                payer_name = payer_info.get("nickname") or payer_info.get("email") or "Desconocido"

                                new_p = Payment(
                                    id=pid,
                                    merchant_id=m.id,
                                    payer_name=payer_name,
                                    amount=float(p.get("transaction_amount", 0.0)),
                                    status="approved",
                                    date_created=datetime.utcnow(),
                                    created_at=datetime.utcnow(),
                                )
                                session.add(new_p)
                                session.commit()
                                print(f"💾 Guardado pago {pid} - ${new_p.amount} de {payer_name}")

                    except Exception as sub_e:
                        session.rollback()
                        print(f"❌ Error procesando merchant {m.name}: {sub_e}")

    except Exception as e:
        print(f"❌ Error general durante el polling: {e}")


def start_scheduler(app):
    """Inicia el scheduler con app.context()"""
    try:
        scheduler.add_job(run_polling_job, "interval", seconds=POLL_INTERVAL_SECONDS, args=[app])
        scheduler.start()
        print(f"[Scheduler] Iniciado cada {POLL_INTERVAL_SECONDS} segundos.")
        print("⏱️ Scheduler activo con contexto Flask.")
    except Exception as e:
        print(f"[Scheduler] Error al iniciar: {e}")
