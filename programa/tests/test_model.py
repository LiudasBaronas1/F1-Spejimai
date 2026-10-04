import unittest

import numpy as np

from f1model import model
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


class EndToEndTest(unittest.TestCase):
    """Visas kelias su TESTINE duomenų baze: App -> Dataset -> mokymas -> spėjimas."""

    @classmethod
    def setUpClass(cls):
        cls.app, cls.tmp = temp_app()
        synthetic_season(cls.app.db, noise=4)
        cls.data = cls.app.dataset()

    def test_learns_that_form_matters_and_predicts_leaders(self):
        fitted = model.fit_all(self.data)
        self.assertGreater(fitted["race"][0]["weekend"] + fitted["race"][0]["form"], 0)
        out = model.predict(self.data, 2026, 9, "Q", weights=fitted["quali"][0])
        self.assertEqual(out["pick"][0], "AAA")
        self.assertEqual(set(out["pick"]), set(DRIVERS[:3]))
        self.assertTrue(0 < out["expected"] <= 6)

    def test_saves_prediction_to_injected_db(self):
        out = model.predict(self.data, 2026, 9, "R")
        model.save_prediction(self.app.db, 2026, 9, "R", out)
        saved = self.app.db.query("SELECT driver FROM predictions WHERE pick_pos IS NOT NULL ORDER BY pick_pos")
        self.assertEqual(saved.driver.tolist(), out["pick"])


if __name__ == "__main__":
    unittest.main()
