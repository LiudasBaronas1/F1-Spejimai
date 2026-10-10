import json
import unittest

import numpy as np
import pandas as pd

from f1model import app, features, reference, settings
from f1model.sources import official, weather
from tests.helpers import temp_app


class DatabaseTest(unittest.TestCase):
    def setUp(self):
        self.app, self.tmp = temp_app()
        self.db = self.app.db

    def test_merge_keeps_other_columns(self):
        key = dict(season=2026, round=1, session="Q")
        self.db.write("weather", [dict(**key, track_rain_frac=0.5)], keys=["season", "round", "session"])
        self.db.write("weather", [dict(**key, fc_pop=0.7)], keys=["season", "round", "session"])
        row = self.db.query("SELECT track_rain_frac, fc_pop FROM weather").iloc[0]
        self.assertEqual((row.track_rain_frac, row.fc_pop), (0.5, 0.7))

    def test_reference_tables_seeded_once(self):
        self.db.execute("DELETE FROM komandos WHERE raktazodis='haas'")
        reference.seed(self.db)  # netuščios lentelės neperrašomos
        self.assertNotIn("haas", [k for k, _ in self.app.reference().team_colors])

    def test_starter_data_copied_only_once(self):
        starter = self.tmp / "start"
        starter.mkdir()
        (starter / "f1.db").write_bytes(self.db.path.read_bytes())
        target, cal = self.tmp / "naujas" / "f1.db", self.tmp / "naujas" / "oru_kalibracija.json"
        app.install_starter_data(starter, target, cal)
        self.assertTrue(target.exists())
        target.write_bytes(b"pakeista")
        app.install_starter_data(starter, target, cal)  # esami vartotojo duomenys neperrašomi
        self.assertEqual(target.read_bytes(), b"pakeista")


class CompositionTest(unittest.TestCase):
    def test_sources_get_injected_dependencies(self):
        app, tmp = temp_app()
        srcs = {type(s).__name__: s for s in app.sources()}
        fia_docs = {id(srcs[n].docs) for n in ("UpgradeSource", "GridSource", "ClassificationSource")}
        self.assertEqual(len(fia_docs), 1)                                   # viena bendra FIA rodyklė
        self.assertEqual(srcs["WeatherSource"].calibration_path, tmp / "oru_kalibracija.json")
        self.assertEqual(srcs["TrackMapSource"].cache_dir, tmp / "fastf1_cache")
        self.assertTrue(all(s.expected_s > 0 for s in srcs.values()))

    def test_report_written_to_injected_path(self):
        from tests.helpers import synthetic_season
        from f1model import model
        app, tmp = temp_app()
        synthetic_season(app.db, rounds=6)
        data = app.dataset()
        app.write_report(data, model.fit_all(data))
        self.assertIn("Modelio parametrai", (tmp / "PARAMETRAI.md").read_text(encoding="utf-8"))


class ReferenceTest(unittest.TestCase):
    def setUp(self):
        self.ref = temp_app()[0].reference()

    def test_similarity(self):
        t = self.ref.tracks
        self.assertAlmostEqual(t.similarity("Monza", "Monza"), 1.0)
        self.assertAlmostEqual(t.similarity("Monza", "Monaco"), t.similarity("Monaco", "Monza"))
        self.assertLess(t.similarity("Monza", "Monaco"), t.similarity("Monza", "Spa-Francorchamps"))
        self.assertEqual(t.circuit("Monte Carlo"), "Monaco")
        self.assertEqual(t.overtaking("Monte Carlo"), 5)
        self.assertEqual(t.character("Monte Carlo")["lenkimo_sunkumas"], 5)

    def test_team_colors_and_reference_lists(self):
        self.assertEqual(self.ref.team_color("Red Bull Racing"), "#3671C6")
        self.assertEqual(self.ref.team_color("Nežinoma"), "#888888")
        self.assertEqual(self.ref.players, [])          # žaidėjų sąrašas – tik vartotojo įrašytas
        self.assertEqual(self.ref.driver_names["ZHOU"], "ZHO")


class SettingsTest(unittest.TestCase):
    def test_missing_keys_are_added_and_values_kept(self):
        _, tmp = temp_app()
        path = tmp / "p.json"
        path.write_text(json.dumps({"pozymiu_daugikliai": {"pace": 0.5}, "nustatymai": {"reguliarizacija": 0.3}}))
        s = settings.load(path, features.names())
        self.assertEqual((s.multiplier("pace"), s.l2), (0.5, 0.3))
        saved = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(set(saved["pozymiu_daugikliai"]), set(features.names()))
        self.assertEqual(saved["pozymiu_daugikliai"]["pace"], 0.5)


class FeatureHelpersTest(unittest.TestCase):
    def test_combine_sources_uses_weights_and_fallback(self):
        S = settings.Settings(market_min_drivers=2)
        o = pd.DataFrame(dict(source=["kalshi", "kalshi", "polymarket", "polymarket", "bookmakers", "bookmakers"],
                              driver=["A", "B"] * 3, prob=[0.6, 0.4, 0.3, 0.7, 0.9, 0.1]))
        comb = features.combine_sources(o, ["A", "B"], S)
        self.assertAlmostEqual(comb["A"], (0.6 * 1.0 + 0.3 * 0.5) / 1.5)   # lažybininkai (svoris 0) neįtraukti
        only_books = features.combine_sources(o[o.source == "bookmakers"], ["A", "B"], S)
        self.assertAlmostEqual(only_books["A"], 0.9)                          # bet naudojami, kai kitų nėra

    def test_z_score_handles_missing(self):
        z = features._z(pd.Series([1.0, 2.0, 3.0, np.nan]))
        self.assertEqual(z.iloc[3], 0.0)
        self.assertAlmostEqual(z.iloc[:3].mean(), 0.0)


class OfficialDataTest(unittest.TestCase):
    def test_on_track_order_ignores_penalties(self):
        laps = pd.DataFrame(dict(Driver=["A", "B", "C", "A", "B"], LapNumber=[1, 1, 1, 2, 2],
                                 Time=pd.to_timedelta([90, 91, 92, 181, 180], unit="s")))
        self.assertEqual(official.on_track_order(laps), ["B", "A", "C"])  # C nepabaigė 2 rato

    def test_knockout_classification(self):
        t = lambda m: pd.Timedelta(minutes=m)
        laps = pd.DataFrame(dict(
            Driver=["A", "B", "C", "A", "B"],
            LapStartTime=[t(0), t(1), t(2), t(20), t(21)],          # pertrauka -> Q2, kur liko A ir B
            LapTime=[pd.Timedelta(seconds=s) for s in (80, 79, 78, 77, 76)]))
        self.assertEqual(official.knockout_classification(laps), ["B", "A", "C"])


class WeatherTest(unittest.TestCase):
    def test_track_wetness(self):
        self.assertEqual(weather.track_wetness(0.0), 0.0)
        self.assertEqual(weather.track_wetness(0.6), 1.0)

    def test_calibration_learns_from_rain_amount(self):
        app, tmp = temp_app()
        rng = np.random.default_rng(1)
        rows = []
        for i in range(200):
            wet = i % 5 == 0
            rows.append(dict(season=2023 + i % 3, round=i, session="R", track_rain_frac=0.5 if wet else 0.0,
                             fc_pop=rng.uniform(0.3, 0.9), fc_pop_region=rng.uniform(0.3, 0.9),
                             fc_precip=rng.uniform(1, 4) if wet else 0.0, fc_cloud=0.9 if wet else 0.3,
                             region_rain_mm=rng.uniform(2, 6) if wet else rng.uniform(0, 0.3)))
        app.db.write("weather", rows)
        cal_path = tmp / "kalibracija.json"
        result = weather.calibrate(app.db, cal_path)
        self.assertLess(result["brier_new"], result["brier_base"])
        df = pd.DataFrame([dict(fc_pop=0.7, fc_pop_region=0.7, fc_precip=f, fc_cloud=c, region_rain_mm=r)
                           for f, c, r in ((0.0, 0.3, 0.1), (3.0, 0.9, 5.0))])
        dry, wet = weather.calibrated_prob(df, cal_path)
        self.assertLess(dry, 0.2)
        self.assertGreater(wet, 0.8)


if __name__ == "__main__":
    unittest.main()
