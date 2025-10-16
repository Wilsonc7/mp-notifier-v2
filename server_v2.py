import os
from flask import Flask, jsonify
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler

from app_v2.models import DB
from app_v2.routes import bp as api_bp
from app_v2.polling import run_polling_job
from app_v2.config import Config


# ============================
# Crear la aplicación Flask
# ============================
def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Inicializar extensiones
    DB.init_app(app)
    CORS(app)

    # Registrar Blueprint
    app.register_blueprint(api_bp)

    # Rutas básicas
    @app.get("/")
    def index():
        return jsonify({"ok": True, "message": "MP Notifier v2 funcionando correctamente 🚀"}), 200

    @app.get("/health")
    def health():
        return jsonify({"ok": True, "status": "healthy"}), 200

    return app


# ============================
# Crear instancia global de app
# ============================
app = create_app()


# ============================
# Scheduler
# ============================
def start_scheduler():
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


# ============================
# Setup inicial antes del primer request
# ============================
@app.before_first_request
def setup():
    with app.app_context():
        try:
            DB.create_all()
            print("[DB] Tablas creadas/verificadas correctamente ✅")
        except Exception as e:
            print(f"[DB] Error creando tablas: {e}")
    start_scheduler()


# ============================
# Main
# ============================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
