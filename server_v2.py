from flask import Flask
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
from app_v2.routes import bp as api_bp
from app_v2.polling import poll_all_merchants
from app_v2.utils.config import DB
import os


def create_app():
    app = Flask(__name__)
    CORS(app)

    # Configuración de la base de datos
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    DB.init_app(app)

    # Registrar las rutas principales
    app.register_blueprint(api_bp)

    # Health check simple (para Render)
    @app.route("/health")
    def health():
        return {"status": "ok"}, 200

    # =========================
    # 🔁 Scheduler de Polling
    # =========================
    scheduler = BackgroundScheduler()

    def run_polling():
        """Ejecuta el polling dentro del contexto de Flask"""
        with app.app_context():
            try:
                poll_all_merchants(DB.session)
            except Exception as e:
                print(f"[Polling Error] {e}")

    # Ejecutar cada 30 segundos
    scheduler.add_job(run_polling, trigger="interval", seconds=30)

    scheduler.start()

    return app


# =========================
# 🚀 Punto de entrada
# =========================
app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
