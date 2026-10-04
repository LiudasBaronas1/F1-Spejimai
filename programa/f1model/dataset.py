"""Visi modeliui reikalingi duomenys (iš DB) + nustatymai ir žinynai, kurie perduodami kartu."""
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .config import COMPETITIVE, QUALI_TYPE, SEASON
from .reference import Reference
from .settings import Settings


def kind_of(session):
    return "quali" if session in QUALI_TYPE else "race"


def _finished(status):
    s = str(status or "")
    return s == "Finished" or s.startswith("+") or s == "Lapped"


@dataclass
class Dataset:
    sess: pd.DataFrame
    res: pd.DataFrame
    prac: pd.DataFrame
    events: pd.DataFrame
    odds: pd.DataFrame
    settings: Settings
    ref: Reference
    cache: dict = field(default_factory=dict)   # apskaičiuoti požymiai (pagal sesiją ir laiką)

    @classmethod
    def load(cls, db, settings):
        ref = Reference.load(db)
        sess = db.query("SELECT s.*, w.rain_prob, w.rain_mm, w.region_rain_mm, w.temp_c, w.fc_pop, w.fc_cloud, "
                        "w.track_rain_frac, w.source AS weather_source FROM sessions s LEFT JOIN weather w "
                        "USING(season, round, session)")
        events = db.query("SELECT * FROM events")
        events["circuit"] = events.location.map(ref.tracks.circuit)
        res = db.query("SELECT * FROM results") \
            .merge(sess[["season", "round", "session", "date_utc", "rain_prob", "temp_c"]],
                   on=["season", "round", "session"]) \
            .merge(events[["season", "round", "circuit"]], on=["season", "round"])
        res["kind"] = np.where(res.session.isin(QUALI_TYPE), "quali", "race")
        res["clean"] = (res.kind == "quali") | res.status.map(_finished)  # be gedimų / avarijų
        odds = db.query("SELECT season, round, session, market, driver, prob, price_ts, source FROM odds")
        return cls(sess, res, db.query("SELECT * FROM practice"), events, odds, settings, ref)

    # --- patogūs filtrai
    def session_rows(self, season, rnd, session=None):
        s = self.sess[(self.sess.season == season) & (self.sess["round"] == rnd)]
        return s if session is None else s[s.session == session]

    def results_of(self, season, rnd, session):
        return self.res[(self.res.season == season) & (self.res["round"] == rnd) & (self.res.session == session)]

    def top3(self, season, rnd, session):
        r = self.results_of(season, rnd, session).dropna(subset=["position"])
        return r.sort_values("position").head(3).driver.tolist()

    def event(self, season, rnd):
        return self.events[(self.events.season == season) & (self.events["round"] == rnd)].iloc[0]

    def done_sessions(self, seasons, types=COMPETITIVE, before=None, by_date=False):
        s = self.sess[self.sess.season.isin(seasons) & (self.sess.status == "ok") & self.sess.session.isin(types)]
        s = s[s.date_utc < before] if before else s
        return s.sort_values("date_utc") if by_date else s

    def next_session(self, now_iso):
        s = self.sess[(self.sess.season == SEASON) & (self.sess.status != "ok")
                      & self.sess.session.isin(COMPETITIVE) & (self.sess.date_utc >= now_iso)].sort_values("date_utc")
        return (int(s.iloc[0]["round"]), s.iloc[0]["session"]) if not s.empty else (None, None)

    def teams(self, season):
        """{vairuotojas: komanda} pagal naujausius sezono duomenis."""
        r = self.res[self.res.season == season].sort_values("date_utc")[["driver", "team"]]
        p = self.prac[self.prac.season == season].sort_values(["round", "session"])[["driver", "team"]]
        return {**dict(zip(p.driver, p.team)), **dict(zip(r.driver, r.team))}

    def entry_list(self, season, rnd, session):
        """Kurie vairuotojai dalyvaus sesijoje."""
        same = self.results_of(season, rnd, session)
        if not same.empty:
            return list(same.driver)
        wk_r = self.res[(self.res.season == season) & (self.res["round"] == rnd)]
        if not wk_r.empty:
            return sorted(set(wk_r.driver))
        wk_p = self.prac[(self.prac.season == season) & (self.prac["round"] == rnd)]
        if not wk_p.empty:  # tik treniruotės – paskutinės treniruotės dalyviai
            return sorted(set(wk_p[wk_p.session == wk_p.session.max()].driver))
        last = self.res[self.res.season == season]
        return sorted(set(last[last["round"] == last["round"].max()].driver))
