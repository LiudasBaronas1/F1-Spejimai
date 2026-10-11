"""Komandinė eilutė (pagrindinė programa – „F1 Spėjimai“ nuoroda / F1 Spėjimai.vbs).

    .venv\\Scripts\\python cli.py spejimas [etapas sesija]   artimiausios (ar nurodytos) sesijos spėjimas
    .venv\\Scripts\\python cli.py testas [metai ...]          sezono atkūrimas: taškai, tikslumas, žaidėjai
    .venv\\Scripts\\python cli.py palyginti [nustatymai]      ar pakeitimas pagerina modelį (porinis bootstrap)
    .venv\\Scripts\\python cli.py atnaujinti [metai ...]      duomenų atnaujinimas (pvz. 2024 2023)
    .venv\\Scripts\\python cli.py automatinis                 spėjimas prieš artėjančią sesiją (užduočių planuoklis)

Pavyzdžiai: cli.py palyginti forma_pusejimo_sesijos=5       cli.py palyginti --be market_top5 --metai 2025 2026
"""
import argparse
import json
import logging
import sys
from datetime import datetime, timedelta, timezone

import pandas as pd

from f1model import automation, backtest, features, settings
from f1model.app import App
from f1model.config import DATA_DIR, SEASON, SESSION_NAMES_LT


def cmd_spejimas(app, args):
    app.update(SEASON)
    data = app.dataset()
    rnd, session = (args.etapas, args.sesija.upper()) if args.etapas else \
        data.next_session((datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat())
    if rnd is None:
        return print("Neradau artėjančios sesijos.")
    fitted = app.train(data)
    out = app.predict(data, fitted, SEASON, rnd, session)
    app.publish(data, fitted, SEASON, rnd, session, out)
    ev = data.event(SEASON, rnd)
    names = data.settings.active(features.names())
    print(f"\n=== {ev['name']} ({ev.circuit}) – {SESSION_NAMES_LT[session]} · lietus {out['rain']:.0%} ===\n")
    print(f"{'':<5}{'P1':>6}{'P2':>6}{'P3':>6}{'TOP3':>6}{'DNF':>6}  "
          + "".join(f"{features.REGISTRY[f].short:>8}" for f in names))
    for d, r in out["table"].head(10).iterrows():
        print(f"{d:<5}" + "".join(f"{r[c]:>6.0%}" for c in ("P1", "P2", "P3", "TOP3", "DNF")) + "  "
              + "".join(f"{r[f]:>+8.1f}" for f in names))
    print("\nSIŪLOMAS SPĖJIMAS: " + " – ".join(out["pick"]) + f"   (tikėtini taškai {out['expected']:.2f} iš 6)")


def print_summary(title, df):
    s = backtest.summary(df)
    print(f"{title}: {s['points']} tšk. per {s['sessions']} sesijų ({s['per_session']:.2f}/sesiją), tikėtini "
          f"{s['expected']:.0f}; vietų log-loss {s['logloss']:.4f}, TOP3 Brier {s['brier']:.4f}")


def cmd_testas(app, args):
    data = app.dataset()
    seasons = args.metai or [SEASON]
    picks = app.excel().read(data.events[data.events.season == SEASON]) if SEASON in seasons else None
    df = backtest.run(data, picks, seasons=seasons)
    pd.set_option("display.width", 220)
    print(df.drop(columns=["round"]).to_string(index=False))
    print("\nIŠ VISO:\n" + df[backtest.score_columns(df, data.ref.players)].sum().sort_values(ascending=False).to_string())
    print()
    print_summary("Modelis", df)
    app.write_report(data, app.train(data))


def variant_settings(base, assignments, disabled):
    """parametrai.json raktai (arba Settings laukai) „raktas=reikšmė“ (reikšmė – JSON) -> nauji Settings."""
    values = {}
    for a in assignments:
        key, _, raw = a.partition("=")
        field = settings.field_name(key)
        if field is None:
            raise SystemExit(f"Nežinomas nustatymas: {key}")
        try:
            values[field] = json.loads(raw)
        except ValueError:
            values[field] = raw
    if disabled:
        unknown = set(disabled) - set(features.names())
        if unknown:
            raise SystemExit(f"Nežinomi požymiai: {', '.join(sorted(unknown))}")
        values["disabled"] = sorted(set(base.disabled) | set(disabled))
    return base.with_values(**values)


def cmd_palyginti(app, args):
    data = app.dataset()
    variant = data.with_settings(variant_settings(data.settings, args.nustatymai, args.be))
    seasons = args.metai or [SEASON - 1, SEASON]
    print(f"Skaičiuoju dabartinį modelį ir variantą ({', '.join(map(str, seasons))})...")
    a = backtest.run(data, seasons=seasons)
    b = backtest.run(variant, seasons=seasons)
    print_summary("Dabartinis", a)
    print_summary("Variantas ", b)
    result = backtest.compare(a, b)
    print(backtest.compare_text(result, len(a)))
    print(f"Sprendimas pagal pagrindinį matą ({backtest.PRIMARY}): variantas geresnis "
          f"{result[backtest.PRIMARY][2]:.0%} atvejų (verta keisti, jei ≥ 95 %).")


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
    sub.add_parser("testas").add_argument("metai", type=int, nargs="*")
    c = sub.add_parser("palyginti")
    c.add_argument("nustatymai", nargs="*", help="raktas=reikšmė (parametrai.json raktai)")
    c.add_argument("--be", nargs="*", default=[], help="išjungti požymiai")
    c.add_argument("--metai", type=int, nargs="*")
    sub.add_parser("atnaujinti").add_argument("metai", type=int, nargs="*")
    sub.add_parser("automatinis")
    args = p.parse_args()
    # automatinis režimas veikia be lango – rašome į žurnalą
    DATA_DIR.mkdir(parents=True, exist_ok=True)
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
