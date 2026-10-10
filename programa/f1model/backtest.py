"""Sezono atkūrimas: kiek taškų modelis būtų surinkęs, palyginti su žaidėjais.
Kiekvienai sesijai naudojami TIK iki jos žinomi duomenys (svoriai mokomi iš ankstesnių sesijų)."""
import pandas as pd

from . import model
from .config import SEASON


def run(data, picks=None, season=SEASON, progress=None):
    """picks – žaidėjų spėjimai (ExcelPicks.read) arba None (tik modelis)."""
    if picks is None:
        picks = pd.DataFrame(columns=["player", "round", "session", "pos", "predicted"])
    events = data.events[data.events.season == season]
    done = data.done_sessions([season], by_date=True)
    rows = []
    for i, (_, s) in enumerate(done.iterrows()):
        rnd, code = int(s["round"]), s.session
        actual = data.top3(season, rnd, code)
        out = model.predict(data, season, rnd, code, before=s.date_utc)
        row = dict(round=rnd, session=code, rezultatas=" ".join(actual), modelis=" ".join(out["pick"]),
                   Modelis=model.score(out["pick"], actual))
        for player, g in picks[(picks["round"] == rnd) & (picks.session == code)].groupby("player"):
            pred = g.sort_values("pos").predicted.tolist()
            if all(isinstance(x, str) for x in pred):
                row[player] = model.score(pred, actual)
        rows.append(row)
        if progress:
            progress((i + 1) / len(done))
    df = pd.DataFrame(rows)
    df.insert(0, "etapas", df["round"].map(events.set_index("round").name.str.replace(" Grand Prix", "")))
    return df


def score_columns(df, players):
    return [c for c in df.columns if c == "Modelis" or c in players]
