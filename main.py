import os
import sys
import argparse
import tempfile
import zipfile
import json
from pathlib import Path
import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from config import Config
from pdf_generator import PDFReportGenerator

# FastAPI App initialisieren
app = FastAPI(
    title="ABB/Chargedot Ladeabrechnung",
    description="Erstellt PDF-Reports aus Ladesessions-CSV"
)

# ----------------- FastAPI Web Routen -----------------

@app.get("/", response_class=HTMLResponse)
async def read_index():
    index_path = Path("templates/index.html")
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Index-Template nicht gefunden.")
    return HTMLResponse(content=index_path.read_text(encoding="utf-8"))


@app.get("/config")
async def get_config():
    """Gibt die Default-Konfiguration für die Web-UI zurück."""
    return JSONResponse(content=Config.to_dict())


@app.post("/upload")
async def upload_csv(file: UploadFile = File(...)):
    """Nimmt eine CSV-Datei entgegen und analysiert die enthaltenen Monate."""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Ungültiges Dateiformat. Bitte lade eine CSV-Datei hoch.")
    
    # Datei temporär speichern zum Einlesen
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
        try:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Fehler beim Speichern der temporären Datei: {e}")
            
    try:
        # Generator instanziieren, um Monate zu parsen (Dummy-Werte für Stammdaten reichen aus)
        generator = PDFReportGenerator(tmp_path, 0.2755, "Temp")
        months = generator.get_available_months()
        return JSONResponse(content={"months": months})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        # Temporäre Datei löschen
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@app.post("/generate")
async def generate_reports(
    file: UploadFile = File(...),
    signature_file: UploadFile = File(None),  # Optionales Unterschriftenbild
    employee_name: str = Form(...),
    license_plate: str = Form(""),
    price_per_kwh: float = Form(0.2755),
    enable_supervisor: bool = Form(False),  # Option für Vorgesetzten
    months: str = Form(...)  # JSON-kodiertes Array von Monaten, z.B. '["2026-06","2026-07"]'
):
    """Generiert PDF-Reports für die ausgewählten Monate."""
    try:
        selected_months = json.loads(months)
    except Exception:
        raise HTTPException(status_code=400, detail="Ungültiges Format für die Monatsauswahl.")

    if not selected_months:
        raise HTTPException(status_code=400, detail="Es muss mindestens ein Monat ausgewählt werden.")

    # CSV temporär speichern
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    # Unterschriftenbild temporär speichern falls vorhanden
    sig_image_path = None
    if signature_file and signature_file.filename:
        suffix = Path(signature_file.filename).suffix
        if suffix.lower() in ('.png', '.jpg', '.jpeg'):
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_sig:
                content = await signature_file.read()
                tmp_sig.write(content)
                sig_image_path = tmp_sig.name

    # Temporäres Verzeichnis für die PDF-Erstellung erstellen
    temp_dir = tempfile.TemporaryDirectory()
    temp_dir_path = Path(temp_dir.name)

    try:
        # Generator initialisieren
        generator = PDFReportGenerator(
            csv_path=tmp_path,
            price_per_kwh=price_per_kwh,
            employee_name=employee_name,
            license_plate=license_plate,
            enable_supervisor_sig=enable_supervisor,
            signature_image_path=sig_image_path
        )

        generated_files = []
        for m in selected_months:
            pdf_file = generator.generate_monthly_report(m, temp_dir_path)
            generated_files.append(pdf_file)

        # Aufräumen der temporären CSV-Datei
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        # Aufräumen des temporären Unterschriftenbildes
        if sig_image_path and os.path.exists(sig_image_path):
            os.remove(sig_image_path)

        local_output_dir = Config.OUTPUT_DIR
        local_output_dir.mkdir(parents=True, exist_ok=True)

        if len(generated_files) == 1:
            # Nur ein PDF erzeugt -> direkt zurückgeben
            target_pdf = generated_files[0]
            local_pdf_path = local_output_dir / target_pdf.name
            local_pdf_path.write_bytes(target_pdf.read_bytes())
            
            # Temporäres Verzeichnis manuell bereinigen, da wir das PDF kopiert haben
            temp_dir.cleanup()

            return FileResponse(
                path=str(local_pdf_path),
                filename=local_pdf_path.name,
                media_type="application/pdf"
            )
        else:
            # Mehrere PDFs erzeugt -> als ZIP-Archiv packen
            zip_filename = "Ladeberichte.zip"
            local_zip_path = local_output_dir / zip_filename

            with zipfile.ZipFile(local_zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for pdf_file in generated_files:
                    # In ZIP packen
                    zip_file.write(pdf_file, arcname=pdf_file.name)
                    # Lokal sichern
                    local_pdf_path = local_output_dir / pdf_file.name
                    local_pdf_path.write_bytes(pdf_file.read_bytes())

            # Temporäres Verzeichnis manuell bereinigen, da wir das ZIP kopiert/erstellt haben
            temp_dir.cleanup()

            return FileResponse(
                path=str(local_zip_path),
                filename=zip_filename,
                media_type="application/zip"
            )

    except Exception as e:
        # Falls Fehler auftreten, temporäre Dateien löschen
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        if 'sig_image_path' in locals() and sig_image_path and os.path.exists(sig_image_path):
            os.remove(sig_image_path)
        raise HTTPException(status_code=500, detail=str(e))


# ----------------- CLI Ausführung -----------------

def run_cli(args):
    """Führt die Report-Generierung auf der Kommandozeile aus."""
    print("--- ABB / Chargedot Ladekosten Report-Generator ---")
    
    csv_path = Path(args.csv)
    if not csv_path.exists():
        # Versuche die neueste CSV im aktuellen Verzeichnis zu finden, falls nicht explizit angegeben
        if args.csv == "latest":
            csv_files = list(Path('.').glob('*.csv'))
            if not csv_files:
                print("Fehler: Keine CSV-Datei im aktuellen Verzeichnis gefunden.")
                sys.exit(1)
            # Sortiere nach Änderungsdatum, neueste zuerst
            csv_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            csv_path = csv_files[0]
            print(f"Verwende neueste gefundene Datei: {csv_path.name}")
        else:
            print(f"Fehler: Datei '{args.csv}' existiert nicht.")
            sys.exit(1)

    employee = args.employee or Config.EMPLOYEE_NAME
    license_plate = args.license_plate or Config.LICENSE_PLATE
    price = args.price if args.price is not None else Config.PRICE_PER_KWH
    output_dir = Path(args.output_dir or Config.OUTPUT_DIR)

    print(f"Fahrer: {employee}")
    if license_plate:
        print(f"Kennzeichen: {license_plate}")
    print(f"Strompreis: {price:.4f} €/kWh")
    print(f"Ausgabe-Ordner: {output_dir.resolve()}")
    print("-" * 50)

    try:
        enable_supervisor = args.enable_supervisor or Config.ENABLE_SUPERVISOR_SIGNATURE
        generator = PDFReportGenerator(
            csv_path=csv_path,
            price_per_kwh=price,
            employee_name=employee,
            license_plate=license_plate,
            enable_supervisor_sig=enable_supervisor,
            signature_image_path=args.signature_image
        )

        available_months = generator.get_available_months()
        if not available_months:
            print("Fehler: Keine abrechenbaren Monate in der CSV gefunden.")
            sys.exit(1)

        # Zu verarbeitende Monate bestimmen
        target_months = []
        if args.month:
            if args.month in available_months:
                target_months = [args.month]
            else:
                print(f"Fehler: Der Monat '{args.month}' ist in den CSV-Daten nicht enthalten.")
                print(f"Verfügbare Monate: {', '.join(available_months)}")
                sys.exit(1)
        else:
            target_months = available_months

        print(f"Generiere Reports für folgende Monate: {', '.join(target_months)}")
        
        for month in target_months:
            pdf_path = generator.generate_monthly_report(month, output_dir)
            print(f" [OK] Bericht generiert: {pdf_path.name}")

        print("Abrechnung erfolgreich abgeschlossen!")

    except Exception as e:
        print(f"Fehler bei der Generierung: {e}")
        sys.exit(1)


# ----------------- Haupteinstiegspunkt -----------------

def main():
    parser = argparse.ArgumentParser(description="ABB / Chargedot Ladekosten Report-Generator")
    subparsers = parser.add_subparsers(dest="mode", help="Ausführungsmodus (cli oder web)")

    # CLI Parser
    cli_parser = subparsers.add_parser("cli", help="Startet die Report-Erstellung im Terminal")
    cli_parser.add_argument("--csv", default="latest", help="Pfad zur CSV-Datei (Standard: neueste im Ordner)")
    cli_parser.add_argument("--month", help="Spezifischer Monat im Format YYYY-MM (Standard: alle Monate)")
    cli_parser.add_argument("--price", type=float, help="Strompreis in €/kWh (Standard: 0.2755)")
    cli_parser.add_argument("--employee", help="Name des Fahrers (Standard: aus config)")
    cli_parser.add_argument("--license-plate", help="Fahrzeug-Kennzeichen (Standard: aus config)")
    cli_parser.add_argument("--output-dir", help="Speicherort für die PDFs (Standard: reports)")
    cli_parser.add_argument("--signature-image", help="Pfad zu einem Bild der Unterschrift (z.B. PNG)")
    cli_parser.add_argument("--enable-supervisor", action="store_true", help="Unterschrift des Vorgesetzten anzeigen (Standard: deaktiviert)")

    # Web Parser
    web_parser = subparsers.add_parser("web", help="Startet die Web-UI (FastAPI)")
    web_parser.add_argument("--host", default="0.0.0.0", help="Host-IP des Webservers")
    web_parser.add_argument("--port", type=int, default=8000, help="Port des Webservers")

    # Standard-Verhalten: Zeige Hilfe, wenn kein Argument übergeben wird
    if len(sys.argv) == 1:
        # Falls keine Argumente, starten wir standardmäßig den Webserver
        print("Kein Modus angegeben, starte standardmäßig den Webserver...")
        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
        return

    args = parser.parse_args()

    if args.mode == "cli":
        run_cli(args)
    elif args.mode == "web":
        print(f"Starte Web-UI auf http://{args.host}:{args.port} ...")
        # reload=True nur aktivieren, wenn wir uns im Entwicklungsmodus befinden
        uvicorn.run("main:app", host=args.host, port=args.port, reload=False)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
