import os
from flask import Flask
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
from app_v2.config import DB
from app_v2.routes import bp as api_bp
from app_v2.polling import poll_all_merchants


def create_app():
    app = Flask(__name__)
    CORS(app)

    # =============================
    # 🔧 Configuración de base de datos
    # =============================
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    DB.init_app(app)

    # =============================
    # 📡 Registrar rutas principales
    # =============================
    app.register_blueprint(api_bp)

    # =============================
    # 🩺 Ruta de verificación (Render health check)
    # =============================
    @app.route("/health")
    def health():
        return {"ok": True, "ts": os.popen("date -u +%Y-%m-%dT%H:%M:%S.%N").read().strip()}

    # =============================
    # 🔁 Scheduler (con contexto Flask)
    # =============================
    scheduler = BackgroundScheduler()

    def run_polling():
        """Ejecuta el polling dentro del contexto Flask"""
        with app.app_context():
            try:
                poll_all_merchants(DB.session)
                print("[Scheduler] Polling ejecutado correctamente ✅")
            except Exception as e:
                print(f"[Scheduler Error] {e}")

    # Ejecutar cada 30 segundos
    scheduler.add_job(run_polling, trigger="interval", seconds=30)
    scheduler.start()

    return app


# =============================
# 🚀 Inicialización del servidor
# =============================
app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
