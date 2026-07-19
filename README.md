# ABB / Chargedot Ladekosten Report-Generator

Dieses Tool verarbeitet den kumulativen CSV-Export aus dem ABB/Chargedot-Portal, filtert die Ladevorgänge nach Kalendermonaten und erstellt übersichtliche PDF-Berichte für die Erstattung der Ladekosten (kWh * Strompreis).

Es unterstützt sowohl eine **Web-UI (FastAPI)** zur einfachen Bedienung im Browser als auch einen **CLI-Modus** zur Automatisierung auf der Kommandozeile. Zudem ist die Anwendung komplett **dockerisiert**.

## Features

- **Automatisches CSV-Parsing**: Verarbeitet kumulative Ladeberichte mit flexiblem Datumsformat.
- **Präzise Berechnung**: Multipliziert geladene Energie (kWh) mit deinem Strompreis (standardmäßig 27,55 ct/kWh).
- **Professioneller PDF-Nachweis**: Generiert ansprechende PDFs mit detaillierter Tabelle, Gesamtsumme der kWh und des Erstattungsbetrags sowie einem Unterschriftsfeld.
- **Web-UI**: Moderner Dark Mode mit Glassmorphism-Effekt zum Hochladen von CSV-Dateien und Konfigurieren der Parameter.
- **CLI**: Voller Kommandozeilensupport.
- **Docker-Support**: Einfaches Deployment mittels Docker & Docker Compose.

---

## Installation & Ausführung

Das Projekt verwendet den schnellen Python-Paketmanager `uv`.

### 1. Lokal ausführen (CLI & Web)

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
   uv run python main.py cli --csv public_charging_sessions.csv --price 0.2755
   ```

### 2. Mit Docker ausführen

1. **Starten via Docker Compose**:
   ```bash
   docker-compose up --build
   ```
   Öffne danach [http://localhost:8000](http://localhost:8000).

---

## Konfiguration (Umgebungsvariablen)

Folgende Umgebungsvariablen können in einer `.env`-Datei oder im Betriebssystem hinterlegt werden, um Standardwerte für die Web-UI vorzubelegen:

| Variable | Beschreibung | Standardwert |
| :--- | :--- | :--- |
| `DEFAULT_EMPLOYEE_NAME` | Name des Fahrers | `Dein Name` |
| `DEFAULT_LICENSE_PLATE` | Kennzeichen des Fahrzeugs | (leer) |
| `DEFAULT_PRICE_PER_KWH` | Strompreis pro kWh in € | `0.2755` |
| `OUTPUT_DIR` | Speicherort für generierte PDFs | `reports` |

---

## CSV-Format

Das Tool ist auf den Export des ABB/Chargedot-Portals ausgelegt. Folgende Spalten müssen in der CSV-Datei enthalten sein:
- `Start Time` (Format: `DD/MM/YYYY HH:MM` oder `YYYY-MM-DD HH:MM`)
- `Charger Alias` (Name der Ladestation)
- `Energy Delivered(kW·h)` (Fließkommazahl der geladenen Energie)
