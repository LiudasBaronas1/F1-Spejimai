import unittest

import numpy as np
import pandas as pd

from f1model import backtest, features, model
from tests.helpers import DRIVERS, synthetic_season, temp_app


class ScoringTest(unittest.TestCase):
    def test_rules_from_game(self):
        # taisyklių pavyzdys: žaidėjas P1 Ver, P2 Pia, P3 Rus; rezultatas Ver, Rus, Pia -> 2 + 1 + 1
        self.assertEqual(model.score(["VER", "PIA", "RUS"], ["VER", "RUS", "PIA"]), 4)
        self.assertEqual(model.score(["VER", "SAI", "PIA"], ["VER", "RUS", "PIA"]), 4)
        self.assertEqual(model.score(["A", "B", "C"], ["A", "B", "C"]), 6)
        self.assertEqual(model.score(["X", "Y", "Z"], ["A", "B", "C"]), 0)

    def test_best_pick_maximises_expected_points(self):
        probs = np.array([[0.6, 0.2, 0.1], [0.2, 0.5, 0.2], [0.1, 0.2, 0.4], [0.1, 0.1, 0.3]])
        pick, value = model.best_pick(probs, ["A", "B", "C", "D"])
        self.assertEqual(pick, ["A", "B", "C"])
        self.assertAlmostEqual(value, (0.9 + 0.6) + (0.9 + 0.5) + (0.7 + 0.4))

    def test_simulation_probabilities_are_valid(self):
        probs = model.simulate(np.array([2.0, 1.0, 0.0, -1.0]), n=5000)
        np.testing.assert_allclose(probs.sum(axis=0), 1.0)            # kiekvienoje vietoje – vienas vairuotojas
        self.assertTrue((probs.sum(axis=1) <= 1.0 + 1e-9).all())      # vairuotojas užima ne daugiau kaip vieną vietą
        self.assertGreater(probs[0, 0], probs[1, 0])                   # stipresnis dažniau laimi

    def test_dnf_lowers_chances(self):
        theta = np.array([2.0, 1.0, 0.0, -1.0, -1.0])
        base = model.simulate(theta, n=20000)
        dnf = model.simulate(theta, n=20000, dnf=np.array([0.5, 0, 0, 0, 0]))
        self.assertAlmostEqual(dnf[0].sum(), 0.5 * base[0].sum(), delta=0.03)   # pusę kartų nefinišuoja
        self.assertGreater(dnf[1, 0], base[1, 0])                               # kiti laimi dažniau
        np.testing.assert_allclose(dnf.sum(axis=0), 1.0)

    def test_sprint_and_rain_scale(self):
        m = model.KindModel({}, 0, chaos=0.4, sprint=0.8)
        self.assertAlmostEqual(m.scale("R", 0.0), 1.0)
        self.assertAlmostEqual(m.scale("S", 0.5), 0.8 * 0.8)


class MetricsTest(unittest.TestCase):
    def table(self):
        return pd.DataFrame(dict(P1=[0.7, 0.2, 0.1], P2=[0.2, 0.6, 0.2], P3=[0.1, 0.2, 0.7],
                                 TOP3=[1.0, 1.0, 1.0]), index=["A", "B", "C"])

    def test_session_metrics(self):
        ll, brier = backtest.session_metrics(self.table(), ["A", "B", "C"])
        self.assertAlmostEqual(ll, -np.mean(np.log([0.7, 0.6, 0.7])))
        self.assertAlmostEqual(brier, 0.0)
        ll2, brier2 = backtest.session_metrics(self.table(), ["X", "B", "C"])  # nelauktas vairuotojas
        self.assertGreater(ll2, ll)
        self.assertAlmostEqual(brier2, 1.0 + 1.0)                                # A ne TOP3 + X trūksta

    def test_compare_detects_clear_improvement(self):
        rng = np.random.default_rng(0)
        base = pd.DataFrame(dict(season=2026, round=range(40), session="R", Modelis=rng.integers(0, 6, 40),
                                 logloss=rng.uniform(1.5, 2.5, 40), brier=rng.uniform(1, 2, 40)))
        better = base.assign(logloss=base.logloss - 0.2)
        mean, (lo, hi), p = backtest.compare(base, better)["logloss"]
        self.assertAlmostEqual(mean, -0.2)
        self.assertLess(hi, 0)
        self.assertEqual(p, 1.0)
        self.assertEqual(backtest.compare(base, base)["Modelis"][2], 0.0)       # vienodi – ne geresnis


class EndToEndTest(unittest.TestCase):
    """Visas kelias su TESTINE duomenų baze: App -> Dataset -> mokymas -> spėjimas -> vertinimas."""

    @classmethod
    def setUpClass(cls):
        cls.app, cls.tmp = temp_app()
        synthetic_season(cls.app.db, noise=4)
        cls.data = cls.app.dataset()

    def test_learns_that_form_matters_and_predicts_leaders(self):
        fitted = self.app.train(self.data)
        self.assertGreater(fitted["race"].weights["weekend"] + fitted["race"].weights["form"], 0)
        out = self.app.predict(self.data, fitted, 2026, 9, "Q")
        self.assertEqual(out["pick"][0], "AAA")
        self.assertEqual(set(out["pick"]), set(DRIVERS[:3]))
        self.assertTrue(0 < out["expected"] <= 6)
        self.assertEqual(list(out["contrib"].index), list(out["table"].index))   # indėliai – ta pati tvarka
        saved = self.app.db.query("SELECT kind, name FROM model_params WHERE name='_sprinto_daugiklis'")
        self.assertEqual(sorted(saved.kind), ["quali", "race"])

    def test_prediction_tables_can_be_reshaped(self):
        # sąsajos grafikas daro melt(); anksčiau X.attrs (lentelės) perėjo į rezultatą ir melt() lūždavo
        out = model.predict(self.data, 2026, 9, "R")
        self.assertEqual(out["contrib"].attrs, {})
        self.assertEqual(out["table"].attrs, {})
        long = out["contrib"].head(8).reset_index(names="d").melt("d", var_name="f", value_name="v")
        self.assertEqual(len(long), 8 * out["contrib"].shape[1])

    def test_disabled_feature_is_not_used(self):
        data = self.data.with_settings(self.data.settings.with_values(disabled=["form"]))
        m = model.fit_weights("race", data)
        self.assertNotIn("form", m.weights)
        self.assertEqual(m.effective(data.settings)["form"], 0.0)

    def test_saves_prediction_to_injected_db(self):
        out = model.predict(self.data, 2026, 9, "R")
        model.save_prediction(self.app.db, 2026, 9, "R", out)
        saved = self.app.db.query("SELECT driver FROM predictions WHERE pick_pos IS NOT NULL ORDER BY pick_pos")
        self.assertEqual(saved.driver.tolist(), out["pick"])

    def test_backtest_reports_accuracy(self):
        df = backtest.run(self.data, seasons=(2026,))
        self.assertGreater(len(df), 4)
        self.assertTrue({"Modelis", "tiketini", "logloss", "brier"} <= set(df.columns))
        self.assertGreater(backtest.summary(df)["points"], 0)


class DnfAndWeatherTest(unittest.TestCase):
    def test_unreliable_driver_gets_higher_dnf_chance(self):
        app, _ = temp_app()
        synthetic_season(app.db)
        app.db.execute("UPDATE results SET status='Retired' WHERE driver='HHH' AND session='R'")
        data = app.dataset()
        X = features.build(data, 2026, 9, "R")
        q = X.attrs["dnf"]
        self.assertGreater(q["HHH"], q["AAA"])
        self.assertEqual(features.build(data, 2026, 9, "Q").attrs["dnf"].max(), 0.0)   # kvalifikacijai – ne

    def test_backtest_uses_forecast_not_sensor_rain(self):
        app, _ = temp_app()
        synthetic_season(app.db)
        app.db.write("weather", [dict(season=2026, round=3, session="R", rain_prob=1.0, rain_prob_fc=0.2)])
        data = app.dataset()
        start = data.session_rows(2026, 3, "R").date_utc.iloc[0]
        self.assertAlmostEqual(features.build(data, 2026, 3, "R", before=start).attrs["rain"], 0.2)
        self.assertAlmostEqual(features.build(data, 2026, 3, "R").attrs["rain"], 1.0)


if __name__ == "__main__":
    unittest.main()
