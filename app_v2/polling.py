import requests
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from app_v2.models import DB, Merchant, Payment
from app_v2.security import decrypt_token

# 🔁 Intervalo de consulta
POLL_INTERVAL_SECONDS = 15

# 🧾 Nuevo endpoint de Mercado Pago que lista todas las actividades (pagos + transferencias)
MP_API_URL = "https://api.mercadopago.com/v1/account/activities/search"

scheduler = BackgroundScheduler()

def run_polling_job(app):
    """Consulta todas las actividades recientes de cada merchant (pagos o transferencias)."""
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

                        # Buscamos las últimas 3 horas de movimientos
                        now = datetime.utcnow()
                        date_from = (now - timedelta(hours=3)).isoformat() + "Z"

                        payload = {
                            "range": {"date_created": {"from": date_from}},
                            "filters": {"event_types": ["transfer", "payment"]},
                            "limit": 10,
                            "sort": {"field": "date_created", "order": "desc"},
                        }

                        headers = {
                            "Authorization": f"Bearer {access_token}",
                            "Content-Type": "application/json",
                        }

                        # ✅ POST (no GET)
                        r = requests.post(MP_API_URL, headers=headers, json=payload, timeout=20)

                        if r.status_code != 200:
                            print(f"⚠️ Error {r.status_code} desde MP: {r.text[:200]}")
                            continue

                        data = r.json()
                        results = data.get("results", [])
                        print(f"📥 {len(results)} actividades recibidas para {m.name}")

                        for item in results:
                            # Determinar si es pago o transferencia
                            event_type = item.get("event_type", "")
                            tx = item.get("transaction", {})

                            if not tx:
                                continue

                            pid = str(tx.get("id") or tx.get("external_id") or f"tx_{datetime.utcnow().timestamp()}")
                            if session.query(Payment).filter_by(id=pid).first():
                                continue

                            amount = float(tx.get("amount", 0.0))
                            payer_name = (
                                tx.get("counterparty_name")
                                or tx.get("description")
                                or "Desconocido"
                            )

                            new_p = Payment(
                                id=pid,
                                merchant_id=m.id,
                                payer_name=payer_name,
                                amount=amount,
                                status="approved",
                                date_created=datetime.utcnow(),
                                created_at=datetime.utcnow(),
                            )
                            session.add(new_p)
                            session.commit()
                            print(f"💾 Guardado {event_type}: ${amount} de {payer_name}")

                    except Exception as sub_e:
                        session.rollback()
                        print(f"❌ Error procesando merchant {m.name}: {sub_e}")

    except Exception as e:
        print(f"❌ Error general durante el polling: {e}")


def start_scheduler(app):
    """Inicia el scheduler con el contexto Flask activo"""
    try:
        scheduler.add_job(run_polling_job, "interval", seconds=POLL_INTERVAL_SECONDS, args=[app])
        scheduler.start()
        print(f"[Scheduler] Iniciado cada {POLL_INTERVAL_SECONDS} segundos.")
        print("⏱️ Scheduler activo con contexto Flask.")
    except Exception as e:
        print(f"[Scheduler] Error al iniciar: {e}")
