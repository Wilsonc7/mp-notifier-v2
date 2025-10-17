import requests
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from app_v2.models import DB, Merchant, Payment
from app_v2.security import decrypt_token

# ==============================
# CONFIG
# ==============================
POLL_INTERVAL_SECONDS = 60  # cada 60 s para evitar saturar Render
MP_API_URL = "https://api.mercadopago.com/v1/payments/search"

scheduler = BackgroundScheduler()

# ==============================
# Función principal de polling
# ==============================
def run_polling_job():
    print("🔄 Ejecutando job de polling...")
    try:
        with DB.session() as session:
            merchants = session.query(Merchant).all()
            for m in merchants:
                try:
                    print(f"📡 Consultando pagos recientes desde Mercado Pago para {m.name}...")

                    # ✅ desencripta el access token
                    access_token = decrypt_token(m.mp_access_token_enc)
                    if not access_token:
                        print(f"⚠️ Token de acceso vacío o inválido para merchant {m.name}")
                        continue

                    # 🔍 ventana de tiempo de los últimos 3 h
                    now = datetime.utcnow()
                    date_from = (now - timedelta(hours=3)).isoformat() + "Z"

                    params = {
                        "sort": "date_created",
                        "criteria": "desc",
                        "begin_date": date_from,
                        "limit": 10
                    }

                    headers = {"Authorization": f"Bearer {access_token}"}
                    r = requests.get(MP_API_URL, headers=headers, params=params, timeout=20)

                    if r.status_code != 200:
                        print(f"⚠️ Error {r.status_code} desde Mercado Pago: {r.text}")
                        continue

                    data = r.json()
                    results = data.get("results", [])
                    print(f"📥 Recibidos {len(results)} pagos para {m.name}")

                    for p in results:
                        status = p.get("status", "")
                        if status != "approved":
                            continue  # solo pagos aprobados

                        payment_id = str(p.get("id"))
                        exists = session.query(Payment).filter_by(id=payment_id).first()
                        if exists:
                            continue  # ya guardado

                        payer_name = ""
                        payer_info = p.get("payer", {})
                        if payer_info:
                            payer_name = payer_info.get("first_name", "") + " " + payer_info.get("last_name", "")

                        amount = p.get("transaction_amount", 0.0)

                        new_payment = Payment(
                            id=payment_id,
                            merchant_id=m.id,
                            payer_name=payer_name.strip() or "Desconocido",
                            amount=amount,
                            status=status,
                            created_at=datetime.utcnow()
                        )
                        session.add(new_payment)
                        session.commit()
                        print(f"💾 Guardado pago {payment_id} - ${amount} de {payer_name}")

                except Exception as inner_e:
                    print(f"❌ Error en merchant {m.name}: {inner_e}")
                    session.rollback()
    except Exception as e:
        print(f"❌ Error durante el polling: {e}")


# ==============================
# Scheduler
# ==============================
def start_scheduler():
    """Inicia el scheduler en background"""
    try:
        scheduler.add_job(run_polling_job, "interval", seconds=POLL_INTERVAL_SECONDS)
        scheduler.start()
        print(f"[Scheduler] Iniciado cada {POLL_INTERVAL_SECONDS} segundos.")
    except Exception as e:
        print(f"[Scheduler] Error al iniciar: {e}")
