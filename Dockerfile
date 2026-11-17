# Hull disclosure labs: three offline labs in one container.
# Run:  docker run --rm -p 127.0.0.1:8080:8080 hull-disclosure-labs
FROM python:3.12-slim

# Set your own PIN at build time: docker build --build-arg FACILITATOR_PIN=xxxx .
ARG FACILITATOR_PIN=hull2026

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LAB_DB=/data/labs.db \
    FACILITATOR_PIN=${FACILITATOR_PIN}

RUN useradd --system --uid 10001 --no-create-home lab \
 && mkdir /data && chown lab /data

WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app

USER lab
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz')"

# One worker so the per-start session key is shared; threads handle a pair of students easily.
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "8", "--access-logfile", "-", "app:create_app()"]
