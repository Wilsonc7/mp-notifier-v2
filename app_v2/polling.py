import os
import traceback
from apscheduler.schedulers.background import BackgroundScheduler
from flask import current_app

from app_v2.models import DB, Device, Payment
from app_v2.clients.mp_client import mp_search_payments


# ============================
# Función principal del polling
# ============================
def run_polling_job():
    """
    Consulta periódicamente las cuentas registradas en Mercado Pago
    y guarda nuevos pagos en la base de datos.
    """
    app = current_app._get_current_object()  # obtiene el contexto de Flask
    with app.app_context():
        try:
            session = DB.session
            devices = session.query(Device).all()

            if not devices:
                print("[Polling] No hay dispositivos registrados.")
                return

            for d in devices:
                if not d.access_token:
                    continue

                try:
                    # Consulta últimos pagos desde Mercado Pago
                    data = mp_search_payments(d.access_token)
                    results = data.get("results", [])

                    for p in results:
                        payment_id = str(p.get("id"))
                        existing = session.query(Payment).filter_by(id=payment_id).first()
                        if existing:
                            continue  # ya está registrado

                        payer = p.get("payer", {}).get("email") or p.get("payer", {}).get("first_name") or "Desconocido"
                        amount = p.get("transaction_amount", 0.0)
                        status = p.get("status", "unknown")

                        new_payment = Payment(
                            id=payment_id,
                            payer_name=payer,
                            amount=amount,
                            status=status,
                            device_id=d.id
                        )
                        session.add(new_payment)
                        session.commit()

                        print(f"[Polling] Nuevo pago guardado: {payment_id} (${amount})")

                except Exception as e:
                    session.rollback()
                    print(f"[Polling] Error al consultar pagos de {d.name}: {e}")

            print("[Scheduler] Polling ejecutado correctamente ✅")

        except Exception as e:
            print(f"[Polling] Error general: {e}")
            traceback.print_exc()
        finally:
            session.close()


# ============================
# Scheduler (Render-friendly)
# ============================
def start_scheduler(app):
    """
    Inicia el scheduler que ejecuta el polling cada X segundos.
    """
    try:
        interval = int(os.environ.get("POLLING_INTERVAL_SECONDS", 30))
        scheduler = BackgroundScheduler(daemon=True)
        scheduler.add_job(func=run_polling_job, trigger="interval", seconds=interval)
        scheduler.start()
        print(f"[Scheduler] Iniciado cada {interval} segundos.")
    except Exception as e:
        print(f"[Scheduler] Error al iniciar: {e}")
