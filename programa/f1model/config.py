from pathlib import Path

PROGRAM_DIR = Path(__file__).resolve().parent.parent   # .../programa
ROOT = PROGRAM_DIR.parent                              # pagrindinis aplankas
DATA_DIR = ROOT / "duomenys"
CACHE_DIR = DATA_DIR / "fastf1_cache"
DB_PATH = DATA_DIR / "f1.db"
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

for d in (DATA_DIR, CACHE_DIR):
    d.mkdir(parents=True, exist_ok=True)
