"""Sezono atkūrimas ir modelio vertinimas.

Kiekvienai įvykusiai sesijai spėjama TIK su iki jos žinomais duomenimis (svoriai mokomi iš ankstesnių
sesijų, orai – prognozė, lažybos – kainos prieš sesiją). Be taškų skaičiuojami tikimybių tikslumo
matai – jie daug stabilesni nei taškai, todėl pagal juos sprendžiama, ar pakeitimas tikrai pagerina
modelį (`compare` – porinis bootstrap: kiek kartų iš 10 000 atsitiktinių sesijų rinkinių naujas variantas
geresnis).
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import model
from .config import SEASON

EPS = 1e-3                  # mažiausia tikimybė (log-loss neperšoka į begalybę dėl Monte Carlo triukšmo)


@dataclass(frozen=True)
class Metric:
    column: str
    label: str
    higher_is_better: bool


METRICS = [Metric("Modelis", "taškai", True),
           Metric("logloss", "vietų log-loss", False),
           Metric("brier", "TOP3 Brier", False)]
PRIMARY = "logloss"


def session_metrics(table, actual):
    """table – spėjimo tikimybės (P1, P2, P3, TOP3 pagal vairuotoją); actual – tikras TOP3.
    logloss – vidutinis −ln P(tikras vairuotojas toje vietoje); brier – Σ (P(TOP3) − buvo TOP3)²."""
    p = [table[f"P{k + 1}"].get(d, 0.0) for k, d in enumerate(actual)]
    logloss = float(-np.mean(np.log(np.clip(p, EPS, 1.0))))
    hit = table.index.isin(actual).astype(float)
    missing = len(set(actual) - set(table.index))   # tikras TOP3 vairuotojas, kurio modelis nelaukė
    return logloss, float(((table.TOP3 - hit) ** 2).sum() + missing)


def run(data, picks=None, seasons=(SEASON,), progress=None):
    """picks – žaidėjų spėjimai (ExcelPicks.read; tik SEASON) arba None. Grąžina lentelę po sesiją."""
    if picks is None:
        picks = pd.DataFrame(columns=["player", "round", "session", "pos", "predicted"])
    done = data.done_sessions(list(seasons), by_date=True)
    rows = []
    for i, (_, s) in enumerate(done.iterrows()):
        season, rnd, code = int(s.season), int(s["round"]), s.session
        actual = data.top3(season, rnd, code)
        if len(actual) < 3:
            continue
        out = model.predict(data, season, rnd, code, before=s.date_utc)
        logloss, brier = session_metrics(out["table"], actual)
        row = dict(season=season, round=rnd, etapas=data.event(season, rnd)["name"].replace(" Grand Prix", ""),
                   session=code, rezultatas=" ".join(actual), modelis=" ".join(out["pick"]),
                   Modelis=model.score(out["pick"], actual), tiketini=round(out["expected"], 2),
                   logloss=round(logloss, 4), brier=round(brier, 4))
        if season == SEASON:
            for player, g in picks[(picks["round"] == rnd) & (picks.session == code)].groupby("player"):
                pred = g.sort_values("pos").predicted.tolist()
                if all(isinstance(x, str) for x in pred):
                    row[player] = model.score(pred, actual)
        rows.append(row)
        if progress:
            progress((i + 1) / len(done))
    return pd.DataFrame(rows)


def score_columns(df, players):
    return [c for c in df.columns if c == "Modelis" or c in players]


def summary(df):
    """{matas: reikšmė}: taškai iš viso ir per sesiją, tikėtini taškai, vidutiniai tikslumo matai."""
    n = len(df)
    return dict(sessions=n, points=int(df.Modelis.sum()), per_session=df.Modelis.mean() if n else 0.0,
                expected=df.tiketini.sum(), logloss=df.logloss.mean() if n else 0.0,
                brier=df.brier.mean() if n else 0.0)


def compare(base, new, n_boot=10000, seed=0):
    """Porinis bootstrap palyginimas (tos pačios sesijos abiejuose). Grąžina
    {stulpelis: (vidutinis pokytis, 95 % intervalas (nuo, iki), dalis atvejų, kai naujas geresnis)}."""
    keys = ["season", "round", "session"]
    m = base.merge(new, on=keys, suffixes=("_a", "_b"))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(m), size=(n_boot, len(m)))
    out = {}
    for metric in METRICS:
        d = (m[f"{metric.column}_b"] - m[f"{metric.column}_a"]).to_numpy(float)
        boot = d[idx].mean(axis=1)
        better = (boot > 0) if metric.higher_is_better else (boot < 0)
        out[metric.column] = (float(d.mean()), tuple(np.percentile(boot, [2.5, 97.5])), float(better.mean()))
    return out


def compare_text(result, n_sessions):
    lines = [f"Palyginta sesijų: {n_sessions}. Teigiama tikimybė = kiek bootstrap imčių naujas variantas geresnis."]
    for metric in METRICS:
        mean, (lo, hi), p = result[metric.column]
        lines.append(f"  {metric.label:<16} pokytis {mean:+.4f} per sesiją  (95 %: {lo:+.4f} .. {hi:+.4f})  "
                     f"geresnis {p:.0%}")
    return "\n".join(lines)
