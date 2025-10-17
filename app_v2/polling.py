import requests
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from app_v2.models import DB, Merchant, Payment
from app_v2.security import decrypt_token

# ==============================
# CONFIG
# ==============================
POLL_INTERVAL_SECONDS = 15  # 🔁 cada 15 segundos
MP_API_URL = "https://api.mercadopago.com/v1/account/movements/search"

scheduler = BackgroundScheduler()

# ==============================
# POLLING PRINCIPAL
# ==============================
def run_polling_job(app):
    """Consulta movimientos recientes (pagos y transferencias)."""
    print("\n🔄 Ejecutando job de polling…")
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

                        now = datetime.utcnow()
                        date_from = (now - timedelta(hours=3)).isoformat() + "Z"
                        params = {"begin_date": date_from, "limit": 10}
                        headers = {"Authorization": f"Bearer {access_token}"}

                        response = requests.get(MP_API_URL, headers=headers, params=params, timeout=20)

                        if response.status_code != 200:
                            print(f"⚠️ Error {response.status_code} desde MP: {response.text[:150]}")
                            continue

                        data = response.json()
                        results = data.get("results", [])
                        print(f"📥 {len(results)} movimientos encontrados para {m.name}")

                        for mov in results:
                            mtype = mov.get("type", "unknown")
                            status = mov.get("status", "unknown")
                            source = mov.get("source", {}) or {}
                            payer_name = source.get("name", "Desconocido")
                            mov_id = str(mov.get("id", ""))
                            amount = float(mov.get("amount", 0.0))
                            created = mov.get("date_created") or mov.get("date")

                            # Mostrar información detallada en consola
                            print(f"🧾 Movimiento: {mtype} | Estado: {status} | Monto: ${amount:.2f} | Origen: {payer_name}")

                            # Solo guardar entradas de dinero aprobadas
                            if mtype not in ["payment", "transfer_received"] or status != "approved":
                                continue

                            # Evitar duplicados
                            if session.query(Payment).filter_by(id=mov_id).first():
                                continue

                            # Guardar nuevo movimiento
                            new_payment = Payment(
                                id=mov_id,
                                merchant_id=m.id,
                                payer_name=payer_name,
                                amount=amount,
                                status="approved",
                                date_created=datetime.fromisoformat(
                                    created.replace("Z", "")
                                ) if created else datetime.utcnow(),
                                created_at=datetime.utcnow(),
                            )

                            session.add(new_payment)
                            session.commit()
                            print(f"💾 Guardado nuevo ingreso: {mtype} ${amount:.2f} de {payer_name}")

                    except Exception as sub_e:
                        session.rollback()
                        print(f"❌ Error procesando merchant {m.name}: {sub_e}")

    except Exception as e:
        print(f"❌ Error general durante el polling: {e}")

# ==============================
# INICIO DEL SCHEDULER
# ==============================
def start_scheduler(app):
    """Inicia el scheduler en segundo plano."""
    try:
        scheduler.add_job(run_polling_job, "interval", seconds=POLL_INTERVAL_SECONDS, args=[app])
        scheduler.start()
        print(f"[Scheduler] Iniciado cada {POLL_INTERVAL_SECONDS} segundos.")
        print("⏱️ Scheduler activo con contexto Flask.")
    except Exception as e:
        print(f"[Scheduler] Error al iniciar: {e}")
