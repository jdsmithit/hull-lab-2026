import re

import pytest

from app import create_app
from app import lab1, lab2, lab3


@pytest.fixture()
def client(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "t.db"), "FACILITATOR_PIN": "1234"})
    return app.test_client()


def test_portal_and_team(client):
    assert client.get("/healthz").json == {"status": "ok"}
    client.post("/team", data={"name": "Team Kraken"})
    assert b"Team Kraken" in client.get("/").data
    assert client.get("/rules").status_code == 200


# ---------------------------------------------------------------- Lab 1

def test_lab1_files_match_their_lessons(client):
    r = client.get("/o/brightwater-bank/.well-known/security.txt")
    assert r.status_code == 200 and r.content_type.startswith("text/plain")
    assert b"Contact: mailto:security@brightwater-bank.test" in r.data
    assert b"http://localhost/o/brightwater-bank/vdp" in r.data            # {base} substituted
    assert re.search(rb"Expires: 20\d\d-\d\d-\d\dT", r.data)

    assert b"2024-03-31" in client.get("/o/humberline-freight/.well-known/security.txt").data
    assert b"Contact:" not in client.get("/o/saltmarsh-energy/.well-known/security.txt").data
    assert client.get("/o/gullwing-airways/.well-known/security.txt").status_code == 404
    assert client.get("/o/gullwing-airways/security.txt").status_code == 200
    assert client.get("/o/ferriby-health/.well-known/security.txt").content_type.startswith("text/html")
    assert client.get("/o/quayside-retail/.well-known/security.txt").status_code == 404
    assert b"vulnerability-disclosure" in client.get("/o/quayside-retail/").data
    assert b"social.example" in client.get("/o/spurn-telecom/.well-known/security.txt").data
    assert client.get("/o/wolds-insurance/security-policy").status_code == 404
    assert client.get("/o/kingston-rail/.well-known/security.txt").status_code == 404
    assert b"2099" in client.get("/o/minster-university/.well-known/security.txt").data


def test_lab1_host_based_routing(client):
    r = client.get("/.well-known/security.txt", headers={"Host": "brightwater-bank.localhost:8080"})
    assert r.status_code == 200
    assert b"http://brightwater-bank.localhost:8080/vdp" in r.data
    # Unknown subdomains fall through to the normal app
    assert client.get("/healthz", headers={"Host": "nope.localhost:8080"}).status_code == 200


def test_lab1_scoring(client):
    assert client.get("/lab1/results").status_code == 302                  # nothing submitted yet
    form = {f"score_{o['slug']}": str(o["score"]) for o in lab1.ORGS}
    form["score_kingston-rail"] = "3"                                       # one wrong
    form["route_kingston-rail"] = "<script>alert(1)</script>"
    r = client.post("/lab1/submit", data=form, follow_redirects=True)
    assert b"9 of 10" in r.data
    assert b"<script>alert(1)</script>" not in r.data                       # escaped


# ---------------------------------------------------------------- Lab 2

def test_lab2_scoring(client):
    form = {f"bucket_{c['id']}": c["answer"][0] for c in lab2.CARDS}
    form["bucket_c6"] = "close"                                             # extortion is not noise
    form["bucket_c1"] = "bogus"                                             # invalid bucket ignored
    r = client.post("/lab2/submit", data=form, follow_redirects=True)
    assert b"6 of 8" in r.data


# ---------------------------------------------------------------- Lab 3

def login(client):
    return client.post("/hullferries/login",
                       data={"email": lab3.STUDENT_EMAIL, "password": lab3.STUDENT_PASSWORD})


def test_lab3_requires_login(client):
    assert client.get("/hullferries/api/bookings/1041").status_code == 401
    assert client.get("/hullferries/my-bookings").status_code == 302
    bad = client.post("/hullferries/login", data={"email": lab3.STUDENT_EMAIL, "password": "x"})
    assert b"Wrong email or password" in bad.data


def test_lab3_idor_and_proof(client):
    login(client)
    own = client.get("/hullferries/api/bookings/1041").json
    assert own["passenger"] == "Hull Student" and "lab_proof" not in own
    other = client.get("/hullferries/api/bookings/1042").json
    assert other["lab_proof"] == lab3.PROOF and other["passport_number"].startswith("TEST")
    assert client.get("/hullferries/api/bookings/9999").status_code == 404


def test_lab3_soc_verdicts(client):
    login(client)
    client.get("/hullferries/api/bookings/1041")
    assert lab3_verdict(client) == "Not found yet"
    client.get("/hullferries/api/bookings/1042")
    client.get("/hullferries/api/bookings/1042")                            # repeat doesn't count twice
    assert lab3_verdict(client) == "Researcher"
    for bid in range(1043, 1060):
        client.get(f"/hullferries/api/bookings/{bid}")
    assert lab3_verdict(client) == "Incident"


def lab3_verdict(client):
    html = client.get("/lab3/soc").data.decode()
    return re.search(r'class="verdict">([^<]+)<', html).group(1)


def test_lab3_report_roundtrip(client):
    client.post("/team", data={"name": "Pair 3"})
    form = {k: f"{k} text" for k, _l, _h in lab3.REPORT_FIELDS}
    form["title"] = "IDOR in /hullferries/api/bookings/{id} exposes passport numbers"
    r = client.post("/lab3/report", data=form, follow_redirects=True)
    assert b"Download as Markdown" in r.data
    md = client.get("/lab3/report.md")
    assert md.headers["Content-Disposition"].endswith("hullferries-report.md")
    body = md.data.decode()
    assert body.startswith("# IDOR in /hullferries/api/bookings/{id}")
    assert "Reported by: Pair 3" in body and "## Steps to reproduce" in body


def test_hullferries_security_txt_and_vdp(client):
    r = client.get("/hullferries/.well-known/security.txt")
    assert r.content_type.startswith("text/plain") and b"Policy:" in r.data
    assert b"Safe harbour" in client.get("/hullferries/vdp").data


# ---------------------------------------------------------------- Facilitator

def test_facilitator_pin_and_reset(client):
    assert b"PIN" in client.get("/facilitator/").data
    assert b"Wrong PIN" in client.post("/facilitator/", data={"pin": "0000"}).data
    client.post("/team", data={"name": "Gone soon"})
    r = client.post("/facilitator/", data={"pin": "1234"}, follow_redirects=True)
    assert lab3.PROOF.encode() in r.data and b"Lab 1 answer key" in r.data
    client.post("/facilitator/reset")
    assert b"Gone soon" not in client.get("/").data


def test_reset_requires_pin(client):
    client.post("/team", data={"name": "Still here"})
    client.post("/facilitator/reset")
    assert b"Still here" in client.get("/").data
