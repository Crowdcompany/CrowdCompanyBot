# Crowdbot - Telegram Bot mit Memory 2.0
# Multi-stage build für kleinere Image-Größe

FROM python:3.11-slim as builder

# Build-Abhängigkeiten
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python Dependencies installieren
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production Image
FROM python:3.11-slim

# Metadata
LABEL maintainer="raimund.bauer@crowdcompany-ug.com"
LABEL description="Crowdbot - Self-hosted Telegram AI Assistant with Memory 2.0"
LABEL version="1.1.0"

# Non-root User erstellen
RUN useradd -m -u 1000 -s /bin/bash botuser

# Python Dependencies von builder kopieren
COPY --from=builder /root/.local /home/botuser/.local

# App-Code kopieren
WORKDIR /app
COPY --chown=botuser:botuser . .

# Data-Verzeichnis erstellen (wird als Volume gemountet)
RUN mkdir -p /app/data && chown botuser:botuser /app/data

# Environment
ENV PATH=/home/botuser/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV DATA_DIR=/app/data

# User wechseln
USER botuser

# Health Check (prüft ob Bot-Prozess läuft)
HEALTHCHECK --interval=60s --timeout=10s --start-period=10s --retries=3 \
    CMD pgrep -f "python.*src.bot" || exit 1

# Volume für persistente Daten
VOLUME ["/app/data"]

# Bot starten
CMD ["python3", "-m", "src.bot"]
