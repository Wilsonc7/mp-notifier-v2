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

    # ✅ Inicializar SQLAlchemy con pre-ping (evita errores de conexión inactiva)
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}
    DB.init_app(app)

    with app.app_context():
        DB.create_all()
        print("📦 Tablas creadas o verificadas correctamente.")

    # ✅ Registrar blueprints
    try:
        from app_v2.routes.devices import devices_bp
        from app_v2.routes.pagos import pagos_bp
        from app_v2.routes_notify import bp_notify  # 🟢 Nuevo blueprint

        app.register_blueprint(devices_bp)
        app.register_blueprint(pagos_bp)
        app.register_blueprint(bp_notify)  # 🟢 Registrar /notify

        print("🧩 Blueprints registrados correctamente: devices, pagos, notify")

    except Exception as e:
        print(f"⚠️ Error registrando blueprints: {e}")

    # ✅ Iniciar el scheduler de polling
    try:
        start_scheduler(app)
        print("⏱️ Scheduler iniciado correctamente.")
    except Exception as e:
        print(f"⚠️ Error iniciando scheduler: {e}")

    # ==============================
    # RUTAS BÁSICAS
    # ==============================
    @app.route("/")
    def index():
        return jsonify({
            "status": "ok",
            "message": "Servidor Flask MP-Notifier v2 activo 🚀",
            "time": datetime.utcnow().isoformat()
        })

    @app.route("/health")
    def health():
        return jsonify({
            "status": "ok",
            "db_connected": DB.session.bind is not None,
            "time": datetime.utcnow().isoformat()
        })

    return app


# ==============================
# Punto de entrada
# ==============================
app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
