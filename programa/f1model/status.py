"""Ar spėjimui reikalingi duomenys surinkti: kiekvienai savaitgalio dalis – būsena ok / warn / missing / na.
Naudojama pradžios puslapyje („Duomenys šiam spėjimui“) ir puslapyje „Duomenys“. Tik skaitymas."""
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import pandas as pd

from .config import COMPETITIVE, DONE_STATUSES, PRACTICE

ODDS_STALE_H = 6


@dataclass
class Check:
    key: str                    # results / practice / grid / weather / odds / news
    state: str                  # ok / warn / missing / na
    text: str                   # vertimo raktas („check.<key>.<būsena>“)
    params: dict = field(default_factory=dict)


def _age_h(iso, now):
    return (now - datetime.fromisoformat(iso)).total_seconds() / 3600 if iso else None


def weekend_checks(data, db, season, rnd, session, now=None):
    now = now or datetime.now(timezone.utc)
    sess = data.session_rows(season, rnd).sort_values("date_utc")
    target = sess[sess.session == session].iloc[0]
    before = sess[sess.date_utc < target.date_utc]
    past = before[pd.to_datetime(before.date_utc, utc=True) + timedelta(hours=1) < now]
    checks = []

    # rezultatai ankstesnių šio savaitgalio sesijų
    comp = past[past.session.isin(COMPETITIVE)]
    missing = list(comp[~comp.status.isin(DONE_STATUSES)].session)
    prelim = list(comp[comp.status == "fia"].session)
    if comp.empty:
        checks.append(Check("results", "na", "check.results.na"))
    elif missing:
        checks.append(Check("results", "missing", "check.results.missing", {"sessions": missing}))
    elif prelim:
        checks.append(Check("results", "warn", "check.results.prelim", {"sessions": prelim}))
    else:
        checks.append(Check("results", "ok", "check.results.ok", {"sessions": list(comp.session)}))

    # treniruotės
    fp = past[past.session.isin(PRACTICE)]
    if fp.empty:
        checks.append(Check("practice", "na", "check.practice.na"))
    else:
        have = set(data.prac[(data.prac.season == season) & (data.prac["round"] == rnd)].session)
        lost = [s for s in fp.session if s not in have]
        checks.append(Check("practice", "warn" if lost else "ok",
                            "check.practice.missing" if lost else "check.practice.ok",
                            {"sessions": lost or list(fp.session)}))

    # starto rikiuotė (tik lenktynėms ir sprintui)
    if session in ("R", "S"):
        res = data.results_of(season, rnd, session)
        quali = "Q" if session == "R" else "SQ"
        q_done = data.session_rows(season, rnd, quali).status.isin(DONE_STATUSES).any()
        if not res.empty and res.grid.notna().any():
            checks.append(Check("grid", "ok", "check.grid.official"))
        elif data.fia_grid(season, rnd, session):
            checks.append(Check("grid", "ok", "check.grid.fia"))
        elif q_done:
            checks.append(Check("grid", "warn", "check.grid.quali"))
        else:
            checks.append(Check("grid", "missing", "check.grid.none"))

    # orai
    if pd.notna(target.track_rain_frac):
        checks.append(Check("weather", "ok", "check.weather.sensors"))
    else:
        w = db.query("SELECT fetched_at FROM weather WHERE season=? AND round=? AND session=?", (season, rnd, session))
        age = _age_h(w.fetched_at.iloc[0], now) if not w.empty and pd.notna(w.fetched_at.iloc[0]) else None
        if age is None:
            checks.append(Check("weather", "missing", "check.weather.none"))
        else:
            checks.append(Check("weather", "ok" if age < 12 else "warn", "check.weather.forecast", {"age": age}))

    # lažybų rinkos
    o = db.query("SELECT source, market, MAX(price_ts) ts, MAX(fetched_at) f FROM odds WHERE season=? AND round=? "
                 "AND session=? GROUP BY source, market", (season, rnd, session))
    if o.empty:
        checks.append(Check("odds", "missing", "check.odds.none"))
    else:
        age = _age_h(o.f.max(), now)
        last_prev = past.date_utc.max() if not past.empty else None
        stale = target.status not in DONE_STATUSES and (
            age > ODDS_STALE_H or (last_prev is not None and o.f.max() < last_prev))
        checks.append(Check("odds", "warn" if stale else "ok", "check.odds.stale" if stale else "check.odds.ok",
                            {"sources": sorted(set(o.source)), "markets": len(o), "age": age}))

    # naujienos
    n = db.query("SELECT MAX(gauta) g FROM naujienos").g.iloc[0]
    age = _age_h(n, now) if n else None
    checks.append(Check("news", "missing" if age is None else "ok" if age < 24 else "warn",
                        "check.news.none" if age is None else "check.news.ok", {"age": age or 0}))
    return checks


def season_matrix(data, season, now=None):
    """Sezono duomenų suvestinė: etapas × sesija -> ok / fia / missing / upcoming (puslapiui „Duomenys“)."""
    now = (now or datetime.now(timezone.utc)).isoformat()
    s = data.sess[data.sess.season == season].copy()
    s["state"] = [st if st in DONE_STATUSES else ("missing" if d < now else "upcoming")
                  for st, d in zip(s.status, s.date_utc)]
    return s.pivot_table(index="round", columns="session", values="state", aggfunc="first")
