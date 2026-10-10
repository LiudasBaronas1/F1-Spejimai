"""Oficialūs F1 duomenys: FastF1 (šis sezonas, su ratais) ir Ergast/Jolpica archyvas (ankstesni sezonai)."""
import logging
import time
from datetime import datetime, timedelta, timezone

import fastf1
import numpy as np
import pandas as pd

from ..config import FASTF1_NAME_TO_CODE, PRACTICE, SEASON, ready_at
from . import DataSource

logging.getLogger("fastf1").setLevel(logging.ERROR)
log = logging.getLogger("f1")

PAGE_PAUSE_S, RETRY_WAIT_S, MAX_RETRIES = 3, 120, 35   # archyvo puslapiai ir užklausų limitas


def enable_cache(path):
    """FastF1 apdorotų sesijų talpykla (be neapdorotų HTTP atsakymų – jie užimdavo šimtus MB).
    Kviečia kompozicijos šaknis (App.create), ne importas."""
    path.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(path), use_requests_cache=False)


def _sec(td):
    return td.total_seconds() if pd.notna(td) else None


def _int(x):
    try:
        return int(x) if pd.notna(x) else None
    except (TypeError, ValueError):
        return None


def _now():
    return datetime.now(timezone.utc).isoformat()


def save_schedule(db, season):
    sched = fastf1.get_event_schedule(season, include_testing=False)
    events, sessions = [], []
    for _, ev in sched.iterrows():
        rnd = int(ev["RoundNumber"])
        events.append(dict(season=season, round=rnd, name=ev["EventName"], country=ev["Country"],
                           location=ev["Location"], date=str(ev["EventDate"].date()), format=ev["EventFormat"]))
        for i in range(1, 6):
            code, start = FASTF1_NAME_TO_CODE.get(ev.get(f"Session{i}")), ev.get(f"Session{i}DateUtc")
            if code and pd.notna(start):
                sessions.append((season, rnd, code, pd.Timestamp(start).tz_localize("UTC").isoformat()))
    db.write("events", events)
    with db.connect() as con:
        for s in sessions:  # jau surinktų sesijų būsena neperrašoma
            con.execute("INSERT OR IGNORE INTO sessions (season, round, session, date_utc, status) "
                        "VALUES (?,?,?,?, 'pending')", s)
            con.execute("UPDATE sessions SET date_utc=? WHERE season=? AND round=? AND session=?",
                        (s[3], s[0], s[1], s[2]))


def save_rows(db, table, season, rnd, code, rows):
    db.write(table, rows, replace_where=("season=? AND round=? AND session=?", (season, rnd, code)))
    with db.connect() as con:
        con.execute("UPDATE sessions SET status=?, loaded_at=? WHERE season=? AND round=? AND session=?",
                    ("ok" if rows else "pending", _now(), season, rnd, code))


# ------------------------------------------------------------------ treniruotės

def practice_rows(season, rnd, code, laps):
    clean = laps.pick_wo_box()
    clean = clean[clean["LapTime"].notna() & (clean["Deleted"] != True)]  # noqa: E712 (gali būti None)
    rows = []
    for drv, dl in clean.groupby("Driver"):
        long_runs, degs = [], []  # ilgų serijų tempas (mediana) ir padangų dėvėjimasis (nuolydis)
        for _, st in dl.groupby("Stint"):
            st = st[st["LapTime"] <= st["LapTime"].min() * 1.04]
            if len(st) >= 5:
                long_runs.append((st["LapTime"].median(), len(st)))
                x = st["LapNumber"].values.astype(float)
                if np.ptp(x) > 0:
                    degs.append((np.polyfit(x, st["LapTime"].dt.total_seconds().values, 1)[0], len(st)))
        lr = min(long_runs, key=lambda x: x[0]) if long_runs else (pd.NaT, 0)
        sectors = [dl[c].min() for c in ("Sector1Time", "Sector2Time", "Sector3Time") if c in dl]
        ideal = sum(sectors, pd.Timedelta(0)) if len(sectors) == 3 and all(pd.notna(s) for s in sectors) else pd.NaT
        sim = dl[(dl["Compound"] == "SOFT") & (dl["TyreLife"] <= 3)] if {"Compound", "TyreLife"} <= set(dl) else dl[:0]
        rows.append(dict(season=season, round=rnd, session=code, driver=drv, team=dl["Team"].iloc[0],
                         best_lap_s=_sec(dl["LapTime"].min()), laps=len(dl), long_run_s=_sec(lr[0]),
                         long_run_laps=lr[1],
                         deg_s_per_lap=sum(d * n for d, n in degs) / sum(n for _, n in degs) if degs else None,
                         ideal_lap_s=_sec(ideal), quali_sim_s=_sec(sim["LapTime"].min() if not sim.empty else pd.NaT)))
    return rows


# ------------------------------------------------------------------ rezultatai

def knockout_classification(laps, min_gap=timedelta(minutes=4)):
    """Kvalifikacijos klasifikacija iš ratų: segmentus (Q1/Q2/Q3) skiria pertraukos be automobilių
    trasoje; rikiuojama pagal pasiektą segmentą, tada pagal geriausią ratą jame."""
    laps = laps[laps["LapStartTime"].notna()].sort_values("LapStartTime")
    ends = laps["LapStartTime"] + laps["LapTime"].fillna(pd.Timedelta(minutes=2))
    seg, current, last_end = [], 0, None
    for start, end in zip(laps["LapStartTime"], ends):
        if last_end is not None and start - last_end > min_gap:
            current += 1
        seg.append(current)
        last_end = end if last_end is None else max(last_end, end)
    laps = laps.assign(Segment=seg)
    rank = []
    for drv, dl in laps.groupby("Driver"):
        top = dl["Segment"].max()
        best = dl[dl["Segment"] == top]["LapTime"].min()
        rank.append((-top, best if pd.notna(best) else pd.Timedelta(hours=1), drv))
    return [d for _, _, d in sorted(rank)]


def on_track_order(laps):
    """Finišo tvarka trasoje (be baudų po finišo): daugiau ratų -> anksčiau kirto liniją."""
    last = laps[laps["Time"].notna()].sort_values("LapNumber").groupby("Driver").tail(1)
    return last.sort_values(["LapNumber", "Time"], ascending=[False, True])["Driver"].tolist()


def result_rows(season, rnd, code, session):
    res, laps = session.results, session.laps
    if res is None or res.empty:
        return []
    if res["Position"].isna().all():  # sprinto kvalifikacijai pozicijų dažnai nėra – skaičiuojame iš ratų
        if laps is None or laps.empty:
            return []
        res = res.assign(Position=res["Abbreviation"].map(
            {d: i + 1 for i, d in enumerate(knockout_classification(laps))}))
    on_track = {}
    if code in ("R", "S") and laps is not None and not laps.empty:  # žaidimas vertina finišą trasoje
        on_track = {d: i + 1 for i, d in enumerate(on_track_order(laps))}
    rows = []
    for _, r in res.iterrows():
        q = [r.get(c) for c in ("Q1", "Q2", "Q3") if pd.notna(r.get(c))]
        pos = _int(r["Position"])
        rows.append(dict(season=season, round=rnd, session=code, driver=r["Abbreviation"],
                         number=str(r["DriverNumber"]), team=r["TeamName"],
                         position=on_track.get(r["Abbreviation"], pos), official_position=pos,
                         grid=_int(r.get("GridPosition")) or None, status=r.get("Status"),
                         best_lap_s=_sec(min(q)) if q else None,
                         points=float(r["Points"]) if pd.notna(r.get("Points")) else None))
    return rows


def load_session(db, season, rnd, code):
    session = fastf1.get_session(season, rnd, code)
    session.load(laps=True, telemetry=False, weather=False, messages=False)
    if code in PRACTICE:
        rows = practice_rows(season, rnd, code, session.laps) if session.laps is not None and not session.laps.empty else []
        save_rows(db, "practice", season, rnd, code, rows)
    else:
        rows = result_rows(season, rnd, code, session)
        save_rows(db, "results", season, rnd, code, rows)
    return bool(rows)


# ------------------------------------------------------------------ archyvas (ankstesni sezonai)

def _with_retry(call):
    for attempt in range(MAX_RETRIES):
        try:
            return call()
        except Exception as e:
            if "Too Many Requests" not in str(e) and "500 calls" not in str(e):
                raise
            log.info("užklausų limitas – laukiu %s s (%s/%s)", RETRY_WAIT_S, attempt + 1, MAX_RETRIES)
            time.sleep(RETRY_WAIT_S)
    raise RuntimeError("Užklausų limitas neatsinaujino")


def _ergast_rows(season, rnd, code, df):
    rows = []
    for _, r in df.iterrows():
        q = [r.get(c) for c in ("Q1", "Q2", "Q3") if pd.notna(r.get(c))]
        rows.append(dict(season=season, round=rnd, session=code, driver=r["driverCode"],
                         number=str(r.get("number")), team=r.get("constructorName"),
                         position=_int(r.get("position")), official_position=_int(r.get("position")),
                         grid=_int(r.get("grid")) or None, status=r.get("status"),
                         best_lap_s=_sec(min(q)) if q else None,
                         points=float(r["points"]) if pd.notna(r.get("points")) else None))
    return rows


def _whole_season(fn, season):
    """Visas sezonas puslapiais po 100 eilučių -> {etapas: DataFrame}."""
    out, resp = {}, _with_retry(lambda: fn(season=season, limit=100))
    while True:
        for (_, d), df in zip(resp.description.iterrows(), resp.content):
            out[int(d["round"])] = pd.concat([out.get(int(d["round"])), df], ignore_index=True)
        if resp.is_complete:
            return out
        time.sleep(PAGE_PAUSE_S)
        try:
            resp = _with_retry(resp.get_next_result_page)
        except ValueError:  # daugiau puslapių nėra
            return out


def update_history(db, season):
    """Ankstesnio sezono rezultatai DALIMIS (lenktynės, kvalifikacijos, sprintai atskirai).
    Sprinto kvalifikacijos rezultatas = sprinto starto rikiuotė."""
    from fastf1.ergast import Ergast
    erg = Ergast(result_type="pandas", auto_cast=True)
    _with_retry(lambda: save_schedule(db, season))
    for code, fn in [("R", erg.get_race_results), ("Q", erg.get_qualifying_results), ("S", erg.get_sprint_results)]:
        todo = db.query("SELECT round FROM sessions WHERE season=? AND status!='ok' AND session=?",
                        (season, code))["round"].astype(int).tolist()
        if not todo:
            continue
        data = _whole_season(fn, season)
        for rnd in (r for r in todo if r in data):
            save_rows(db, "results", season, rnd, code, _ergast_rows(season, rnd, code, data[rnd]))
            if code == "S":
                sq = data[rnd].sort_values("grid").assign(position=lambda d: range(1, len(d) + 1))
                sq.loc[sq.grid.fillna(0) <= 0, "position"] = None  # startas iš boksų – vieta nežinoma
                save_rows(db, "results", season, rnd, "SQ",
                          _ergast_rows(season, rnd, "SQ", sq.assign(grid=None, status=None, points=None)))
        log.info("%s %s: įrašyta %s etapų", season, code, sum(r in data for r in todo))
        time.sleep(PAGE_PAUSE_S)


class OfficialSource(DataSource):
    label = "oficialūs F1 duomenys"
    expected_s = 15.0

    def update(self, season):
        if season < SEASON:
            return update_history(self.db, season)
        save_schedule(self.db, season)
        now = datetime.now(timezone.utc)
        todo = self.db.query("SELECT s.round, s.session, s.date_utc, e.name FROM sessions s JOIN events e "
                             "USING(season, round) WHERE s.season=? AND s.status!='ok' ORDER BY s.date_utc", (season,))
        todo = todo[[ready_at(d, c) <= now for d, c in zip(todo.date_utc, todo.session)]]
        for i, (_, s) in enumerate(todo.iterrows()):
            self.progress(i, len(todo), f"{season} R{s['round']:02d} {s['name']} · {s.session}")
            try:
                ok = load_session(self.db, season, int(s["round"]), s.session)
                log.info("%s R%02d %-3s -> %s", season, s["round"], s.session, "gerai" if ok else "duomenų dar nėra")
            except Exception as e:  # tinklo ar duomenų klaida – bandysime kitą kartą
                log.warning("%s R%02d %-3s -> klaida: %s", season, s["round"], s.session, e)
