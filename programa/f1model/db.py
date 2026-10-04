"""SQLite duomenų bazė. `Database` – priklausomybė, kurią gauna visi ją naudojantys moduliai
(testams galima perduoti kitą failą)."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

import pandas as pd

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
CREATE TABLE IF NOT EXISTS zaideju_spejimai (
    zaidejas TEXT, season INTEGER, round INTEGER, session TEXT, vieta INTEGER, spejimas TEXT,
    rezultatas_excel TEXT, PRIMARY KEY (zaidejas, season, round, session, vieta));

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
                   "kalbos", "vertimai", "nustatymai", "duomenu_versija"}

# Senesnių DB versijų atnaujinimas: (lentelė, stulpelis, tipas)
NEW_COLUMNS = [("results", "official_position", "INTEGER"), ("weather", "region_rain_mm", "REAL"),
               ("practice", "deg_s_per_lap", "REAL"), ("practice", "ideal_lap_s", "REAL"),
               ("practice", "quali_sim_s", "REAL"), ("weather", "track_rain_frac", "REAL"),
               ("weather", "track_air_c", "REAL"), ("weather", "track_temp_c", "REAL"),
               ("weather", "fc_pop", "REAL"), ("weather", "fc_pop_region", "REAL"),
               ("weather", "fc_precip", "REAL"), ("weather", "fc_cloud", "REAL")]

VIEWS = {
    "v_rezultatai": """
        SELECT r.season AS metai, r.round AS etapas, e.name AS grand_prix, e.location AS trasa,
               r.session AS sesija, s.date_utc AS data, r.driver AS vairuotojas, r.team AS komanda,
               r.position AS vieta, r.official_position AS oficiali_vieta, r.grid AS starto_vieta,
               r.status AS statusas, r.best_lap_s AS geriausias_ratas_s, r.points AS taskai,
               w.rain_prob AS lietus, w.temp_c AS temperatura
        FROM results r JOIN events e USING(season, round) JOIN sessions s USING(season, round, session)
        LEFT JOIN weather w USING(season, round, session)""",
    "v_orai": """
        SELECT w.season AS metai, w.round AS etapas, e.name AS grand_prix, e.location AS trasa,
               w.session AS sesija, s.date_utc AS data, w.rain_prob AS lietaus_tikimybe,
               w.track_rain_frac AS lijo_trasoje_laiko_dalis, w.fc_pop AS prognozes_tikimybe,
               w.rain_mm AS krituliai_mm, w.region_rain_mm AS krituliai_regione_mm, w.fc_cloud AS debesuotumas,
               w.temp_c AS temperatura, w.track_temp_c AS trasos_temperatura, w.source AS saltinis
        FROM weather w JOIN events e USING(season, round) JOIN sessions s USING(season, round, session)""",
    "v_treniruotes": """
        SELECT p.season AS metai, p.round AS etapas, e.name AS grand_prix, p.session AS sesija,
               p.driver AS vairuotojas, p.team AS komanda, p.best_lap_s AS geriausias_ratas_s,
               p.laps AS ratai, p.long_run_s AS ilgos_serijos_tempas_s,
               p.long_run_laps AS ilgos_serijos_ratai, p.deg_s_per_lap AS padangu_devejimas_s_ratui,
               p.ideal_lap_s AS idealus_ratas_s, p.quali_sim_s AS kvalif_simuliacija_s
        FROM practice p JOIN events e USING(season, round)""",
    "v_vairuotojai": """
        SELECT r.season AS metai, r.driver AS vairuotojas, MAX(r.team) AS komanda,
               SUM(r.session='R') AS lenktynes, SUM(r.session='R' AND r.position=1) AS pergales,
               SUM(r.session='R' AND r.position<=3) AS podiumai,
               ROUND(AVG(CASE WHEN r.session='R' THEN r.position END), 2) AS vid_vieta_lenktynese,
               ROUND(AVG(CASE WHEN r.session='Q' THEN r.position END), 2) AS vid_vieta_kvalifikacijoje,
               SUM(r.session='Q' AND r.position=1) AS pole_pozicijos, SUM(r.points) AS taskai
        FROM results r GROUP BY r.season, r.driver""",
    "v_koeficientai": """
        SELECT o.season AS metai, o.round AS etapas, e.name AS grand_prix, o.session AS sesija,
               o.market AS rinka, o.source AS saltinis, o.driver AS vairuotojas, ROUND(o.prob, 4) AS tikimybe,
               ROUND(1.0 / NULLIF(o.prob, 0), 2) AS koeficientas, ROUND(o.volume) AS apyvarta_usd,
               o.price_ts AS kainos_laikas, r.position AS tikra_vieta
        FROM odds o JOIN events e USING(season, round) LEFT JOIN results r USING(season, round, session, driver)""",
    "v_modelio_spejimai": """
        SELECT p.created_at AS sukurta, p.season AS metai, p.round AS etapas, e.name AS grand_prix,
               p.session AS sesija, p.pick_pos AS speta_vieta, p.driver AS vairuotojas,
               ROUND(p.p_top3, 3) AS tikimybe_top3, r.position AS tikra_vieta
        FROM predictions p JOIN events e USING(season, round) LEFT JOIN results r USING(season, round, session, driver)
        WHERE p.pick_pos IS NOT NULL""",
}

TABLE_INFO = {
    "events": "Etapai (Grand Prix): metai, etapo nr., pavadinimas, šalis, trasa, data, formatas",
    "sessions": "Sesijos: FP1–3, SQ, S, Q, R; pradžios laikas UTC, ar duomenys surinkti",
    "results": "Rezultatai: vieta (finišas trasoje), oficiali vieta, starto vieta, statusas, taškai",
    "practice": "Treniruotės: geriausias ratas, ilgų serijų tempas, padangų dėvėjimasis",
    "weather": "Orai: jutiklių faktas, prognozės požymiai, galutinė lietaus tikimybė",
    "odds": "Lažybų kainos prieš sesiją: win / pole / podium / top5; polymarket / kalshi / bookmakers",
    "predictions": "Visi išsaugoti modelio spėjimai su tikimybėmis",
    "model_params": "Paskutiniai išmokti modelio svoriai",
    "zaideju_spejimai": "Jūsų ir draugų spėjimai iš Excel lentelės",
    "trasos": "Žinynas: trasų charakteristikos (1–5), lenkimo sunkumas, koordinatės",
    "trasu_sinonimai": "Žinynas: FastF1 vietovės pavadinimas -> trasa",
    "komandos": "Žinynas: komandų spalvos (pagal raktinį žodį pavadinime)",
    "zaidejai": "Žinynas: totalizatoriaus žaidėjai (Excel lapų pavadinimai)",
    "gp_pavadinimai": "Žinynas: Excel GP pavadinimas -> FastF1 pavadinimo dalis",
    "vairuotoju_vardai": "Žinynas: vardai lažybų rinkose -> vairuotojo trumpinys",
    "trasu_konturai": "Trasų žemėlapiai: kontūras ir posūkiai (iš greičiausio kvalifikacijos rato)",
    "kalbos": "Sąsajos kalbos (kodas -> pavadinimas)",
    "vertimai": "Sąsajos tekstai kiekviena kalba (raktas, kalba, tekstas)",
    "nustatymai": "Programos pasirinkimai, pvz. sąsajos kalba",
    "duomenu_versija": "Modelio duomenų pakeitimų skaitiklis (pagal jį modelis persimoko)",
    **{v: f"Rodinys: {d}" for v, d in [("v_rezultatai", "Rezultatai su GP pavadinimu, data ir orais"),
                                 ("v_orai", "Orai: prognozė ir jutiklių faktas"),
                                 ("v_treniruotes", "Treniruočių tempas su GP pavadinimu"),
                                 ("v_vairuotojai", "Vairuotojų sezono suvestinė"),
                                 ("v_koeficientai", "Lažybų tikimybės ir koeficientai šalia rezultato"),
                                 ("v_modelio_spejimai", "Modelio spėjimai palyginti su tikru rezultatu")]},
}


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
        existing = dict(con.execute("SELECT name, sql FROM sqlite_master WHERE type='view'").fetchall())
        for name, sql in VIEWS.items():
            create = f"CREATE VIEW {name} AS {sql}"
            if existing.get(name) != create:  # perkuriame tik pasikeitusius (kad nekistų DB failas)
                con.execute(f"DROP VIEW IF EXISTS {name}")
                con.execute(create)
        tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        for table in set(tables) - NOT_MODEL_INPUT:
            for op in ("INSERT", "UPDATE", "DELETE"):
                con.execute(f"CREATE TRIGGER IF NOT EXISTS {table}_{op.lower()}_versija AFTER {op} ON {table} "
                            f"BEGIN UPDATE duomenu_versija SET n = n + 1; END")

    def mtime(self):
        return self.path.stat().st_mtime if self.path.exists() else 0

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

    def read_only_query(self, sql, max_rows=10000):
        """Vartotojo SQL užklausa TIK SKAITYMO režimu (duomenų pakeisti neįmanoma)."""
        con = sqlite3.connect(f"{self.path.resolve().as_uri()}?mode=ro", uri=True)
        try:
            cur = con.execute(sql)
            rows = cur.fetchmany(max_rows + 1)
            return pd.DataFrame(rows[:max_rows], columns=[d[0] for d in cur.description or []]), len(rows) > max_rows
        finally:
            con.close()

    def schema(self):
        with self.connect() as con:
            names = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view') "
                                               "AND name NOT LIKE 'sqlite_%' ORDER BY type DESC, name")]
            return {n: [r[1] for r in con.execute(f"PRAGMA table_info({n})")] for n in names}
