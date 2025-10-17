import requests
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from flask import current_app

from app_v2.models import DB, Merchant, Payment
from app_v2.security import decrypt_token

POLL_INTERVAL_SECONDS = 60
MP_API_URL = "https://api.mercadopago.com/v1/payments/search"

scheduler = BackgroundScheduler()

# ==============================
# POLLING PRINCIPAL
# ==============================
def run_polling_job():
    """Consulta los pagos recientes desde Mercado Pago y guarda nuevos."""
    print("🔄 Ejecutando job de polling...")

    # 🔧 Crear contexto Flask manualmente
    try:
        app = current_app._get_current_object()
    except RuntimeError:
        # Si no hay app activa (Render recién reiniciado)
        from app_v2.server_import import app  # pequeño helper que veremos abajo
        app_context = app.app_context()
        app_context.push()
        print("🧩 Contexto Flask creado manualmente para polling.")
    else:
        app_context = app.app_context()
        app_context.push()

    try:
        with DB.session.begin() as session:
            merchants = session.query(Merchant).all()

            for m in merchants:
                try:
                    print(f"📡 Consultando pagos recientes desde Mercado Pago para {m.name}...")

                    access_token = decrypt_token(m.mp_access_token_enc)
                    if not access_token:
                        print(f"⚠️ Token vacío o inválido para merchant {m.name}")
                        continue

                    now = datetime.utcnow()
                    date_from = (now - timedelta(hours=3)).isoformat() + "Z"

                    params = {
                        "sort": "date_created",
                        "criteria": "desc",
                        "begin_date": date_from,
                        "limit": 10,
                    }
                    headers = {"Authorization": f"Bearer {access_token}"}

                    r = requests.get(MP_API_URL, headers=headers, params=params, timeout=20)
                    if r.status_code != 200:
                        print(f"⚠️ Error {r.status_code} desde MP para {m.name}: {r.text[:200]}")
                        continue

                    data = r.json()
                    results = data.get("results", [])
                    print(f"📥 Recibidos {len(results)} pagos para {m.name}")

                    nuevos = 0
                    for p in results:
                        if p.get("status") != "approved":
                            continue

                        payment_id = str(p.get("id"))
                        if session.query(Payment).filter_by(id=payment_id).first():
                            continue  # evitar duplicados

                        payer_info = p.get("payer", {}) or {}
                        payer_name = (
                            f"{payer_info.get('first_name', '')} {payer_info.get('last_name', '')}"
                        ).strip() or "Desconocido"
                        amount = float(p.get("transaction_amount", 0.0))

                        new_payment = Payment(
                            id=payment_id,
                            merchant_id=m.id,
                            payer_name=payer_name,
                            amount=amount,
                            status="approved",
                            date_created=datetime.fromisoformat(
                                p.get("date_created").replace("Z", "")
                            )
                            if p.get("date_created")
                            else datetime.utcnow(),
                            created_at=datetime.utcnow(),
                        )
                        session.add(new_payment)
                        nuevos += 1

                    if nuevos:
                        session.commit()
                        print(f"💾 {nuevos} pagos nuevos guardados para {m.name}")

                except Exception as inner_e:
                    print(f"❌ Error procesando merchant {m.name}: {inner_e}")
                    session.rollback()

    except Exception as e:
        print(f"❌ Error general durante el polling: {e}")
    finally:
        app_context.pop()

# ==============================
# SCHEDULER
# ==============================
def start_scheduler():
    """Inicia el scheduler en background"""
    try:
        scheduler.add_job(run_polling_job, "interval", seconds=POLL_INTERVAL_SECONDS)
        scheduler.start()
        print(f"[Scheduler] Iniciado cada {POLL_INTERVAL_SECONDS} segundos.")
        print("⏱️ Scheduler iniciado correctamente.")
    except Exception as e:
        print(f"[Scheduler] Error al iniciar: {e}")
