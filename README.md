# You Found a Bug. Now What? · Labs

Three offline, hands-on labs for the Hull University lecture on responsible disclosure. All three run in one
Docker container on each team's own machine. Nothing leaves the machine, and every organisation, person and
record in it is fictional.

| Lab | Time | What students do |
|---|---|---|
| 1 · security.txt hunt | 10 min, pairs | Fetch and score the security.txt of 10 fictional organisations, each built to teach one RFC 9116 lesson |
| 2 · Triage game | 10 min, groups of 4 | Play the security team: sort 8 incoming reports into Act today / Needs more info / Close / Escalate to legal |
| 3 · Find it, then report it | 15 min, pairs | Find an IDOR in the fictional HullFerries booking site, prove it with minimum access, write a seven-part report |

## Students: start the labs

The image is local: there's no registry. Get it onto the machine one of two ways, then run it.

```
# Either: load it from the USB stick (no internet needed). Use the arm64 file on Apple Silicon.
docker load -i hull-disclosure-labs-amd64.tar

# Or: build it from the repo (needs internet once, to fetch the Python base image)
git clone https://github.com/jdsmithit/hull-lab-2026.git && cd hull-lab-2026
docker build -t hull-disclosure-labs .

# Then run it
docker run --rm -p 127.0.0.1:8080:8080 hull-disclosure-labs
```

Then open <http://localhost:8080>.

- `127.0.0.1:` keeps the deliberately vulnerable app reachable from your own machine only, not from
  classmates on the same network. Don't drop it.
- `--rm` removes the container when you stop it (Ctrl+C). Your answers go with it. Leave it running for the session.
- Podman works too: replace `docker` with `podman`.

## Facilitator

- **Share the repo link only after the labs.** The source contains the answer keys and the Lab 3 proof token.
  The deck shows the link on the final 30-day challenge slide, so students can take the labs home.

- **Facilitator page:** <http://localhost:8080/facilitator> on any team's machine. It has the answer keys for Labs 1 and 2,
  the Lab 3 proof token, the team's progress and a reset button. The PIN is set at build time (see below);
  the default is `hull2026`.
- **Lab 3 SOC moment:** after Lab 3, ask every pair to open **Lab 3 → SOC view** and shout out how many other
  customers' records they viewed. One was enough to prove the bug, and the verdict (Researcher / Getting greedy /
  Incident) does the rest.
- **Lab 3 reports:** teams download their report as Markdown (`hullferries-report.md`) and email it to
  John.smith@dfds.com with their team name in the subject. The report page says this too.
- **Lab 3 hint at minute 4:** open DevTools → Network and reload *My bookings*. It's also on the brief page.
- **The container is out of scope.** Students could dig the answers out of the image. The rules page says so
  and explains why. Treat anyone who does it as a live Part 4 example.

### Before the day: check with the university

- [ ] Docker (or Podman) installed on the lab machines, and students allowed to run it
- [ ] Load the image from the USB tarballs (building on site needs internet to fetch the Python base image)
- [ ] Machine architecture: Intel/AMD (`amd64`) or ARM (`arm64`)
- [ ] Port 8080 free. If not, use `-p 127.0.0.1:9090:8080` and open `localhost:9090`
- [ ] Run a full pass on one actual lab machine: all three labs, the report download and the SOC view

### Fallback if Docker isn't available

Students can run the app directly with Python 3.11 or newer:

```
pip install -r requirements.txt
gunicorn --bind 127.0.0.1:8080 --workers 1 --threads 8 "app:create_app()"
```

If that's not possible either, use PortSwigger's free *Insecure direct object references* lab for Lab 3 and
the printed Lab 2 cards.

## Build the image and the USB tarballs

```
# Local build
docker build --build-arg FACILITATOR_PIN=<your-pin> -t hull-disclosure-labs .

# Tarballs for the USB stick, one per architecture, in dist/
FACILITATOR_PIN=<your-pin> ./scripts/build.sh
```

Each tarball loads as `hull-disclosure-labs`, so students run the same command whichever way they got the image.

## Develop and test

```
pip install -r requirements.txt pytest
python -m pytest -q
flask --app app:create_app run --port 8080 --debug
```

## How it's built

- One Flask app (`app/`), served by gunicorn on port 8080. SQLite file at `/data/labs.db` inside the container.
- Runs as a non-root user. No external calls, CDNs or web fonts.
- Lab 1 organisations are served path-based (`/o/<slug>/…`) and host-based (`<slug>.localhost:8080`).
  Browsers and current curl versions resolve `*.localhost` to your own machine; if one doesn't, use the
  path-based URLs.
- Lab 3's bug is deliberate: `GET /hullferries/api/bookings/<id>` checks you're logged in, but not that the
  booking is yours.

| Path | What |
|---|---|
| `app/lab1.py` | The 10 organisations, their files and the scoring key |
| `app/lab2.py` | The 8 report cards and answers |
| `app/lab3.py` | HullFerries, the SOC view and the report form |
| `app/facilitator.py` | PIN-protected answer keys and reset |
| `tests/test_labs.py` | Tests for every lab |
