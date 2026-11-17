"""Lab 2: triage game. The team plays the security team and sorts 8 incoming reports."""
from flask import Blueprint, redirect, render_template, request, url_for

from .db import get_db

bp = Blueprint("lab2", __name__, url_prefix="/lab2")

BUCKETS = {
    "act": "Act today",
    "info": "Needs more info",
    "close": "Close (noise)",
    "legal": "Escalate to legal",
}

CARDS = [
    {
        "id": "c1", "from": "r.patel@student.example",
        "subject": "IDOR in /api/bookings/{id} exposes other customers' passport numbers",
        "body": "Logged in as my own test account (booking 2210). Changing the id in "
                "GET /api/bookings/2210 to 2211 returns another customer's name and passport number. "
                "Steps, request and redacted response attached. I viewed one record and stopped. "
                "Happy to follow your disclosure timeline.",
        "answer": ["act"],
        "why": "A real, reproducible bug with personal data exposure, minimum access and a perfect tone. "
               "This is the report you want to receive.",
    },
    {
        "id": "c2", "from": "anon-hunter@mail.example",
        "subject": "Critical vulnerability found!!!",
        "body": "I found a critical vulnerability on your website. Reply to this email for the details.",
        "answer": ["info"],
        "why": "Might be real, but there's nothing to triage. Ask for steps and evidence. The reporter has "
               "made themselves the slowest email of the day.",
    },
    {
        "id": "c3", "from": "bountyking@mail.example",
        "subject": "Security issue: missing SPF / DMARC record",
        "body": "Your domain has no DMARC policy, so attackers can spoof your email. This is a serious "
                "issue. Please pay a bounty of $500 to my PayPal.",
        "answer": ["close"],
        "why": "A classic beg bounty: a best-practice finding with an unprompted payment demand. Close it, "
               "politely or not at all.",
    },
    {
        "id": "c4", "from": "scanner-reports@mail.example",
        "subject": "40 vulnerabilities on your site (report attached)",
        "body": "Attached is the full output of my scanner: 40 findings including 'Server header discloses "
                "version', 'Clickjacking possible on /about' and 'TLS 1.2 enabled'.",
        "answer": ["close", "info"],
        "why": "Unverified scanner noise. Close it, or ask them for one manually verified issue with real "
               "impact.",
    },
    {
        "id": "c5", "from": "j.smith@researcher.example",
        "subject": "Admin panel exposed with default credentials",
        "body": "Your /admin panel accepts admin/admin. I logged in, browsed the customer list and "
                "exported a few hundred records to show the impact. Screenshots attached.",
        "answer": ["act", "legal"],
        "why": "Both. The bug is real and urgent (act today), but they went far beyond proving it and "
               "exported personal data (escalate). The line between research and a breach is how much you touched.",
    },
    {
        "id": "c6", "from": "darkside-sec@mail.example",
        "subject": "Pay EUR 5,000 in 72 hours",
        "body": "I have found a serious flaw in your systems. Pay EUR 5,000 within 72 hours or I publish "
                "the details and your data.",
        "answer": ["legal"],
        "why": "A demand plus a threat is extortion, whatever the sender calls it. Straight to legal and "
               "incident response.",
    },
    {
        "id": "c7", "from": "m.okafor@student.example",
        "subject": "Stored XSS in support chat widget",
        "body": "The chat widget on your site (served from chat-widget-vendor.example) is vulnerable to "
                "stored XSS. Full steps and a proof of concept that only pops an alert box are below.",
        "answer": ["info"],
        "why": "A good report, but the widget belongs to a third-party vendor and is out of your scope. "
               "Thank them and redirect them to the vendor, or coordinate with the vendor yourself.",
    },
    {
        "id": "c8", "from": "r.patel@student.example",
        "subject": "Following up: IDOR report from 30 days ago",
        "body": "Hi, I reported an access control issue 30 days ago and haven't had a reply. Could you "
                "confirm you received it? I won't publish anything without agreeing a date with you.",
        "answer": ["act"],
        "why": "Act today: you failed them. A polite chaser after 30 days of silence is how good "
               "researchers end up escalating to a CERT, or going public.",
    },
]


def _answers():
    rows = get_db().execute("SELECT card, bucket, reason FROM lab2_answers").fetchall()
    return {r["card"]: r for r in rows}


@bp.route("/")
def index():
    return render_template("lab2/index.html", cards=CARDS, buckets=BUCKETS, answers=_answers())


@bp.post("/submit")
def submit():
    db = get_db()
    for card in CARDS:
        bucket = request.form.get(f"bucket_{card['id']}")
        if bucket not in BUCKETS:
            bucket = None
        reason = (request.form.get(f"reason_{card['id']}") or "").strip()[:500]
        db.execute("INSERT INTO lab2_answers (card, bucket, reason) VALUES (?, ?, ?) "
                   "ON CONFLICT(card) DO UPDATE SET bucket = excluded.bucket, reason = excluded.reason",
                   (card["id"], bucket, reason))
    db.commit()
    return redirect(url_for("lab2.results"))


@bp.route("/results")
def results():
    answers = _answers()
    if not answers:
        return redirect(url_for("lab2.index"))
    correct = sum(1 for c in CARDS if answers.get(c["id"]) and answers[c["id"]]["bucket"] in c["answer"])
    return render_template("lab2/results.html", cards=CARDS, buckets=BUCKETS, answers=answers,
                           correct=correct)
