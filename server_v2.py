from flask import Flask
from flask_cors import CORS
from app_v2.models import DB
from app_v2.routes import bp as api_bp
from app_v2.polling import start_scheduler
from config import Config
import os


def create_app():
    """Crea y configura la aplicación Flask v2"""
    app = Flask(__name__)
    app.config.from_object(Config)

    # ===========================
    # Inicializar base de datos
    # ===========================
    DB.init_app(app)

    # Crear tablas si no existen
    with app.app_context():
        DB.create_all()
        print("📦 Tablas creadas o verificadas correctamente.")

    # ===========================
    # CORS y Blueprints
    # ===========================
    CORS(app)
    app.register_blueprint(api_bp)

    # ===========================
    # Iniciar Scheduler
    # ===========================
    try:
        start_scheduler(app)
        print("⏱️ Scheduler iniciado correctamente.")
    except Exception as e:
        print(f"[Scheduler] Error al iniciar: {e}")

    print("✅ Flask App v2 inicializada correctamente con SQLAlchemy.")
    return app


# ============================================================
# Crear instancia global (Render usa 'app' como entry point)
# ============================================================
app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Servidor corriendo en puerto {port}")
    app.run(host="0.0.0.0", port=port)
