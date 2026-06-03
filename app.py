"""
app.py
Flask application factory. Run with: python app.py  (dev)
                              or: gunicorn app:app  (production on Render)
"""

import os
from flask import Flask
from flask_login import LoginManager
from dotenv import load_dotenv

from db import get_db, ensure_indexes

load_dotenv()


def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ["FLASK_SECRET_KEY"]

    # ── Flask-Login setup ───────────────────────────────────────────────────
    login_manager = LoginManager(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please sign in to continue."

    from models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.get_by_id(user_id)

    # ── Register blueprints ─────────────────────────────────────────────────
    from routes.auth import auth_bp, init_oauth
    from routes.groups import groups_bp
    from routes.transactions import transactions_bp
    from routes.summary import summary_bp
    from routes.receipts import receipts_bp

    init_oauth(app)
    app.register_blueprint(auth_bp)
    app.register_blueprint(groups_bp)
    app.register_blueprint(transactions_bp)
    app.register_blueprint(summary_bp)
    app.register_blueprint(receipts_bp)

    # ── DB indexes ──────────────────────────────────────────────────────────
    with app.app_context():
        try:
            ensure_indexes()
        except Exception as e:
            app.logger.warning(f"Could not connect to MongoDB at startup: {e}")

    return app


app = create_app()

if __name__ == "__main__":
    debug = os.environ.get("FLASK_ENV") != "production"
    PORT = int(os.environ.get("PORT", 5000))
    app.run(debug=debug, port=PORT)