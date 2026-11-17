"""Lab 3: find the IDOR in HullFerries, then report it.

HullFerries is a deliberately vulnerable, fictional ferry booking site:
GET /hullferries/api/bookings/<id> checks that you are logged in, but not that
the booking is yours. Any booking that isn't yours carries a lab proof token,
so viewing ONE other record is enough. The SOC view then shows each team how
much they touched.
"""
import random
from datetime import datetime, timezone
from functools import wraps

from flask import (Blueprint, Response, jsonify, redirect, render_template,
                   request, session, url_for)

from .db import get_db

bp = Blueprint("lab3", __name__, url_prefix="/lab3")
hf = Blueprint("hullferries", __name__, url_prefix="/hullferries")

STUDENT_EMAIL = "student@hullferries.test"
STUDENT_PASSWORD = "seasick2026"
OWN_BOOKING = 1041
FIRST_ID, LAST_ID = 1001, 1400
PROOF = "HULL{one-record-is-enough}"

REPORT_FIELDS = [
    ("title", "1. Title", "Bug class + location + impact"),
    ("summary", "2. Summary", "Two sentences: what's broken, who is harmed"),
    ("asset", "3. Affected asset", "Exact URL / endpoint, parameter, time tested"),
    ("steps", "4. Steps to reproduce", "Numbered steps a stranger could follow cold"),
    ("evidence", "5. Evidence", "Request/response. Redact personal data. Include the lab proof token."),
    ("impact", "6. Impact and severity", "Realistic worst case. CVSS 4.0 vector if you can."),
    ("fix", "7. Suggested fix and your details", "One-line fix, how to reach you, credit wanted?"),
]

RUBRIC = [
    ("Title names bug class, location and impact", 2),
    ("Steps a stranger could reproduce", 3),
    ("Evidence redacted, minimum data shown", 2),
    ("Honest severity", 2),
    ("Tone: no demands, offers to follow their timeline", 1),
]

_FIRST = ["Amira", "Ben", "Chloe", "Dawid", "Erin", "Farah", "George", "Hana", "Isaac", "Jade",
          "Kofi", "Lena", "Mateo", "Nia", "Oscar", "Priya", "Quinn", "Rosa", "Sam", "Tomasz"]
_LAST = ["Abbott", "Brennan", "Chowdhury", "Dvorak", "Ellis", "Fischer", "Gallagher", "Haddad",
         "Iqbal", "Jansen", "Kowalski", "Larsen", "Mensah", "Novak", "O'Neill", "Petrov"]
_ROUTES = ["Kingston Quay → Nordhaven", "Nordhaven → Kingston Quay",
           "Kingston Quay → Vesterby", "Vesterby → Kingston Quay"]
_CABINS = ["Inside twin", "Outside twin", "Commodore suite", "Reclining seat"]
_VEHICLES = ["Car", "Motorbike", "None", "Van", "Car + trailer"]


def _build_bookings():
    rng = random.Random(2026)
    out = {}
    for bid in range(FIRST_ID, LAST_ID + 1):
        out[bid] = {
            "booking_id": bid,
            "passenger": f"{rng.choice(_FIRST)} {rng.choice(_LAST)}",
            "passport_number": f"TEST{rng.randint(100000, 999999)}",
            "date_of_birth": f"{rng.randint(1950, 2005)}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}",
            "route": rng.choice(_ROUTES),
            "sailing": f"2026-12-{rng.randint(1, 28):02d}",
            "cabin": rng.choice(_CABINS),
            "vehicle": rng.choice(_VEHICLES),
            "email": f"passenger{bid}@example.test",
        }
    out[OWN_BOOKING].update({"passenger": "Hull Student", "email": STUDENT_EMAIL,
                             "passport_number": "TEST000000"})
    return out


BOOKINGS = _build_bookings()


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _log(status, booking_id=None):
    db = get_db()
    db.execute("INSERT INTO lab3_requests (ts, method, path, status, booking_id) VALUES (?, ?, ?, ?, ?)",
               (_now(), request.method, request.full_path.rstrip("?"), status, booking_id))
    db.commit()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("hf_user") != STUDENT_EMAIL:
            if request.path.startswith("/hullferries/api/"):
                _log(401, kwargs.get("booking_id"))
                return jsonify({"error": "login required"}), 401
            return redirect(url_for("hullferries.login"))
        return view(*args, **kwargs)
    return wrapped


# ---------------------------------------------------------------- HullFerries (the target)

@hf.route("/")
def home():
    return render_template("hullferries/home.html")


@hf.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if (request.form.get("email", "").strip().lower() == STUDENT_EMAIL
                and request.form.get("password") == STUDENT_PASSWORD):
            session["hf_user"] = STUDENT_EMAIL
            return redirect(url_for("hullferries.my_bookings"))
        error = "Wrong email or password."
    return render_template("hullferries/login.html", error=error)


@hf.route("/logout")
def logout():
    session.pop("hf_user", None)
    return redirect(url_for("hullferries.home"))


@hf.route("/my-bookings")
@login_required
def my_bookings():
    return render_template("hullferries/my_bookings.html", booking_id=OWN_BOOKING)


@hf.route("/api/bookings/<int:booking_id>")
@login_required
def api_booking(booking_id):
    booking = BOOKINGS.get(booking_id)
    if booking is None:
        _log(404, booking_id)
        return jsonify({"error": "booking not found"}), 404
    # The vulnerability: no check that the booking belongs to the logged-in user.
    data = dict(booking)
    if booking_id != OWN_BOOKING:
        data["lab_proof"] = PROOF
    _log(200, booking_id)
    return jsonify(data)


@hf.route("/.well-known/security.txt")
def security_txt():
    base = request.host_url.rstrip("/") + "/hullferries"
    body = ("Contact: mailto:security@hullferries.test\n"
            "Expires: 2027-06-30T23:59:59Z\n"
            f"Policy: {base}/vdp\n"
            "Preferred-Languages: en\n"
            f"Canonical: {base}/.well-known/security.txt\n")
    return Response(body, content_type="text/plain; charset=utf-8")


@hf.route("/vdp")
def vdp():
    return render_template("hullferries/vdp.html")


# ---------------------------------------------------------------- Lab 3 brief, SOC view, report

@bp.route("/")
def brief():
    return render_template("lab3/brief.html", email=STUDENT_EMAIL, password=STUDENT_PASSWORD)


def soc_stats():
    db = get_db()
    total = db.execute("SELECT COUNT(*) FROM lab3_requests").fetchone()[0]
    others = db.execute("SELECT COUNT(DISTINCT booking_id) FROM lab3_requests WHERE status = 200 "
                        "AND booking_id IS NOT NULL AND booking_id != ?", (OWN_BOOKING,)).fetchone()[0]
    errors = db.execute("SELECT COUNT(*) FROM lab3_requests WHERE status >= 400").fetchone()[0]
    span = db.execute("SELECT MIN(ts), MAX(ts) FROM lab3_requests").fetchone()
    recent = db.execute("SELECT ts, method, path, status FROM lab3_requests ORDER BY id DESC LIMIT 25").fetchall()
    if others == 0:
        verdict = ("Not found yet", "You haven't viewed anyone else's booking yet.")
    elif others == 1:
        verdict = ("Researcher", "One other record: enough to prove the bug. This is what a good report looks like.")
    elif others <= 10:
        verdict = ("Getting greedy", f"{others} other customers' records. One was enough to prove it.")
    else:
        verdict = ("Incident", f"{others} other customers' records. To the company, this now looks like a "
                               "data breach, not research.")
    return {"total": total, "others": others, "errors": errors, "first": span[0], "last": span[1],
            "recent": recent, "verdict": verdict}


@bp.route("/soc")
def soc():
    return render_template("lab3/soc.html", s=soc_stats())


def _report():
    row = get_db().execute("SELECT body FROM lab3_report WHERE id = 1").fetchone()
    return row["body"] if row else None


def build_markdown(form, team):
    lines = [f"# {form.get('title') or 'Vulnerability report'}", "",
             f"*Reported by: {team or 'Team'} · Target: HullFerries (lab) · {_now()} UTC*", ""]
    for key, label, _hint in REPORT_FIELDS[1:]:
        lines += [f"## {label.split('. ', 1)[1]}", "", (form.get(key) or "").strip() or "_(empty)_", ""]
    return "\n".join(lines)


@bp.route("/report", methods=["GET", "POST"])
def report():
    if request.method == "POST":
        form = {k: (request.form.get(k) or "")[:4000] for k, _l, _h in REPORT_FIELDS}
        team = get_db().execute("SELECT name FROM team WHERE id = 1").fetchone()
        body = build_markdown(form, team["name"] if team else None)
        db = get_db()
        db.execute("INSERT INTO lab3_report (id, body, updated) VALUES (1, ?, ?) "
                   "ON CONFLICT(id) DO UPDATE SET body = excluded.body, updated = excluded.updated",
                   (body, _now()))
        db.commit()
        session["report_form"] = form
        return redirect(url_for("lab3.report_done"))
    return render_template("lab3/report.html", fields=REPORT_FIELDS, values=session.get("report_form", {}),
                           rubric=RUBRIC)


@bp.route("/report/done")
def report_done():
    body = _report()
    if body is None:
        return redirect(url_for("lab3.report"))
    return render_template("lab3/report_done.html", body=body, rubric=RUBRIC)


@bp.route("/report.md")
def report_md():
    body = _report()
    if body is None:
        return redirect(url_for("lab3.report"))
    return Response(body, content_type="text/markdown; charset=utf-8",
                    headers={"Content-Disposition": "attachment; filename=hullferries-report.md"})
