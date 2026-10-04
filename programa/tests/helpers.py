"""Testų pagalbinės priemonės: laikina duomenų bazė ir sintetinis sezonas."""
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from f1model.app import App

DRIVERS = ["AAA", "BBB", "CCC", "DDD", "EEE", "FFF", "GGG", "HHH"]   # AAA – stipriausias


def temp_app():
    """App su laikinais failais (tikri duomenys nepaliečiami). Grąžina (app, tmp katalogas)."""
    tmp = Path(tempfile.mkdtemp(prefix="f1test_"))
    return App.create(db_path=tmp / "f1.db", params_path=tmp / "parametrai.json",
                      report_path=tmp / "PARAMETRAI.md", excel_path=tmp / "nera.xlsx", starter_dir=None), tmp


def synthetic_season(db, season=2026, rounds=8, noise=None):
    """Sukuria `rounds` įvykusių etapų (Q ir R), kuriuose vairuotojai finišuoja DRIVERS tvarka
    (su nedideliais sukeitimais pagal `noise`), ir vieną artėjantį etapą."""
    start = datetime(season, 3, 1, tzinfo=timezone.utc)
    events, sessions, results = [], [], []
    for rnd in range(1, rounds + 2):
        day = start + timedelta(days=14 * rnd)
        events.append(dict(season=season, round=rnd, name=f"Test {rnd} Grand Prix", country="X", location="Monza",
                           date=str(day.date()), format="conventional"))
        done = rnd <= rounds
        for code, hours in (("Q", 0), ("R", 24)):
            sessions.append(dict(season=season, round=rnd, session=code,
                                 date_utc=(day + timedelta(hours=hours)).isoformat(), status="ok" if done else "pending"))
            if done:
                order = list(DRIVERS)
                if noise and rnd % noise == 0:  # kartais du lyderiai susikeičia vietomis
                    order[0], order[1] = order[1], order[0]
                results += [dict(season=season, round=rnd, session=code, driver=d, team="Team " + d[0],
                                 position=i + 1, official_position=i + 1, grid=i + 1, status="Finished")
                            for i, d in enumerate(order)]
    db.write("events", events)
    db.write("sessions", sessions)
    db.write("results", results)
