"""Komandinė eilutė (pagrindinė programa – „F1 Spėjimai“ nuoroda / F1 Spėjimai.vbs).

    .venv\\Scripts\\python cli.py spejimas [etapas sesija]   artimiausios (ar nurodytos) sesijos spėjimas
    .venv\\Scripts\\python cli.py testas                      sezono atkūrimas prieš žaidėjus
    .venv\\Scripts\\python cli.py atnaujinti [metai ...]      duomenų atnaujinimas (pvz. 2024 2023)
    .venv\\Scripts\\python cli.py automatinis                 spėjimas prieš artėjančią sesiją (užduočių planuoklis)
"""
import argparse
import logging
import sys
from datetime import datetime, timedelta, timezone

import pandas as pd

from f1model import automation, backtest, features, model, report
from f1model.app import App
from f1model.config import DATA_DIR, SEASON, SESSION_NAMES_LT
from f1model.dataset import kind_of


def cmd_spejimas(app, args):
    app.update(SEASON)
    data = app.dataset()
    rnd, session = (args.etapas, args.sesija.upper()) if args.etapas else \
        data.next_session((datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat())
    if rnd is None:
        return print("Neradau artėjančios sesijos.")
    fitted = model.fit_all(data)
    model.save_weights(app.db, fitted)
    out = model.predict(data, SEASON, rnd, session, weights=fitted[kind_of(session)][0])
    model.save_prediction(app.db, SEASON, rnd, session, out)
    ev = data.event(SEASON, rnd)
    report.write(app.report_path, data, fitted, last=(ev["name"], session, out, ev.circuit))
    names = features.names()
    print(f"\n=== {ev['name']} ({ev.circuit}) – {SESSION_NAMES_LT[session]} · lietus {out['rain']:.0%} ===\n")
    print(f"{'':<5}{'P1':>6}{'P2':>6}{'P3':>6}{'TOP3':>6}  " + "".join(f"{features.REGISTRY[f].short:>8}" for f in names))
    for d, r in out["table"].head(10).iterrows():
        print(f"{d:<5}" + "".join(f"{r[c]:>6.0%}" for c in ("P1", "P2", "P3", "TOP3")) + "  "
              + "".join(f"{r[f]:>+8.1f}" for f in names))
    print("\nSIŪLOMAS SPĖJIMAS: " + " – ".join(out["pick"]) + f"   (tikėtini taškai {out['expected']:.2f} iš 6)")


def cmd_testas(app, args):
    data = app.dataset()
    df = backtest.run(data, app.excel().read(data.events[data.events.season == SEASON]))
    pd.set_option("display.width", 200)
    print(df.drop(columns="round").to_string(index=False))
    print("\nIŠ VISO:\n" + df[backtest.score_columns(df, data.ref.players)].sum().sort_values(ascending=False).to_string())
    report.write(app.report_path, data, model.fit_all(data))


def cmd_atnaujinti(app, args):
    for season in args.metai or [SEASON]:
        app.update(season)


def cmd_automatinis(app, args):
    automation.run(app)


def main():
    p = argparse.ArgumentParser(description="F1 spėjimų modelis")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("spejimas")
    s.add_argument("etapas", type=int, nargs="?")
    s.add_argument("sesija", nargs="?", default="R", help="SQ, S, Q arba R")
    sub.add_parser("testas")
    sub.add_parser("atnaujinti").add_argument("metai", type=int, nargs="*")
    sub.add_parser("automatinis")
    args = p.parse_args()
    # automatinis režimas veikia be lango – rašome į žurnalą
    target = dict(filename=DATA_DIR / "automatinis.log", encoding="utf-8") if args.cmd == "automatinis" \
        else dict(stream=sys.stdout)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S", **target)
    try:
        globals()[f"cmd_{args.cmd}"](App.create(), args)
    except Exception:
        logging.exception("Klaida")
        raise


if __name__ == "__main__":
    main()
