import time
from flask import current_app
from app_v2.models import DB
from app_v2.utils.mp_client import process_payments


def run_polling_job():
    """
    Job ejecutado periódicamente por APScheduler para consultar pagos nuevos.
    Ahora corre dentro del contexto de Flask, evitando errores de contexto.
    """
    try:
        # Importar aquí para evitar import circular
        from server_v2 import app

        # Abrimos un contexto de aplicación de Flask
        with app.app_context():
            print("🔄 Ejecutando job de polling...")
            start = time.time()

            # Procesar pagos pendientes
            process_payments(DB)

            print(f"✅ Polling completado en {round(time.time() - start, 2)}s.")
    except Exception as e:
        print(f"❌ Error durante el polling: {e}")
