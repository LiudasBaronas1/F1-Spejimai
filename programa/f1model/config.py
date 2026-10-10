"""Konstantos ir numatytieji keliai. Jokių šalutinių poveikių importuojant (aplankus sukuria App.create)."""
from datetime import datetime, timedelta
from pathlib import Path

PROGRAM_DIR = Path(__file__).resolve().parent.parent   # .../programa
ROOT = PROGRAM_DIR.parent                              # pagrindinis aplankas
DATA_DIR = ROOT / "duomenys"
CACHE_DIR = DATA_DIR / "fastf1_cache"
DB_PATH = DATA_DIR / "f1.db"
CALIBRATION_PATH = DATA_DIR / "oru_kalibracija.json"  # orų prognozės kalibravimas (sources/weather.py)
EXCEL_PATH = DATA_DIR / "Rezultatai_ Bendri.xlsx"   # neprivaloma: asmeninė totalizatoriaus lentelė (ne GitHub'e)
STARTER_DIR = PROGRAM_DIR / "pradiniai_duomenys"       # duomenų bazė naujam vartotojui (kopijuojama pirmą kartą)
PARAMS_JSON = ROOT / "parametrai.json"                 # parametrai, kuriuos galima keisti ranka
REPORT_PATH = ROOT / "PARAMETRAI.md"                   # automatiškai generuojamas aprašas

SEASON = 2026

# Sesijų trumpiniai (FastF1 identifikatoriai)
PRACTICE = ["FP1", "FP2", "FP3"]
QUALI_TYPE = ["SQ", "Q"]      # spėjama pagal vieno rato greitį
RACE_TYPE = ["S", "R"]        # spėjama pagal lenktynių tempą ir starto poziciją
COMPETITIVE = QUALI_TYPE + RACE_TYPE
# Sesijos būsena: ok – oficialūs F1 duomenys (FastF1); fia – preliminarus rezultatas iš FIA klasifikacijos
# (kol F1 archyvas vėluoja; vėliau perrašomas); pending – duomenų dar nėra.
DONE_STATUSES = ("ok", "fia")

# Sesijų trukmė minutėmis – iš jos skaičiuojama, kada laukti duomenų ir koks orų prognozės langas
SESSION_MINUTES = {"FP1": 60, "FP2": 60, "FP3": 60, "SQ": 45, "S": 45, "Q": 60, "R": 120}
READY_PAD_MIN = 15      # oficialūs F1 duomenys anksčiausiai ~15 min. po sesijos pabaigos


def ready_at(date_utc, session, pad_min=READY_PAD_MIN):
    """Kada sesijos duomenys gali būti paskelbti: pradžia + trukmė + atsarga (datetime UTC)."""
    return datetime.fromisoformat(date_utc) + timedelta(minutes=SESSION_MINUTES[session] + pad_min)

SESSION_NAMES_LT = {
    "FP1": "1 treniruotė", "FP2": "2 treniruotė", "FP3": "3 treniruotė",
    "SQ": "Sprinto kvalifikacija", "S": "Sprintas",
    "Q": "Kvalifikacija", "R": "Lenktynės",
}

# FastF1 grąžina pilnus sesijų pavadinimus
FASTF1_NAME_TO_CODE = {
    "Practice 1": "FP1", "Practice 2": "FP2", "Practice 3": "FP3",
    "Sprint Qualifying": "SQ", "Sprint Shootout": "SQ",
    "Sprint": "S", "Qualifying": "Q", "Race": "R",
}
