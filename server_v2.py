import os
from flask import Flask
from flask_cors import CORS

from app_v2.models import DB
from app_v2.routes import bp as api_bp
from app_v2.polling import start_scheduler

# ==============================
# CONFIGURACIÓN FLASK
# ==============================
app = Flask(__name__)
CORS(app)

# ✅ Configurar base de datos desde el entorno
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

DB.init_app(app)

# ==============================
# RUTAS
# ==============================
app.register_blueprint(api_bp)

# ==============================
# ARRANQUE
# ==============================
@app.before_first_request
def initialize():
    with app.app_context():
        print("📦 Tablas creadas o verificadas correctamente.")
        DB.create_all()

        start_scheduler()
        print("✅ Flask App v2 inicializada correctamente con SQLAlchemy.")

# ==============================
# MAIN
# ==============================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
