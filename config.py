import os
from pathlib import Path
from dotenv import load_dotenv

# Lade .env Datei falls vorhanden
load_dotenv()

class Config:
    @classmethod
    def get_employee_name(cls) -> str:
        name = os.getenv("DEFAULT_EMPLOYEE_NAME") or os.getenv("EMPLOYEE_NAME") or ""
        return name if name != "Dein Name" else ""

    @classmethod
    def get_license_plate(cls) -> str:
        return os.getenv("DEFAULT_LICENSE_PLATE") or os.getenv("LICENSE_PLATE") or ""

    @classmethod
    def get_price_per_kwh(cls) -> float:
        val = os.getenv("DEFAULT_PRICE_PER_KWH") or os.getenv("DEFAULT_KWH_PRICE") or os.getenv("PRICE_PER_KWH") or "0.2755"
        try:
            return float(val)
        except ValueError:
            return 0.2755

    @classmethod
    def get_output_dir(cls) -> Path:
        return Path(os.getenv("OUTPUT_DIR", "reports"))

    @classmethod
    def get_enable_supervisor_signature(cls) -> bool:
        val = os.getenv("ENABLE_SUPERVISOR_SIGNATURE") or os.getenv("ENABLE_SUPERVISOR") or "false"
        return val.lower() in ("true", "1", "yes")

    @classmethod
    def to_dict(cls):
        return {
            "employee_name": cls.get_employee_name(),
            "license_plate": cls.get_license_plate(),
            "price_per_kwh": cls.get_price_per_kwh(),
            "output_dir": str(cls.get_output_dir()),
            "enable_supervisor_signature": cls.get_enable_supervisor_signature()
        }
