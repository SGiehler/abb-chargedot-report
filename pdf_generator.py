import os
from pathlib import Path
import pandas as pd
from datetime import datetime

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm

class PDFReportGenerator:
    def __init__(self, csv_path: str, price_per_kwh: float, employee_name: str, license_plate: str = "", enable_supervisor_sig: bool = False, signature_image_path: str = None):
        self.csv_path = Path(csv_path)
        self.price_per_kwh = price_per_kwh
        self.employee_name = employee_name
        self.license_plate = license_plate
        self.enable_supervisor_sig = enable_supervisor_sig
        self.signature_image_path = signature_image_path
        self.df = None
        self._load_data()

    def _load_data(self):
        """Lädt und bereinigt die CSV-Datei."""
        if not self.csv_path.exists():
            raise FileNotFoundError(f"CSV-Datei nicht gefunden: {self.csv_path}")
        
        # CSV einlesen
        try:
            self.df = pd.read_csv(self.csv_path)
        except Exception as e:
            raise ValueError(f"Fehler beim Einlesen der CSV-Datei: {e}")
        
        # Spaltennamen bereinigen (Leerzeichen entfernen)
        self.df.columns = [col.strip() for col in self.df.columns]
        
        # Prüfen, ob benötigte Spalten vorhanden sind
        required_cols = ['Start Time', 'Energy Delivered(kW·h)', 'Charger Alias']
        for col in required_cols:
            if col not in self.df.columns:
                # Manchmal weichen die Spalten leicht ab, versuchen wir eine fuzzy Suche
                matched_col = None
                for c in self.df.columns:
                    if col.lower() in c.lower() or c.lower() in col.lower():
                        matched_col = c
                        break
                if matched_col:
                    self.df.rename(columns={matched_col: col}, inplace=True)
                else:
                    raise KeyError(f"Erforderliche Spalte '{col}' fehlt in der CSV-Datei. Vorhanden: {list(self.df.columns)}")

        # Startzeit in DateTime konvertieren
        # Das Format in der CSV war "19/07/2026 13:23"
        self.df['Parsed Start Time'] = pd.to_datetime(
            self.df['Start Time'], 
            dayfirst=True, 
            errors='coerce'
        )
        
        # Zeilen löschen, bei denen die Startzeit nicht geparst werden konnte
        self.df = self.df.dropna(subset=['Parsed Start Time'])
        
        # Geladene Energie bereinigen und in Float umwandeln
        self.df['Energy Delivered(kW·h)'] = pd.to_numeric(
            self.df['Energy Delivered(kW·h)'], 
            errors='coerce'
        ).fillna(0.0)

        # Dauer einlesen und in Float umwandeln
        if 'Duration(h)' not in self.df.columns:
            matched_duration_col = None
            for c in self.df.columns:
                if 'duration' in c.lower():
                    matched_duration_col = c
                    break
            if matched_duration_col:
                self.df.rename(columns={matched_duration_col: 'Duration(h)'}, inplace=True)
            else:
                self.df['Duration(h)'] = 0.0

        self.df['Duration(h)'] = pd.to_numeric(
            self.df['Duration(h)'], 
            errors='coerce'
        ).fillna(0.0)
        
        # Spalten für Berechnungen hinzufügen
        self.df['Calculated Cost'] = self.df['Energy Delivered(kW·h)'] * self.price_per_kwh
        self.df['YearMonth'] = self.df['Parsed Start Time'].dt.strftime('%Y-%m')

    def get_available_months(self):
        """Gibt eine Liste aller in der CSV-Datei gefundenen Monate (YYYY-MM) zurück."""
        if self.df is None or self.df.empty:
            return []
        # Sortiert absteigend (neueste Monate zuerst)
        return sorted(self.df['YearMonth'].unique(), reverse=True)

    def generate_monthly_report(self, month: str, output_dir: Path) -> Path:
        """Generiert ein PDF für einen bestimmten Monat (Format: YYYY-MM)."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Daten für den Monat filtern
        month_data = self.df[self.df['YearMonth'] == month].sort_values(by='Parsed Start Time')
        
        if month_data.empty:
            raise ValueError(f"Keine Ladesessions für den Monat {month} gefunden.")

        # Datum für den Titel formatieren (z.B. "Juli 2026")
        dt_month = datetime.strptime(month, '%Y-%m')
        
        # Deutsche Monatsnamen Mapper
        months_de = {
            1: "Januar", 2: "Februar", 3: "März", 4: "April", 5: "Mai", 6: "Juni",
            7: "Juli", 8: "August", 9: "September", 10: "Oktober", 11: "November", 12: "Dezember"
        }
        month_name = f"{months_de[dt_month.month]} {dt_month.year}"
        
        # PDF Dateiname
        filename = f"Ladenachweis_{month}_{self.employee_name.replace(' ', '_')}.pdf"
        pdf_path = output_dir / filename
        
        # PDF Dokument einrichten (A4, 2cm Ränder)
        doc = SimpleDocTemplate(
            str(pdf_path),
            pagesize=A4,
            leftMargin=2*cm,
            rightMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        # Styles definieren
        styles = getSampleStyleSheet()
        
        # Custom Styles
        title_style = ParagraphStyle(
            'DocTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=22,
            leading=26,
            textColor=colors.HexColor('#1E293B'),
            spaceAfter=15
        )
        
        subtitle_style = ParagraphStyle(
            'DocSubTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=12,
            leading=16,
            textColor=colors.HexColor('#475569'),
            spaceAfter=25
        )
        
        body_style = ParagraphStyle(
            'DocBody',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#334155')
        )
        
        header_table_style = ParagraphStyle(
            'HeaderTableText',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#1E293B')
        )

        table_header_style = ParagraphStyle(
            'TableHeaderText',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9,
            leading=12,
            textColor=colors.white
        )

        table_cell_style = ParagraphStyle(
            'TableCellText',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#334155')
        )

        table_cell_bold_style = ParagraphStyle(
            'TableCellBoldText',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#1E293B')
        )

        elements = []
        
        # 1. Header (Titel & Monat)
        elements.append(Paragraph("Abrechnung Ladekosten Firmenwagen", title_style))
        elements.append(Paragraph(f"Abrechnungsmonat: {month_name}", subtitle_style))
        
        # 2. Stammdaten-Tabelle
        meta_data = [
            [Paragraph("Fahrer:", header_table_style), Paragraph(self.employee_name, body_style)],
            [Paragraph("Fahrzeug-Kennzeichen:", header_table_style), Paragraph(self.license_plate if self.license_plate else "Nicht angegeben", body_style)],
            [Paragraph("Erstattungs-Tarif:", header_table_style), Paragraph(f"{self.price_per_kwh:.4f} € / kWh", body_style)],
            [Paragraph("Erstellungsdatum:", header_table_style), Paragraph(datetime.now().strftime('%d.%m.%Y %H:%M'), body_style)]
        ]
        
        meta_table = Table(meta_data, colWidths=[5*cm, 12*cm])
        meta_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 0),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
        ]))
        
        elements.append(meta_table)
        elements.append(Spacer(1, 20))
        
        # 3. Ladevorgänge Tabelle
        # Header definieren
        table_data = [[
            Paragraph("Datum / Uhrzeit (Start)", table_header_style),
            Paragraph("Ladestation (Alias)", table_header_style),
            Paragraph("Dauer (h)", table_header_style),
            Paragraph("Energie (kWh)", table_header_style),
            Paragraph("Betrag (€)", table_header_style)
        ]]
        
        # Zeilen hinzufügen
        total_kwh = 0.0
        total_duration = 0.0
        total_cost = 0.0
        
        for idx, row in month_data.iterrows():
            date_str = row['Parsed Start Time'].strftime('%d.%m.%Y %H:%M')
            alias = str(row['Charger Alias']) if pd.notna(row['Charger Alias']) else "Unbekannt"
            duration = row['Duration(h)']
            kwh = row['Energy Delivered(kW·h)']
            cost = row['Calculated Cost']
            
            total_kwh += kwh
            total_duration += duration
            total_cost += cost
            
            table_data.append([
                Paragraph(date_str, table_cell_style),
                Paragraph(alias, table_cell_style),
                Paragraph(f"{duration:.2f}", table_cell_style),
                Paragraph(f"{kwh:.3f}", table_cell_style),
                Paragraph(f"{cost:.2f} €", table_cell_style)
            ])
            
        # Summen-Zeile
        table_data.append([
            Paragraph("Gesamtsumme", table_cell_bold_style),
            Paragraph("", table_cell_style),
            Paragraph(f"{total_duration:.2f}", table_cell_bold_style),
            Paragraph(f"{total_kwh:.3f}", table_cell_bold_style),
            Paragraph(f"{total_cost:.2f} €", table_cell_bold_style)
        ])
        
        # Spaltenbreiten (A4 Nutzbreite ist ca. 17cm bei 2x2cm Margins)
        cols_width = [4.2*cm, 5.0*cm, 2.2*cm, 2.8*cm, 2.8*cm]
        
        charging_table = Table(table_data, colWidths=cols_width, repeatRows=1)
        
        # Tabellen-Styling definieren
        t_style = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E293B')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ]
        
        # Alternierende Zeilenfarben (außer Header und Summen-Zeile)
        for i in range(1, len(table_data) - 1):
            if i % 2 == 0:
                t_style.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#F8FAFC')))
                
        # Summenzeile hervorheben
        t_style.append(('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#E2E8F0')))
        
        charging_table.setStyle(TableStyle(t_style))
        elements.append(charging_table)
        elements.append(Spacer(1, 20))
        
        # 4. Zusammenfassung & Unterschrift
        summary_text = (
            f"Hiermit wird die Erstattung von <b>{total_cost:.2f} €</b> für die im Monat {month_name} "
            f"geladene Energie von insgesamt <b>{total_kwh:.3f} kWh</b> auf Basis des vereinbarten "
            f"Stromtarifs von <b>{self.price_per_kwh:.4f} € / kWh</b> beantragt."
        )
        
        elements.append(Paragraph(summary_text, body_style))
        elements.append(Spacer(1, 30))
        
        # Unterschriftenfelder vorbereiten
        sig_date = datetime.now().strftime('%d.%m.%Y')
        
        # Unterschriftenbild laden falls vorhanden
        sig_img_flowable = None
        if self.signature_image_path and os.path.exists(self.signature_image_path):
            try:
                sig_img_flowable = RLImage(self.signature_image_path, width=4.5*cm, height=1.5*cm)
                sig_img_flowable.hAlign = 'LEFT'
            except Exception as e:
                print(f"Fehler beim Laden des Unterschriftenbildes: {e}")

        # Mitarbeiter Unterschriften-Block als Tabelle für perfektes Alignment
        emp_data = [
            ["", sig_img_flowable if sig_img_flowable else Spacer(1, 1.5*cm)],
            [Paragraph(sig_date, body_style), Paragraph("______________________", body_style)],
            [Paragraph("Datum, Unterschrift Mitarbeiter", body_style), ""]
        ]
        emp_sig_block = Table(emp_data, colWidths=[2.2*cm, 5.8*cm])
        emp_sig_block.setStyle(TableStyle([
            ('SPAN', (0, 2), (1, 2)),
            ('VALIGN', (0,0), (-1,-1), 'BOTTOM'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ('TOPPADDING', (0,0), (-1,-1), 0),
        ]))

        # Haupt-Tabelle für die Unterschriften aufbauen
        if self.enable_supervisor_sig:
            # Vorgesetzten Unterschriften-Block
            supervisor_data = [
                ["", Spacer(1, 1.5*cm)],
                ["", Paragraph("______________________", body_style)],
                [Paragraph("Datum, Unterschrift Vorgesetzter", body_style), ""]
            ]
            supervisor_sig_block = Table(supervisor_data, colWidths=[2.2*cm, 5.8*cm])
            supervisor_sig_block.setStyle(TableStyle([
                ('SPAN', (0, 2), (1, 2)),
                ('VALIGN', (0,0), (-1,-1), 'BOTTOM'),
                ('LEFTPADDING', (0,0), (-1,-1), 0),
                ('RIGHTPADDING', (0,0), (-1,-1), 0),
                ('BOTTOMPADDING', (0,0), (-1,-1), 2),
                ('TOPPADDING', (0,0), (-1,-1), 0),
            ]))
            
            sig_data = [[emp_sig_block, supervisor_sig_block]]
            sig_table = Table(sig_data, colWidths=[8.5*cm, 8.5*cm])
        else:
            sig_data = [[emp_sig_block]]
            sig_table = Table(sig_data, colWidths=[17*cm])
            
        sig_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
        ]))
        
        # Zusammenhalten von Zusammenfassung & Unterschrift, damit sie nicht auf eine leere Folgeseite rutschen
        elements.append(KeepTogether([sig_table]))
        
        # PDF bauen
        doc.build(elements)
        
        return pdf_path
