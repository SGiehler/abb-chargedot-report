import os
from pathlib import Path
from dotenv import load_dotenv

# Lade .env Datei falls vorhanden
load_dotenv()

class Config:
    EMPLOYEE_NAME = os.getenv("DEFAULT_EMPLOYEE_NAME", "Dein Name")
    LICENSE_PLATE = os.getenv("DEFAULT_LICENSE_PLATE", "")
    PRICE_PER_KWH = float(os.getenv("DEFAULT_PRICE_PER_KWH", "0.2755"))
    OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "reports"))

    @classmethod
    def to_dict(cls):
        return {
            "employee_name": cls.EMPLOYEE_NAME,
            "license_plate": cls.LICENSE_PLATE,
            "price_per_kwh": cls.PRICE_PER_KWH,
            "output_dir": str(cls.OUTPUT_DIR)
        }
