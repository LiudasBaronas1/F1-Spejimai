"""Orai: trasos jutikliai (faktas) + Open-Meteo prognozė, kalibruota pagal tai, ar trasoje TIKRAI lijo.

1. TrackWeatherSource – FastF1 trasos jutikliai kiekvienoje įvykusioje sesijoje: kiek laiko lijo,
   oro ir trasos temperatūra. Tai „tiesa“ (orų modelių tinklelis tropikuose dažnai rodo lietų,
   kurio trasoje nėra).
2. WeatherSource – prognozės požymiai sesijos lange: lietaus tikimybė (trasoje ir regione), kritulių
   kiekis (trasoje ir regione ±1 val.), debesuotumas. Praeities sesijoms – istorinių prognozių
   archyvas (tokia prognozė, kokia buvo prieš sesiją), ateities – gyva prognozė.
3. Kalibravimas – logistinė regresija: prognozės požymiai -> P(trasoje lis). Mokoma iš visų sesijų,
   kurioms žinomas jutiklių faktas; rezultatas – duomenys/oru_kalibracija.json.

Galutinė `rain_prob`: įvykusiai sesijai – faktas iš jutiklių, kitaip – kalibruota prognozė.
"""
import json
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from ..config import DATA_DIR, SEASON
from . import DataSource, get_json, log

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
HISTORICAL_URL = "https://historical-forecast-api.open-meteo.com/v1/forecast"
CALIBRATION_FILE = DATA_DIR / "oru_kalibracija.json"
DURATION_H = {"FP1": 1, "FP2": 1, "FP3": 1, "SQ": 1, "S": 1, "Q": 1, "R": 2}
LIVE_DAYS = 60               # naujesnėms nei tiek dienų – gyvos prognozės API (su past_days)
REGION_KM, WINDOW_PAD_H = 15, 1
WET_FRAC = 0.3               # jei lijo ≥30 % sesijos laiko – sesija visiškai šlapia
WET_LABEL = 0.1              # kalibravimui: „lijo“, jei lietus ≥10 % sesijos laiko
L2 = 0.1                     # išbandyta 0.01–3: 0.1 mažiausia paklaida (kryžminis patikrinimas)
KEYS = ["season", "round", "session"]


def track_wetness(frac):
    return float(np.clip(frac / WET_FRAC, 0, 1))


def region_points(lat, lon):
    dlat = REGION_KM / 111.0
    dlon = REGION_KM / (111.0 * max(np.cos(np.radians(lat)), 0.2))
    return [(lat, lon), (lat + dlat, lon), (lat - dlat, lon), (lat, lon + dlon), (lat, lon - dlon)]


# ------------------------------------------------------------------ 1. trasos jutikliai

class TrackWeatherSource(DataSource):
    label = "trasos jutikliai"

    def update(self, season):
        import fastf1
        from fastf1 import _api
        from . import official  # noqa: F401 – įjungia FastF1 talpyklą
        done_before = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        todo = self.db.query("SELECT s.round, s.session FROM sessions s LEFT JOIN weather w USING(season, round, session) "
                        "WHERE s.season=? AND s.date_utc < ? AND w.track_rain_frac IS NULL", (season, done_before))
        if todo.empty:
            return
        schedule = fastf1.get_event_schedule(season, include_testing=False)  # vieną kartą per sezoną
        for _, s in todo.iterrows():
            try:
                session = schedule.get_event_by_round(int(s["round"])).get_session(s.session)
                w = pd.DataFrame(_api.weather_data(session.api_path))
            except Exception as e:
                if "calls" in str(e):  # FastF1 užklausų limitas – tęsime kitą kartą
                    log.info("Trasos jutikliai: užklausų limitas, tęsiama vėliau")
                    return
                continue
            if w.empty:
                continue
            self.db.write("weather", [dict(season=season, round=int(s["round"]), session=s.session,
                                               track_rain_frac=float(w.Rainfall.astype(bool).mean()),
                                               track_air_c=float(w.AirTemp.astype(float).mean()),
                                               track_temp_c=float(w.TrackTemp.astype(float).mean()))], KEYS)


# ------------------------------------------------------------------ 2. prognozės požymiai

def fetch(points, start, end, live):
    js = get_json(FORECAST_URL if live else HISTORICAL_URL, dict(
        latitude=",".join(f"{p[0]:.4f}" for p in points), longitude=",".join(f"{p[1]:.4f}" for p in points),
        start_date=str(start), end_date=str(end), timezone="UTC",
        hourly="precipitation,precipitation_probability,cloud_cover,temperature_2m"))
    return [pd.DataFrame(j["hourly"]).assign(time=lambda h: pd.to_datetime(h.time, utc=True)).set_index("time")
            for j in (js if isinstance(js, list) else [js])]


def forecast_features(points, start, hours):
    s = pd.Timestamp(start).floor("h")
    core = slice(s, s + pd.Timedelta(hours=hours))
    wide = slice(s - pd.Timedelta(hours=WINDOW_PAD_H), s + pd.Timedelta(hours=hours + WINDOW_PAD_H))
    c = points[0].loc[core]
    if c.empty:
        return None
    pop = lambda h: float(h["precipitation_probability"].max()) / 100 if h["precipitation_probability"].notna().any() else 0.0
    return dict(fc_pop=pop(c), fc_pop_region=max(pop(h.loc[wide]) for h in points),
                fc_precip=float(c.precipitation.fillna(0).sum()), fc_cloud=float(c.cloud_cover.mean()) / 100,
                region_rain_mm=float(np.mean([h.loc[wide, "precipitation"].fillna(0).sum() for h in points])),
                temp_c=float(c.temperature_2m.mean()))


# ------------------------------------------------------------------ 3. kalibravimas

def design(df):
    """Prognozės požymiai -> matrica logistinei regresijai."""
    return np.column_stack([np.ones(len(df)), df.fc_pop, df.fc_pop_region, np.log1p(df.fc_precip),
                            np.log1p(df.region_rain_mm), df.fc_cloud])


def naive_prob(df):
    """Ankstesnis metodas (palyginimui): 60 % trasos + 40 % regiono didžiausios tikimybės."""
    return 0.6 * df.fc_pop + 0.4 * df.fc_pop_region


def _fit_logistic(X, y):
    def loss(b):
        z = X @ b
        return np.sum(np.logaddexp(0, z) - y * z) + L2 * b[1:] @ b[1:]
    return minimize(loss, np.zeros(X.shape[1]), method="L-BFGS-B").x


def _sigmoid(z):
    return 1 / (1 + np.exp(-z))


def calibrate(db, path=CALIBRATION_FILE):
    """Išmoko P(lietus trasoje | prognozė) ir įvertina tikslumą (palikus po vieną sezoną testui)."""
    d = db.query("SELECT * FROM weather WHERE track_rain_frac IS NOT NULL AND fc_pop IS NOT NULL "
                 "AND region_rain_mm IS NOT NULL").fillna({"fc_precip": 0, "fc_cloud": 0.5})
    if len(d) < 50 or (d.track_rain_frac >= WET_LABEL).sum() < 5:
        return None
    y = (d.track_rain_frac >= WET_LABEL).astype(float).values
    cv = np.zeros(len(d))
    for season in d.season.unique():  # kryžminis patikrinimas: kiekvienas sezonas – testinis
        test = (d.season == season).values
        cv[test] = _sigmoid(design(d[test]) @ _fit_logistic(design(d[~test]), y[~test]))
    brier = lambda p: float(np.mean((p - y) ** 2))
    result = dict(coef=_fit_logistic(design(d), y).tolist(), sessions=int(len(d)), wet_sessions=int(y.sum()),
                  brier_new=brier(cv), brier_old=brier(naive_prob(d).values), brier_base=brier(np.full(len(y), y.mean())),
                  fitted_at=datetime.now().isoformat(timespec="minutes"))
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    log.info("Orų kalibravimas: %s sesijų (%s lietingų); Brier %.3f (anksčiau %.3f)", result["sessions"],
             result["wet_sessions"], result["brier_new"], result["brier_old"])
    return result


def calibrated_prob(df, path=CALIBRATION_FILE):
    if path.exists():
        coef = np.array(json.loads(path.read_text(encoding="utf-8"))["coef"])
        return _sigmoid(design(df) @ coef)
    return naive_prob(df).values


# ------------------------------------------------------------------ šaltinis

class WeatherSource(DataSource):
    label = "regiono orai"

    def update(self, season, force=False):
        now = datetime.now(timezone.utc)
        loc = self.db.query("SELECT round, location FROM events WHERE season=?", (season,)).set_index("round").location
        sess = self.db.query("SELECT s.round, s.session, s.date_utc, w.fc_pop, w.track_rain_frac FROM sessions s "
                        "LEFT JOIN weather w USING(season, round, session) WHERE s.season=?", (season,))
        for rnd, g in sess[sess.session.isin(DURATION_H)].groupby("round"):
            starts = pd.to_datetime(g.date_utc, utc=True, format="ISO8601")
            live = starts.max() > now - timedelta(days=LIVE_DAYS)
            need = g if (force or live) else g[g.fc_pop.isna()]   # senų etapų prognozė nekinta
            coords = self.ref.tracks.coords(loc.get(rnd, ""))
            if need.empty or starts.min() > now + timedelta(days=15) or coords is None:
                continue
            try:
                points = fetch(region_points(*coords), (starts.min() - timedelta(hours=2)).date(),
                               (starts.max() + timedelta(hours=4)).date(), live)
            except Exception as e:  # vieno etapo klaida nestabdo kitų
                log.warning("Orai %s R%s: %s", season, rnd, e)
                continue
            rows = [dict(season=season, round=int(rnd), session=s.session, fetched_at=now.isoformat(), **f)
                    for _, s in need.iterrows() if (f := forecast_features(points, s.date_utc, DURATION_H[s.session]))]
            self.db.write("weather", rows, KEYS)
        if season == SEASON:
            calibrate(self.db)
        finalize(self.db, season)


def finalize(db, season, path=CALIBRATION_FILE):
    """Galutinė lietaus tikimybė ir temperatūra: faktas iš jutiklių, jei yra, kitaip – kalibruota prognozė."""
    w = db.query("SELECT * FROM weather WHERE season=?", (season,))
    if w.empty:
        return
    has_fc = w.fc_pop.notna() & w.region_rain_mm.notna()
    prob = pd.Series(np.nan, index=w.index)
    prob[has_fc] = calibrated_prob(w[has_fc].fillna({"fc_precip": 0, "fc_cloud": 0.5}), path)
    fact = w.track_rain_frac.notna()
    w["rain_prob"] = np.where(fact, w.track_rain_frac.fillna(0).map(track_wetness), prob)
    w["rain_mm"] = w.fc_precip
    w["temp_c"] = w.track_air_c.where(fact, w.temp_c)
    w["source"] = np.where(fact, "trasos jutikliai", "prognozė")
    db.write("weather", w[KEYS + ["rain_prob", "rain_mm", "temp_c", "source"]].to_dict("records"), KEYS)
