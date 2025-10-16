import os
from flask import Flask, jsonify
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler

from app_v2.models import DB
from app_v2.routes import bp as api_bp
from app_v2.polling import run_polling_job
from app_v2.config import Config


# =========================================================
# Crear la aplicación Flask y registrar todos los módulos
# =========================================================
def create_app():
    app = Flask(__name__)

    # Cargar configuración general
    app.config.from_object(Config)

    # Inicializar SQLAlchemy correctamente
    DB.init_app(app)

    # Habilitar CORS
    CORS(app)

    # Registrar las rutas principales (API)
    app.register_blueprint(api_bp)

    # =====================================================
    # Endpoint raíz y de health check
    # =====================================================
    @app.get("/")
    def index():
        return jsonify({"ok": True, "message": "MP Notifier v2 funcionando correctamente 🚀"}), 200

    @app.get("/health")
    def health():
        return jsonify({"ok": True, "ts": "OK"}), 200

    return app


# =========================================================
# Inicialización global
# =========================================================
app = create_app()


# =========================================================
# Scheduler (polling en segundo plano)
# =========================================================
def start_scheduler():
    """Inicia el proceso recurrente que consulta pagos en segundo plano"""
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(
        run_polling_job,
        "interval",
        seconds=Config.POLLING_INTERVAL_SECONDS,
        id="polling_task",
        replace_existing=True,
    )
    scheduler.start()
    print("[Scheduler] Polling inicializado correctamente ⏱️")


# =========================================================
# Inicialización antes del primer request
# =========================================================
@app.before_first_request
def initialize():
    """Crea tablas si no existen y arranca el scheduler"""
    with app.app_context():
        try:
            DB.create_all()
            print("[DB] Tablas creadas/verificadas correctamente ✅")
        except Exception as e:
            print(f"[DB] Error al crear tablas: {e}")
    start_scheduler()


# =========================================================
# Ejecutar la app
# =========================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"[SERVER] Iniciando MP Notifier v2 en puerto {port} 🌐")
    app.run(host="0.0.0.0", port=port)
