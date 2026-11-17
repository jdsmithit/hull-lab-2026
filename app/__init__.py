"""Hull disclosure labs: three offline, hands-on labs in one Flask app.

Everything is served from one process on port 8080. No external network calls,
no CDNs. All organisations, people and data are fictional.
"""
import os
import secrets

from flask import Flask

from . import db, portal, lab1, lab2, lab3, facilitator


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
        DATABASE=os.environ.get("LAB_DB") or os.path.join(app.instance_path, "labs.db"),
        FACILITATOR_PIN=os.environ.get("FACILITATOR_PIN", "hull2026"),
        SESSION_COOKIE_SAMESITE="Lax",
    )
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    app.register_blueprint(portal.bp)
    app.register_blueprint(lab1.bp)
    app.register_blueprint(lab1.orgs_bp)
    app.register_blueprint(lab2.bp)
    app.register_blueprint(lab3.bp)
    app.register_blueprint(lab3.hf)
    app.register_blueprint(facilitator.bp)
    return app
