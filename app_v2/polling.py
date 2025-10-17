import requests
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from app_v2.models import DB, Merchant, Payment
from app_v2.security import decrypt_token

# Intervalo de consulta en segundos (más rápido = más inmediato)
POLL_INTERVAL_SECONDS = 15  
MP_API_URL = "https://api.mercadopago.com/v1/account/activities/search"

scheduler = BackgroundScheduler()


def run_polling_job(app):
    """Consulta movimientos de cuenta desde Mercado Pago (incluye transferencias y QR)."""
    print("🔄 Ejecutando job de polling (cuenta MP)...")
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

                        headers = {"Authorization": f"Bearer {access_token}"}
                        now = datetime.utcnow()
                        date_from = (now - timedelta(hours=6)).isoformat() + "Z"
                        params = {"limit": 10, "begin_date": date_from}

                        # 📡 Consultamos los movimientos recientes
                        r = requests.get(MP_API_URL, headers=headers, params=params, timeout=20)
                        if r.status_code != 200:
                            print(f"⚠️ Error {r.status_code} desde MP: {r.text[:200]}")
                            continue

                        data = r.json()
                        results = data.get("results") or data.get("data") or []

                        print(f"📥 {len(results)} movimientos recibidos para {m.name}")

                        for mov in results:
                            # Filtramos solo ingresos (type puede ser credit, inflow, debit, etc.)
                            mov_type = mov.get("type") or mov.get("operation_type")
                            if mov_type not in ["credit", "inflow"]:
                                continue

                            # ID único del movimiento
                            pid = str(mov.get("id") or mov.get("operation_id") or mov.get("activity_id"))
                            if not pid:
                                continue

                            # Evitar duplicados
                            if session.query(Payment).filter_by(id=pid).first():
                                continue

                            payer_name = (
                                mov.get("source", {}).get("nickname")
                                or mov.get("source", {}).get("name")
                                or mov.get("description")
                                or "Desconocido"
                            )

                            amount = abs(float(mov.get("amount", 0.0)))

                            # Guardamos el movimiento como pago aprobado
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
                            print(f"💾 Guardado ingreso {pid} - ${amount:.2f} de {payer_name}")

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
