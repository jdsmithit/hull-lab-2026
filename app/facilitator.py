"""Facilitator page: answer keys, this team's progress, and a reset button. PIN-protected."""
import hmac

from flask import (Blueprint, current_app, redirect, render_template, request,
                   session, url_for)

from . import lab1, lab2, lab3
from .db import get_db, reset_all

bp = Blueprint("facilitator", __name__, url_prefix="/facilitator")


def _authed():
    return session.get("facilitator") is True


@bp.route("/", methods=["GET", "POST"])
def index():
    error = None
    if request.method == "POST":
        if hmac.compare_digest(request.form.get("pin", ""), current_app.config["FACILITATOR_PIN"]):
            session["facilitator"] = True
            return redirect(url_for("facilitator.index"))
        error = "Wrong PIN."
    if not _authed():
        return render_template("facilitator/login.html", error=error)
    db = get_db()
    progress = {
        "lab1": db.execute("SELECT COUNT(*) FROM lab1_answers").fetchone()[0],
        "lab2": db.execute("SELECT COUNT(*) FROM lab2_answers").fetchone()[0],
        "lab3_report": db.execute("SELECT COUNT(*) FROM lab3_report").fetchone()[0],
    }
    return render_template("facilitator/index.html", orgs=lab1.ORGS, cards=lab2.CARDS,
                           buckets=lab2.BUCKETS, progress=progress, soc=lab3.soc_stats(),
                           proof=lab3.PROOF)


@bp.post("/reset")
def reset():
    if _authed():
        reset_all()
        session.clear()
        session["facilitator"] = True
    return redirect(url_for("facilitator.index"))


@bp.route("/logout")
def logout():
    session.pop("facilitator", None)
    return redirect(url_for("portal.index"))
