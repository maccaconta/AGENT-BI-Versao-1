FROM python:3.11-slim

# ─── System deps ───────────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ─── Work dir ──────────────────────────────────────────────────────────────────
WORKDIR /app

# ─── Python dependencies ───────────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ─── App source ────────────────────────────────────────────────────────────────
COPY . .

# ─── Static files ──────────────────────────────────────────────────────────────
RUN python manage.py collectstatic --noinput --settings=config.settings.production || true

# ─── Non-root user ─────────────────────────────────────────────────────────────
RUN adduser --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "4", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
