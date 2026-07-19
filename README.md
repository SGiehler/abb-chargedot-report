# ABB / Chargedot Ladekosten Report-Generator

Dieses Tool verarbeitet den kumulativen CSV-Export aus dem ABB/Chargedot-Portal, filtert die Ladevorgänge nach Kalendermonaten und erstellt übersichtliche PDF-Berichte für die Erstattung der Ladekosten (kWh * Strompreis).

Es unterstützt sowohl eine **Web-UI (FastAPI)** zur einfachen Bedienung im Browser als auch einen **CLI-Modus** zur Automatisierung auf der Kommandozeile. Zudem ist die Anwendung komplett **dockerisiert** und wird automatisch im GitHub Container Registry (GHCR) bereitgestellt.

## Features

- **Automatisches CSV-Parsing**: Verarbeitet kumulative Ladeberichte mit flexiblem Datumsformat.
- **Berechnung mit Ladedauer**: Multipliziert geladene Energie (kWh) mit deinem Strompreis (standardmäßig 27,55 ct/kWh) und weist die Ladedauer für jede Session aus.
- **Digitale Unterschrift**: Lade ein Bild deiner Unterschrift (PNG/JPG) in der Web-UI hoch, um das PDF automatisch zu unterschreiben. Das aktuelle Erstellungsdatum wird automatisch vorausgefüllt.
- **Vorgesetzten-Option**: Optionales Unterschriftsfeld für Vorgesetzte, konfigurierbar in der Web-UI, via CLI-Flag oder Umgebungsvariable.
- **Professioneller PDF-Nachweis**: Generiert ansprechende PDFs mit detaillierter Tabelle, Gesamtsumme der kWh, Gesamtdauer, Erstattungsbetrag sowie Unterschriftenfeldern.
- **Web-UI**: Moderner Dark Mode mit Glassmorphism-Effekt zum Hochladen von CSV-Dateien und Konfigurieren der Parameter.
- **CLI**: Voller Kommandozeilensupport.
- **Docker-Support**: Einfaches Deployment mittels Docker & Docker Compose.

---

## Installation & Ausführung

### 1. Ausführen mit Docker (Empfohlen)

Das Docker-Image wird bei jedem Release und Push auf `main` in der GitHub Container Registry (GHCR) veröffentlicht.

#### A. Direkt mit Docker:
```bash
docker run -d \
  -p 8000:8000 \
  -v ./reports:/app/reports \
  -e DEFAULT_EMPLOYEE_NAME="Stefan Giehler" \
  -e DEFAULT_PRICE_PER_KWH=0.2755 \
  ghcr.io/sgiehler/abb-chargedot-report:latest
```

#### B. Mit Docker Compose (lokaler Build):
Nutze die beigefügte `docker-compose.yml`:
```bash
docker-compose up --build
```
Öffne danach [http://localhost:8000](http://localhost:8000).

---

### 2. Lokal ausführen (ohne Docker)

**Voraussetzungen**: Python 3.10+ und `uv` installiert.

1. **Abhängigkeiten installieren**:
   ```bash
   uv pip install -e .
   ```

2. **Web-UI starten**:
   ```bash
   uv run python main.py web
   ```
   Öffne danach [http://localhost:8000](http://localhost:8000) im Browser.

3. **CLI ausführen**:
   ```bash
   # Generiert Berichte für alle Monate
   uv run python main.py cli --csv public_charging_sessions.csv --price 0.2755
   
   # Mit optionaler Unterschrift und Vorgesetztenfeld
   uv run python main.py cli --csv public_charging_sessions.csv --price 0.2755 --signature-image path/to/sig.png --enable-supervisor
   ```

---

## Konfiguration (Umgebungsvariablen)

Folgende Umgebungsvariablen können in einer `.env`-Datei oder im Betriebssystem hinterlegt werden, um Standardwerte für die Web-UI vorzubelegen:

| Variable | Beschreibung | Standardwert |
| :--- | :--- | :--- |
| `DEFAULT_EMPLOYEE_NAME` | Name des Fahrers | `Dein Name` |
| `DEFAULT_LICENSE_PLATE` | Kennzeichen des Fahrzeugs | (leer) |
| `DEFAULT_PRICE_PER_KWH` | Strompreis pro kWh in € | `0.2755` |
| `ENABLE_SUPERVISOR_SIGNATURE` | Unterschriftsfeld für Vorgesetzten standardmäßig einblenden | `false` |
| `OUTPUT_DIR` | Speicherort für generierte PDFs | `reports` |

---

## CSV-Format

Das Tool ist auf den Export des ABB/Chargedot-Portals ausgelegt. Folgende Spalten müssen in der CSV-Datei enthalten sein:
- `Start Time` (Format: `DD/MM/YYYY HH:MM` oder `YYYY-MM-DD HH:MM`)
- `Charger Alias` (Name der Ladestation)
- `Duration(h)` (Ladedauer in Stunden)
- `Energy Delivered(kW·h)` (Geladene Energie)
