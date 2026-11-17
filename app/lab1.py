"""Lab 1: security.txt hunt across ten fictional organisations.

Each organisation is reachable two ways:
  path-based:  http://localhost:8080/o/<slug>/.well-known/security.txt
  host-based:  http://<slug>.localhost:8080/.well-known/security.txt
Each one teaches one lesson about RFC 9116.
"""
from datetime import date, timedelta

from flask import (Blueprint, Response, abort, redirect, render_template,
                   request, url_for)

from .db import get_db

bp = Blueprint("lab1", __name__, url_prefix="/lab1")
orgs_bp = Blueprint("orgs", __name__)

PLAIN = "text/plain; charset=utf-8"
HTML_RAW = "text/html; charset=utf-8"  # served raw, for the wrong-content-type lesson
PAGE = "page"                          # rendered inside the org's site template

FAKE_KEY = """-----BEGIN PGP PUBLIC KEY BLOCK-----

(Lab placeholder: not a real key. In real life, import this
key and use it to encrypt sensitive report details.)
-----END PGP PUBLIC KEY BLOCK-----
"""


def _vdp(name, contact):
    return (f"<h2>Vulnerability disclosure policy</h2>"
            f"<p>{name} welcomes reports from security researchers.</p>"
            f"<h3>In scope</h3><ul><li>Our public website and customer portal</li></ul>"
            f"<h3>Out of scope</h3><ul><li>Denial of service, spam, social engineering of staff</li>"
            f"<li>Third-party services we use</li></ul>"
            f"<h3>Safe harbour</h3><p>If you follow this policy, we will not take legal action "
            f"against you for good-faith research.</p>"
            f"<h3>How to report</h3><p>{contact}</p>"
            f"<p>We aim to reply within 5 working days and to fix valid issues within 90 days.</p>")


def _hall(name):
    return (f"<h2>Hall of fame</h2><p>{name} thanks these researchers for reporting "
            f"issues responsibly:</p><ul><li>A. Researcher</li><li>B. Student</li></ul>")


ORGS = [
    {
        "slug": "brightwater-bank", "name": "Brightwater Bank", "sector": "Banking", "color": "#0b5d4b",
        "footer": [("Vulnerability disclosure", "vdp"), ("Hall of fame", "hall-of-fame")],
        "files": {
            ".well-known/security.txt": (PLAIN,
                "# Brightwater Bank security contact\n"
                "Contact: mailto:security@brightwater-bank.test\n"
                "Contact: {base}/vdp\n"
                "Expires: {expires}\n"
                "Encryption: {base}/pgp-key.txt\n"
                "Acknowledgments: {base}/hall-of-fame\n"
                "Policy: {base}/vdp\n"
                "Preferred-Languages: en\n"
                "Canonical: {base}/.well-known/security.txt\n"),
            "pgp-key.txt": (PLAIN, FAKE_KEY),
            "vdp": (PAGE, _vdp("Brightwater Bank", "Email security@brightwater-bank.test. "
                                                    "Encrypt sensitive details with our PGP key.")),
            "hall-of-fame": (PAGE, _hall("Brightwater Bank")),
        },
        "score": 7,
        "route": "security@brightwater-bank.test (encrypted with their PGP key), following the policy at /vdp.",
        "lesson": "The model file: every field present, Expires in the future, a policy, a key and a hall of fame.",
    },
    {
        "slug": "humberline-freight", "name": "Humberline Freight", "sector": "Logistics", "color": "#8a4b0f",
        "footer": [("Responsible disclosure", "vdp")],
        "files": {
            ".well-known/security.txt": (PLAIN,
                "Contact: mailto:psirt@humberline-freight.test\n"
                "Expires: 2024-03-31T23:59:59Z\n"
                "Policy: {base}/vdp\n"
                "Acknowledgments: {base}/thanks\n"),
            "vdp": (PAGE, _vdp("Humberline Freight", "Email psirt@humberline-freight.test.")),
            "thanks": (PAGE, _hall("Humberline Freight")),
        },
        "score": 5,
        "route": "psirt@humberline-freight.test, but confirm it still works first: the file expired in March 2024.",
        "lesson": "Expired file. RFC 9116 says to treat it as stale. Use it, but check the contact via another route.",
    },
    {
        "slug": "saltmarsh-energy", "name": "Saltmarsh Energy", "sector": "Energy", "color": "#3a5f0b",
        "footer": [("Security", "vdp")],
        "files": {
            ".well-known/security.txt": (PLAIN,
                "Expires: {expires}\n"
                "Policy: {base}/vdp\n"
                "Preferred-Languages: en, da\n"),
            "vdp": (PAGE, _vdp("Saltmarsh Energy", "Use the form on this page or email "
                                                   "security@saltmarsh-energy.test.")),
        },
        "score": 4,
        "route": "security@saltmarsh-energy.test, found via the Policy link (the file itself has no Contact).",
        "lesson": "No Contact field, so the file is invalid. Follow the Policy link to find the real route.",
    },
    {
        "slug": "gullwing-airways", "name": "Gullwing Airways", "sector": "Aviation", "color": "#1f3b8a",
        "footer": [("Disclosure policy", "vdp")],
        "files": {
            "security.txt": (PLAIN,
                "Contact: mailto:cyber@gullwing-airways.test\n"
                "Expires: {expires}\n"
                "Policy: {base}/vdp\n"),
            "vdp": (PAGE, _vdp("Gullwing Airways", "Email cyber@gullwing-airways.test.")),
        },
        "score": 4,
        "route": "cyber@gullwing-airways.test, from the legacy /security.txt location.",
        "lesson": "Nothing at /.well-known/. The file is at the old top-level /security.txt. Check both.",
    },
    {
        "slug": "ferriby-health", "name": "Ferriby Health", "sector": "Healthcare", "color": "#7a1f5c",
        "footer": [("Report a security issue", "vdp")],
        "files": {
            ".well-known/security.txt": (HTML_RAW,
                "Contact: mailto:infosec@ferriby-health.test\n"
                "Expires: {expires}\n"
                "Policy: {base}/vdp\n"
                "Encryption: {base}/pgp-key.txt\n"),
            "pgp-key.txt": (PLAIN, FAKE_KEY),
            "vdp": (PAGE, _vdp("Ferriby Health", "Email infosec@ferriby-health.test. Never include "
                                                 "patient data in your report.")),
        },
        "score": 5,
        "route": "infosec@ferriby-health.test, encrypted with their key.",
        "lesson": "Served as text/html instead of text/plain. Run curl -i and read the Content-Type header.",
    },
    {
        "slug": "quayside-retail", "name": "Quayside Retail", "sector": "Retail", "color": "#b0122b",
        "footer": [("Found a security issue?", "vulnerability-disclosure")],
        "files": {
            "vulnerability-disclosure": (PAGE, _vdp("Quayside Retail", "Email "
                                                    "security-reports@quayside-retail.test.")),
        },
        "score": 0,
        "route": "security-reports@quayside-retail.test, from the 'Found a security issue?' link in the site footer.",
        "lesson": "No security.txt at all, but a disclosure page is linked in the footer. Look around the site.",
    },
    {
        "slug": "spurn-telecom", "name": "Spurn Point Telecom", "sector": "Telecoms", "color": "#5b2a86",
        "footer": [],
        "files": {
            ".well-known/security.txt": (PLAIN,
                "Contact: https://social.example/@spurntelecom\n"
                "Expires: {expires}\n"),
        },
        "score": 4,
        "route": "Send a DM to the social account asking for a private channel. Never post details publicly.",
        "lesson": "A valid file, but the only contact is a social media account. That's the trap: ask for a "
                  "private route.",
    },
    {
        "slug": "wolds-insurance", "name": "Wolds Insurance", "sector": "Insurance", "color": "#0d5c8c",
        "footer": [("Hall of fame", "hall-of-fame")],
        "files": {
            ".well-known/security.txt": (PLAIN,
                "Contact: mailto:security@wolds-insurance.test\n"
                "Expires: {expires}\n"
                "Policy: {base}/security-policy\n"
                "Encryption: {base}/pgp-key.txt\n"
                "Acknowledgments: {base}/hall-of-fame\n"),
            "pgp-key.txt": (PLAIN, FAKE_KEY),
            "hall-of-fame": (PAGE, _hall("Wolds Insurance")),
        },
        "score": 6,
        "route": "security@wolds-insurance.test, but ask about scope and safe harbour before testing anything.",
        "lesson": "The Policy link returns 404: no published scope means no safe harbour. Ask before testing.",
    },
    {
        "slug": "kingston-rail", "name": "Kingston Rail Co", "sector": "Transport", "color": "#333f48",
        "footer": [],
        "files": {},
        "score": 0,
        "route": "No route published. Try security@ the domain, then a national CERT or the NCSC to broker contact.",
        "lesson": "Nothing anywhere. This is where reports go to die, and why national routes exist.",
    },
    {
        "slug": "minster-university", "name": "Minster University", "sector": "Education", "color": "#6b4e16",
        "footer": [("Security disclosure", "vdp"), ("Thanks", "hall-of-fame")],
        "files": {
            ".well-known/security.txt": (PLAIN,
                "Contact: mailto:cert@minster-university.test\n"
                "Expires: 2099-12-31T23:59:59Z\n"
                "Policy: {base}/vdp\n"
                "Acknowledgments: {base}/hall-of-fame\n"
                "Hiring: {base}/jobs\n"),
            "vdp": (PAGE, _vdp("Minster University", "Email cert@minster-university.test.")),
            "hall-of-fame": (PAGE, _hall("Minster University")),
        },
        "score": 6,
        "route": "cert@minster-university.test.",
        "lesson": "Valid, but Expires is in 2099. RFC 9116 recommends less than a year, so check it's maintained.",
    },
]
ORGS_BY_SLUG = {o["slug"]: o for o in ORGS}

RUBRIC = [
    ("File at /.well-known/security.txt, served as text/plain", "2 (only 1 if found elsewhere or wrong type)"),
    ("Has a Contact field", "1"),
    ("Expires is in the future", "1"),
    ("Policy link that works", "1"),
    ("Encryption key", "1"),
    ("Acknowledgments / hall of fame", "1"),
]


def expires_future():
    return (date.today() + timedelta(days=200)).isoformat() + "T23:59:59Z"


def serve_org(slug, path, base):
    org = ORGS_BY_SLUG.get(slug)
    if org is None:
        abort(404)
    path = path.strip("/")
    if path == "":
        return render_template("lab1/org_home.html", org=org, base=base)
    entry = org["files"].get(path)
    if entry is None:
        return render_template("lab1/org_page.html", org=org, base=base,
                               content="<h2>404: page not found</h2>"), 404
    kind, body = entry
    text = body.replace("{base}", base).replace("{expires}", expires_future())
    if kind == PAGE:
        return render_template("lab1/org_page.html", org=org, base=base, content=text)
    return Response(text, content_type=kind)


@orgs_bp.before_app_request
def host_based_orgs():
    """Serve <slug>.localhost as that organisation's own website."""
    host = request.host.split(":")[0].lower()
    if host.endswith(".localhost"):
        slug = host[: -len(".localhost")]
        if slug in ORGS_BY_SLUG:
            return serve_org(slug, request.path, request.host_url.rstrip("/"))
    return None


@orgs_bp.route("/o/<slug>/", defaults={"path": ""})
@orgs_bp.route("/o/<slug>/<path:path>")
def org_site(slug, path):
    return serve_org(slug, path, request.host_url.rstrip("/") + f"/o/{slug}")


def _answers():
    rows = get_db().execute("SELECT slug, score, route FROM lab1_answers").fetchall()
    return {r["slug"]: r for r in rows}


@bp.route("/")
def index():
    return render_template("lab1/index.html", orgs=ORGS, rubric=RUBRIC, answers=_answers(),
                           port=request.host.split(":")[1] if ":" in request.host else "80")


@bp.post("/submit")
def submit():
    db = get_db()
    for org in ORGS:
        raw = request.form.get(f"score_{org['slug']}", "")
        route = (request.form.get(f"route_{org['slug']}") or "").strip()[:300]
        score = int(raw) if raw.isdigit() and 0 <= int(raw) <= 7 else None
        db.execute("INSERT INTO lab1_answers (slug, score, route) VALUES (?, ?, ?) "
                   "ON CONFLICT(slug) DO UPDATE SET score = excluded.score, route = excluded.route",
                   (org["slug"], score, route))
    db.commit()
    return redirect(url_for("lab1.results"))


@bp.route("/results")
def results():
    answers = _answers()
    if not answers:
        return redirect(url_for("lab1.index"))
    correct = sum(1 for o in ORGS if answers.get(o["slug"]) and answers[o["slug"]]["score"] == o["score"])
    return render_template("lab1/results.html", orgs=ORGS, answers=answers, correct=correct)
