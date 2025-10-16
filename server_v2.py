from flask import Flask, jsonify
from flask_cors import CORS
from app_v2.models import DB
from app_v2.routes import bp as api_bp
from app_v2.polling import start_scheduler
from app_v2.config import Config


def create_app():
    """
    Crea e inicializa la aplicación Flask principal.
    Compatible con Render y Gunicorn.
    """
    app = Flask(__name__)

    # Carga configuración general
    app.config.from_object(Config)

    # Inicializa SQLAlchemy correctamente (soluciona error de contexto)
    DB.init_app(app)

    # Permite acceso desde el ESP32, navegadores, etc.
    CORS(app, resources={r"/*": {"origins": "*"}})

    # Registra las rutas principales
    app.register_blueprint(api_bp)

    # ============================
    # Endpoints básicos
    # ============================
    @app.get("/")
    def index():
        """Endpoint base para verificar disponibilidad"""
        return jsonify({"ok": True, "message": "API BlackDog MP Notifier v2 funcionando ✅"}), 200

    @app.get("/health")
    def health():
        """Endpoint de salud para monitoreo"""
        return jsonify({"ok": True, "status": "healthy"}), 200

    # ============================
    # Inicializa scheduler (polling)
    # ============================
    with app.app_context():
        try:
            start_scheduler(app)
            print("[Scheduler] Iniciado correctamente ✅")
        except Exception as e:
            print(f"[Scheduler] Error al iniciar: {e}")

    return app


# =========================================================
# Punto de entrada principal (usado por Gunicorn o local)
# =========================================================
app = create_app()

if __name__ == "__main__":
    # Modo desarrollo local
    app.run(host="0.0.0.0", port=10000, debug=True)
