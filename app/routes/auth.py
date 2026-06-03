"""
routes/auth.py
Authentication routes:
  GET  /login           — render login page
  GET  /auth/google     — start Google OAuth flow
  GET  /auth/callback   — handle Google OAuth callback
  POST /logout          — clear session
"""

import os
from flask import Blueprint, redirect, url_for, session, request, render_template, flash
from flask_login import login_user, logout_user, login_required, current_user
from authlib.integrations.flask_client import OAuth

from models import User

auth_bp = Blueprint("auth", __name__)

# Authlib OAuth registry is created once and attached to the app in create_app
# We access it via the app's extensions dict after registration.
# Using a module-level instance is simpler for blueprints:
oauth = OAuth()


def init_oauth(app):
    """Call this from create_app() after app is created."""
    oauth.init_app(app)
    oauth.register(
        name="google",
        client_id=os.environ.get("GOOGLE_CLIENT_ID"),
        client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


# ── Routes ──────────────────────────────────────────────────────────────────

@auth_bp.route("/login")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("groups.index"))
    return render_template("login.html")


@auth_bp.route("/auth/google")
def google_login():
    redirect_uri = url_for("auth.google_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route("/auth/callback")
def google_callback():
    try:
        token = oauth.google.authorize_access_token()
    except Exception:
        flash("Sign-in failed. Please try again.", "error")
        return redirect(url_for("auth.login"))

    userinfo = token.get("userinfo")
    if not userinfo or not userinfo.get("email"):
        flash("Could not retrieve account details from Google.", "error")
        return redirect(url_for("auth.login"))

    user = User.upsert_from_google(userinfo)
    login_user(user, remember=True)
    next_url = session.pop("next", None) or url_for("groups.index")
    return redirect(next_url)


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))