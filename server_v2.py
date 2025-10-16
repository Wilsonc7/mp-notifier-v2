from flask import Flask
from flask_cors import CORS
from app_v2.models import DB
from app_v2.routes import bp as api_bp
from app_v2.polling import start_scheduler
from config import Config
import os


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Inicializar base de datos
    DB.init_app(app)

    # CORS y rutas
    CORS(app)
    app.register_blueprint(api_bp)

    # Crear tablas si no existen
    with app.app_context():
        DB.create_all()

    # Iniciar scheduler
    start_scheduler(app)

    print("🚀 Servidor Flask v2 inicializado correctamente.")
    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
