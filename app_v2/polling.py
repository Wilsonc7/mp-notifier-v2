import requests
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from app_v2.models import DB, Merchant, Payment
from app_v2.security import decrypt_token

# ==============================
# CONFIG
# ==============================
POLL_INTERVAL_SECONDS = 30  # 🔸 cada 30 seg para test
MP_API_URL = "https://api.mercadopago.com/v1/payments"
# Nueva URL, ya no se usa /search

scheduler = BackgroundScheduler()

def run_polling_job(app):
    """Consulta pagos recientes desde Mercado Pago"""
    print("🔄 Ejecutando job de polling...")
    try:
        with app.app_context():
            with DB.session() as session:
                merchants = session.query(Merchant).all()

                for m in merchants:
                    try:
                        access_token = decrypt_token(m.mp_access_token_enc)
                        if not access_token:
                            print(f"⚠️ Token vacío o inválido para {m.name}")
                            continue

                        # Buscar pagos recientes (últimas 3 horas)
                        now = datetime.utcnow()
                        date_from = (now - timedelta(hours=3)).isoformat() + "Z"

                        headers = {
                            "Authorization": f"Bearer {access_token}"
                        }
                        params = {
                            "sort": "date_created",
                            "criteria": "desc",
                            "limit": 10,
                            "range": "date_created",
                            "begin_date": date_from,
                        }

                        # 🔁 Nueva forma: buscar directamente en /payments
                        r = requests.get(MP_API_URL, headers=headers, params=params, timeout=20)
                        if r.status_code != 200:
                            print(f"⚠️ Error {r.status_code} desde MP: {r.text[:200]}")
                            continue

                        data = r.json()
                        results = data.get("results", []) or data.get("elements", [])
                        print(f"📥 {len(results)} pagos recibidos para {m.name}")

                        for p in results:
                            if p.get("status") != "approved":
                                continue

                            pid = str(p.get("id"))
                            if session.query(Payment).filter_by(id=pid).first():
                                continue

                            payer_info = p.get("payer", {}) or {}
                            payer_name = (
                                f"{payer_info.get('first_name', '')} {payer_info.get('last_name', '')}"
                            ).strip() or "Desconocido"

                            new_p = Payment(
                                id=pid,
                                merchant_id=m.id,
                                payer_name=payer_name,
                                amount=float(p.get("transaction_amount", 0.0)),
                                status="approved",
                                date_created=datetime.fromisoformat(
                                    p.get("date_created").replace("Z", "")
                                ) if p.get("date_created") else datetime.utcnow(),
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
