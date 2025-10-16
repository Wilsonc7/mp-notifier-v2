import time
from flask import current_app
from apscheduler.schedulers.background import BackgroundScheduler
from app_v2.models import DB
from app_v2.clients.mp_client import process_payments

scheduler = BackgroundScheduler()


def run_polling_job():
    """
    Job ejecutado periódicamente por APScheduler para consultar pagos nuevos.
    Corre dentro del contexto de Flask, evitando errores de contexto.
    """
    try:
        # Importar aquí para evitar import circular
        from server_v2 import app

        with app.app_context():
            print("🔄 Ejecutando job de polling...")
            start = time.time()
            process_payments(DB)
            print(f"✅ Polling completado en {round(time.time() - start, 2)}s.")
    except Exception as e:
        print(f"❌ Error durante el polling: {e}")


def start_scheduler(app):
    """
    Inicializa el scheduler y programa el job de polling.
    """
    try:
        # Ejecutar dentro del contexto de la app Flask
        with app.app_context():
            if not scheduler.running:
                scheduler.add_job(run_polling_job, "interval", seconds=30)
                scheduler.start()
                print("[Scheduler] Iniciado cada 30 segundos.")
    except Exception as e:
        print(f"❌ Error al iniciar el scheduler: {e}")
