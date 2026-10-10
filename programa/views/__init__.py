"""Programos puslapiai (meniu kairėje). Kiekvienas puslapis – atskiras modulis su funkcija `render(c)`.

Puslapiai gauna `Ctx` – siaurą sąsają į programą (duomenys, modelis, vertėjas ir kelios operacijos).
Tiesiogiai į duomenų bazę ar `App` puslapiai nesikreipia, todėl juos lengva keisti ir tikrinti.
NAUJAS PUSLAPIS = naujas modulis su render(c) + įrašas PAGES + vertimas „nav.<raktas>“."""
from dataclasses import dataclass
from functools import cached_property
from typing import Callable

from f1model import backtest, features, model, status


@dataclass
class Ctx:
    app: object                       # f1model.app.App (naudojamas tik šios klasės metoduose)
    t: object                         # Translator
    data: object                      # Dataset
    fitted: dict                      # {"quali"/"race": (svoriai, imčių sk.)}
    weights_before: Callable          # (rūšis, iki) -> svoriai; mokant rodomas eigos skydelis
    request_update: Callable          # paleidžia duomenų atnaujinimą

    # --- dažnai naudojami
    @property
    def S(self):
        return self.data.settings

    @property
    def ref(self):
        return self.data.ref

    @cached_property
    def session_names(self):
        return self.t.prefixed("session", ["FP1", "FP2", "FP3", "SQ", "S", "Q", "R"])

    @cached_property
    def labels(self):
        return {f: self.t.get(f"feature.{f}.label", x.label) for f, x in features.REGISTRY.items()}

    @cached_property
    def briefing(self):
        return self.app.briefing()

    @cached_property
    def track_info(self):
        return self.app.track_info(self.data)

    @property
    def has_excel(self):
        return self.app.has_excel

    # --- operacijos
    def track_outline(self, circuit):
        return self.app.track_outline(circuit)

    def checks(self, season, rnd, session):
        return status.weekend_checks(self.data, self.app.db, season, rnd, session)

    def save_prediction(self, season, rnd, session, out):
        ev = self.data.event(season, rnd)
        model.save_prediction(self.app.db, season, rnd, session, out)
        self.app.write_report(self.data, self.fitted, last=(ev["name"], session, out, ev.circuit))

    def run_backtest(self, season, players_season, progress):
        fresh = self.app.dataset()
        picks = self.app.excel().read(fresh.events[fresh.events.season == season]) if players_season else None
        return backtest.run(fresh, picks, season=season, progress=progress)

    def report_text(self, refresh=False):
        if refresh or not self.app.report_path.exists():
            self.app.write_report(self.data, self.fitted)
        return self.app.report_path.read_text(encoding="utf-8")

    def save_settings(self):
        self.app.save_settings()

    def reference_rows(self, table):
        return self.app.db.query(f"SELECT * FROM {table}")

    def save_reference(self, table, rows):
        self.app.save_reference(table, rows)

    def default_reference_rows(self, table):
        return self.app.default_rows(table)


def pages():
    """[(raktas, render)] – meniu tvarka; pirmas – numatytasis."""
    from . import data_status, model_info, news, next_session, season, weekend
    return [("next", next_session.render), ("weekend", weekend.render), ("season", season.render),
            ("news", news.render), ("model", model_info.render), ("data", data_status.render)]
