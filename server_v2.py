from flask import Flask
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
import os

from app_v2.config import Config
from app_v2.models import DB
from app_v2.routes import bp as api_bp
from app_v2.admin_routes import admin as admin_bp
from app_v2.polling import poll_all_merchants


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app)

    DB.init_app(app)

    with app.app_context():
        DB.create_all()

    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(admin_bp)

    # Polling automático
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(
        func=lambda: poll_all_merchants(DB.session),
        trigger="interval",
        seconds=Config.POLLING_INTERVAL_SECONDS,
    )
    scheduler.start()

    @app.route("/")
    def home():
        return "🚀 MP Notifier v2 Backend activo"

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
