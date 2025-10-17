from flask import Flask, jsonify
from flask_cors import CORS
from datetime import datetime
from app_v2.models import DB
from app_v2.polling import start_scheduler

def create_app():
    app = Flask(__name__)
    app.config.from_object("app_v2.config.Config")

    # ✅ Habilitar CORS
    CORS(app)

    # ✅ Inicializar la base de datos con pre-ping para evitar conexiones muertas
    DB.init_app(app)

    with app.app_context():
        DB.create_all()
        print("📦 Tablas creadas o verificadas correctamente.")

    # ✅ Registrar blueprints (rutas del sistema)
    try:
        from app_v2.routes.devices import devices_bp
        from app_v2.routes.pagos import pagos_bp
        app.register_blueprint(devices_bp)
        app.register_blueprint(pagos_bp)
        print("🧩 Blueprints de dispositivos y pagos registrados correctamente.")
    except Exception as e:
        print(f"⚠️ Error registrando blueprints: {e}")

    # ✅ Iniciar el scheduler del polling dentro del contexto de la app
    try:
        start_scheduler(app)
    except Exception as e:
        print(f"⚠️ Error iniciando el scheduler: {e}")

    # ✅ Rutas simples de prueba
    @app.route("/")
    def home():
        return jsonify({
            "status": "ok",
            "message": "Servidor Flask MP-Notifier v2 en ejecución 🚀",
            "time": datetime.utcnow().isoformat()
        })

    @app.route("/health")
    def health():
        return jsonify({
            "status": "ok",
            "time": datetime.utcnow().isoformat(),
            "db_connected": DB.session.bind is not None
        })

    return app


# ==============================
# Punto de entrada
# ==============================
app = create_app()

if __name__ == "__main__":
    # ⚙️ Ejecución local (no necesaria en Render)
    app.run(host="0.0.0.0", port=10000, debug=True)
