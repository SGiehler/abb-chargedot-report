FROM python:3.11-slim

WORKDIR /app

# Systemabhängigkeiten für Reportlab installieren (falls nötig, aber pure Python/Reportlab braucht meist keine extra Libs auf Debian)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Kopieren der Projekt-Konfiguration
COPY pyproject.toml README.md ./

# Pip-Abhängigkeiten installieren
RUN pip install --no-cache-dir .

# App-Quellcode kopieren
COPY . .

# Reports Ordner und Downloads-Temp erstellen
RUN mkdir -p reports

# Expose Port 8000
EXPOSE 8000

# Startbefehl für den Web-Modus
ENTRYPOINT ["python", "main.py"]
CMD ["web"]
