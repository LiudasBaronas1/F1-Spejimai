"""SQLite duomenų bazė. `Database` – priklausomybė, kurią gauna visi ją naudojantys moduliai
(testams galima perduoti kitą failą)."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import pandas as pd

# pandas/numpy skaičiai užklausų parametruose (kitaip SQLite juos įrašytų kaip baitus ir nerastų sutapimų)
for _t in (np.int64, np.int32):
    sqlite3.register_adapter(_t, int)
sqlite3.register_adapter(np.float64, float)

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    season INTEGER, round INTEGER, name TEXT, country TEXT, location TEXT, date TEXT, format TEXT,
    PRIMARY KEY (season, round));
CREATE TABLE IF NOT EXISTS sessions (
    season INTEGER, round INTEGER, session TEXT, date_utc TEXT,
    status TEXT,              -- 'ok' (duomenys surinkti) / 'pending'
    loaded_at TEXT, PRIMARY KEY (season, round, session));
CREATE TABLE IF NOT EXISTS results (
    season INTEGER, round INTEGER, session TEXT, driver TEXT, number TEXT, team TEXT,
    position INTEGER,          -- finišo vieta TRASOJE (be baudų po finišo) – taip vertina žaidimas
    official_position INTEGER, -- oficiali klasifikacija (su baudomis)
    grid INTEGER, status TEXT, best_lap_s REAL, points REAL,
    PRIMARY KEY (season, round, session, driver));
CREATE TABLE IF NOT EXISTS practice (
    season INTEGER, round INTEGER, session TEXT, driver TEXT, team TEXT,
    best_lap_s REAL, laps INTEGER, long_run_s REAL, long_run_laps INTEGER, deg_s_per_lap REAL,
    ideal_lap_s REAL, quali_sim_s REAL, PRIMARY KEY (season, round, session, driver));
CREATE TABLE IF NOT EXISTS weather (
    season INTEGER, round INTEGER, session TEXT,
    rain_prob REAL,            -- galutinė lietaus tikimybė (faktas iš jutiklių arba kalibruota prognozė)
    rain_prob_fc REAL,         -- kalibruota prognozė (tokia, kokia buvo žinoma prieš sesiją)
    rain_mm REAL, region_rain_mm REAL, temp_c REAL, source TEXT, fetched_at TEXT,
    track_rain_frac REAL, track_air_c REAL, track_temp_c REAL,          -- trasos jutikliai
    fc_pop REAL, fc_pop_region REAL, fc_precip REAL, fc_cloud REAL,     -- prognozės požymiai
    PRIMARY KEY (season, round, session));
CREATE TABLE IF NOT EXISTS odds (
    season INTEGER, round INTEGER, session TEXT, market TEXT, driver TEXT,
    price REAL, prob REAL, volume REAL, price_ts TEXT, event_slug TEXT, fetched_at TEXT,
    source TEXT,               -- polymarket / kalshi / bookmakers
    PRIMARY KEY (season, round, session, market, driver, source));
CREATE TABLE IF NOT EXISTS model_params (
    kind TEXT, name TEXT, value REAL, n_samples INTEGER, fitted_at TEXT, PRIMARY KEY (kind, name));
CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT, season INTEGER, round INTEGER, session TEXT,
    driver TEXT, p1 REAL, p2 REAL, p3 REAL, p_top3 REAL, pick_pos INTEGER);

-- ŽINYNAI (redaguojami programoje; pradinės reikšmės – reference.py)
CREATE TABLE IF NOT EXISTS trasos (
    trasa TEXT PRIMARY KEY, greitis REAL, prispaudimas REAL, gatve REAL, padangos REAL,
    lenkimo_sunkumas REAL, platuma REAL, ilguma REAL);
CREATE TABLE IF NOT EXISTS trasu_sinonimai (vieta TEXT PRIMARY KEY, trasa TEXT);
CREATE TABLE IF NOT EXISTS komandos (raktazodis TEXT PRIMARY KEY, spalva TEXT);
CREATE TABLE IF NOT EXISTS zaidejai (vardas TEXT PRIMARY KEY, aktyvus INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS gp_pavadinimai (excel_pavadinimas TEXT PRIMARY KEY, fastf1_dalis TEXT);
CREATE TABLE IF NOT EXISTS vairuotoju_vardai (vardas TEXT PRIMARY KEY, kodas TEXT);
CREATE TABLE IF NOT EXISTS trasu_konturai (
    trasa TEXT PRIMARY KEY, taskai TEXT,   -- JSON [[x, y], ...] (0..1), pagal greičiausią ratą
    posukiai TEXT,                         -- JSON [[numeris, x, y], ...]
    sezonas INTEGER, etapas INTEGER);

-- FIA DOKUMENTAI (sources/fia.py)
CREATE TABLE IF NOT EXISTS atnaujinimai (
    season INTEGER, round INTEGER, komanda TEXT,
    nr INTEGER,                -- detalės nr. dokumente; 0 – komanda atnaujinimų neatvežė
    detale TEXT, priezastis TEXT,   -- performance / circuit / reliability
    aprasymas TEXT,
    puslapis INTEGER,          -- komandos puslapis FIA PDF'e (nuorodai)
    PRIMARY KEY (season, round, komanda, nr));
CREATE TABLE IF NOT EXISTS starto_rikiuote (
    season INTEGER, round INTEGER, session TEXT, driver TEXT, grid INTEGER, dokumentas TEXT,
    PRIMARY KEY (season, round, session, driver));
CREATE TABLE IF NOT EXISTS fia_dokumentai (
    tipas TEXT, season INTEGER, round INTEGER, url TEXT, gauta TEXT, PRIMARY KEY (tipas, season, round));

-- NAUJIENOS (sources/news.py; šaltiniai ir temos – žinynai)
CREATE TABLE IF NOT EXISTS naujienos (
    url TEXT PRIMARY KEY, saltinis TEXT, pavadinimas TEXT, santrauka TEXT, paskelbta TEXT,
    komandos TEXT, zymes TEXT, gauta TEXT);
CREATE TABLE IF NOT EXISTS naujienu_saltiniai (pavadinimas TEXT PRIMARY KEY, adresas TEXT, aktyvus INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS naujienu_zymes (zyme TEXT, raktazodis TEXT, PRIMARY KEY (zyme, raktazodis));

-- SĄSAJA (pradinės reikšmės – translations.py)
CREATE TABLE IF NOT EXISTS kalbos (kodas TEXT PRIMARY KEY, pavadinimas TEXT);
CREATE TABLE IF NOT EXISTS vertimai (raktas TEXT, kalba TEXT, tekstas TEXT, PRIMARY KEY (raktas, kalba));
CREATE TABLE IF NOT EXISTS nustatymai (raktas TEXT PRIMARY KEY, reiksme TEXT);

-- Modelio duomenų versija: didinama trigeriais po kiekvieno modelio duomenų pakeitimo (žr. data_version)
CREATE TABLE IF NOT EXISTS duomenu_versija (id INTEGER PRIMARY KEY CHECK (id = 1), n INTEGER);
INSERT OR IGNORE INTO duomenu_versija VALUES (1, 0);
"""

# Lentelės, kurių pakeitimai NEKEIČIA modelio (jo paties išvestis, sąsaja). Visos kitos (ir naujos) – keičia.
NOT_MODEL_INPUT = {"model_params", "predictions", "zaideju_spejimai", "trasu_konturai",
                   "kalbos", "vertimai", "nustatymai", "duomenu_versija",
                   "fia_dokumentai", "naujienos", "naujienu_saltiniai", "naujienu_zymes", "atnaujinimai"}

# Senesnių DB versijų atnaujinimas: (lentelė, stulpelis, tipas)
NEW_COLUMNS = [("results", "official_position", "INTEGER"), ("weather", "region_rain_mm", "REAL"),
               ("practice", "deg_s_per_lap", "REAL"), ("practice", "ideal_lap_s", "REAL"),
               ("practice", "quali_sim_s", "REAL"), ("weather", "track_rain_frac", "REAL"),
               ("weather", "track_air_c", "REAL"), ("weather", "track_temp_c", "REAL"),
               ("weather", "fc_pop", "REAL"), ("weather", "fc_pop_region", "REAL"),
               ("weather", "fc_precip", "REAL"), ("weather", "fc_cloud", "REAL"),
               ("atnaujinimai", "puslapis", "INTEGER"), ("weather", "rain_prob_fc", "REAL")]
OLD_VIEWS = ["v_rezultatai", "v_orai", "v_treniruotes", "v_vairuotojai", "v_koeficientai", "v_modelio_spejimai",
             "v_atnaujinimai"]   # buvusios SQL skilties rodiniai – pašalinami

class Database:
    def __init__(self, path):
        self.path = Path(path)
        self._migrated = False

    @contextmanager
    def connect(self):
        con = sqlite3.connect(self.path)
        try:
            if not self._migrated:  # schema ir migracijos – vieną kartą per objektą
                self._migrate(con)
                self._migrated = True
            yield con
            con.commit()
        finally:
            con.close()

    @staticmethod
    def _migrate(con):
        con.executescript(SCHEMA)
        for table, col, typ in NEW_COLUMNS:
            if col not in {r[1] for r in con.execute(f"PRAGMA table_info({table})")}:
                con.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")
        con.execute("UPDATE results SET official_position = position WHERE official_position IS NULL")
        for name in OLD_VIEWS:
            con.execute(f"DROP VIEW IF EXISTS {name}")
        tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        for table in tables:
            for op in ("INSERT", "UPDATE", "DELETE"):
                if table in NOT_MODEL_INPUT:  # jei lentelė vėliau tapo „ne modelio“ – trigerį pašaliname
                    con.execute(f"DROP TRIGGER IF EXISTS {table}_{op.lower()}_versija")
                else:
                    con.execute(f"CREATE TRIGGER IF NOT EXISTS {table}_{op.lower()}_versija AFTER {op} ON {table} "
                                f"BEGIN UPDATE duomenu_versija SET n = n + 1; END")

    def data_version(self):
        """Keičiasi tik pasikeitus modelio duomenims (ne sąsajos tekstams, išsaugotiems spėjimams ar svoriams)."""
        return int(self.query("SELECT n FROM duomenu_versija").n.iloc[0])

    def query(self, sql, params=()):
        with self.connect() as con:
            return pd.read_sql_query(sql, con, params=params)

    def write(self, table, rows, keys=None, replace_where=None):
        """Įrašo eilutes. keys – atnaujinami tik pateikti stulpeliai (kiti lieka);
        be keys – eilutė perrašoma visa. replace_where=(sql, params) – prieš tai ištrinama."""
        with self.connect() as con:
            if replace_where:
                con.execute(f"DELETE FROM {table} WHERE {replace_where[0]}", replace_where[1])
            if rows:
                cols = list(rows[0].keys())
                sql = f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})"
                if keys:
                    sql += f" ON CONFLICT({','.join(keys)}) DO UPDATE SET " + \
                           ", ".join(f"{c}=excluded.{c}" for c in cols if c not in keys)
                else:
                    sql = sql.replace("INSERT", "INSERT OR REPLACE", 1)
                con.executemany(sql, [tuple(r[c] for c in cols) for r in rows])

    def execute(self, sql, params=()):
        with self.connect() as con:
            con.execute(sql, params)
