import requests
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from app_v2.models import DB, Merchant, Payment
from app_v2.security import decrypt_token

# ==============================
# CONFIG
# ==============================
POLL_INTERVAL_SECONDS = 15   # 🔁 cada 15 segundos → detección casi en tiempo real
MP_API_URL = "https://api.mercadopago.com/v1/account/movements/search"

scheduler = BackgroundScheduler()

# ==============================
# FUNCIONES DE POLLING
# ==============================
def run_polling_job(app):
    """Consulta movimientos de cuenta (pagos + transferencias)"""
    print("🔄 Ejecutando job de polling…")
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

                        # Buscar movimientos de las últimas 3 horas
                        now = datetime.utcnow()
                        date_from = (now - timedelta(hours=3)).isoformat() + "Z"
                        params = {"begin_date": date_from, "limit": 10}
                        headers = {"Authorization": f"Bearer {access_token}"}

                        r = requests.get(MP_API_URL, headers=headers, params=params, timeout=20)
                        if r.status_code != 200:
                            print(f"⚠️ Error {r.status_code} desde MP: {r.text[:150]}")
                            continue

                        data = r.json()
                        results = data.get("results", [])
                        print(f"📥 {len(results)} movimientos recibidos para {m.name}")

                        for mov in results:
                            mtype = mov.get("type")
                            status = mov.get("status")

                            # Solo pagos o transferencias aprobadas
                            if mtype not in ["payment", "transfer_received"] or status != "approved":
                                continue

                            mov_id = str(mov.get("id"))
                            if session.query(Payment).filter_by(id=mov_id).first():
                                continue  # evitar duplicados

                            payer_info = mov.get("source", {}).get("name", "Desconocido")
                            amount = float(mov.get("amount", 0.0))
                            created = mov.get("date_created") or mov.get("date")

                            new_payment = Payment(
                                id=mov_id,
                                merchant_id=m.id,
                                payer_name=payer_info,
                                amount=amount,
                                status="approved",
                                date_created=datetime.fromisoformat(
                                    created.replace("Z", "")
                                ) if created else datetime.utcnow(),
                                created_at=datetime.utcnow(),
                            )

                            session.add(new_payment)
                            session.commit()
                            print(f"💾 Guardado movimiento {mov_id} - ${amount} de {payer_info}")

                    except Exception as sub_e:
                        session.rollback()
                        print(f"❌ Error procesando merchant {m.name}: {sub_e}")

    except Exception as e:
        print(f"❌ Error general durante el polling: {e}")

# ==============================
# SCHEDULER
# ==============================
def start_scheduler(app):
    """Inicia el scheduler con app.context()"""
    try:
        scheduler.add_job(run_polling_job, "interval", seconds=POLL_INTERVAL_SECONDS, args=[app])
        scheduler.start()
        print(f"[Scheduler] Iniciado cada {POLL_INTERVAL_SECONDS} s.")
        print("⏱️ Scheduler activo con contexto Flask.")
    except Exception as e:
        print(f"[Scheduler] Error al iniciar: {e}")
