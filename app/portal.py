from flask import Blueprint, redirect, render_template, request, url_for

from .db import get_db

bp = Blueprint("portal", __name__)


@bp.app_context_processor
def inject_team():
    row = get_db().execute("SELECT name FROM team WHERE id = 1").fetchone()
    return {"team_name": row["name"] if row else None}


@bp.route("/")
def index():
    return render_template("index.html")


@bp.post("/team")
def set_team():
    name = (request.form.get("name") or "").strip()[:40]
    if name:
        db = get_db()
        db.execute("INSERT INTO team (id, name) VALUES (1, ?) "
                   "ON CONFLICT(id) DO UPDATE SET name = excluded.name", (name,))
        db.commit()
    return redirect(url_for("portal.index"))


@bp.route("/rules")
def rules():
    return render_template("rules.html")


@bp.route("/healthz")
def healthz():
    return {"status": "ok"}
