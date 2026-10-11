import unittest
from datetime import datetime, timedelta, timezone

from f1model.scheduler import PRE_SESSION_MIN, AutoUpdatePolicy
from tests.helpers import temp_app

NOW = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)


def iso(dt):
    return dt.isoformat()


class PolicyTest(unittest.TestCase):
    def setUp(self):
        self.p = AutoUpdatePolicy(enabled=True, idle_min=180, weekend_min=20)

    def test_first_run_is_immediate_and_off_means_never(self):
        self.assertEqual(self.p.next_due(None, [], NOW), NOW)
        self.assertIsNone(AutoUpdatePolicy(enabled=False).next_due(None, [], NOW))

    def test_idle_interval_between_weekends(self):
        far = [("R", iso(NOW + timedelta(days=10)))]
        last = NOW - timedelta(minutes=30)
        self.assertEqual(self.p.next_due(iso(last), far, NOW), last + timedelta(minutes=180))
        self.assertFalse(self.p.due(iso(last), far, NOW))

    def test_weekend_interval_and_pre_session_update(self):
        race = NOW + timedelta(hours=2)
        sessions = [("Q", iso(NOW - timedelta(hours=20))), ("R", iso(race))]
        last = NOW - timedelta(minutes=5)
        self.assertEqual(self.p.next_due(iso(last), sessions, NOW), last + timedelta(minutes=20))
        just_before = race - timedelta(minutes=PRE_SESSION_MIN)
        last = just_before - timedelta(minutes=10)            # kitas – likus PRE_SESSION_MIN iki starto
        self.assertEqual(self.p.next_due(iso(last), sessions, just_before - timedelta(minutes=1)), just_before)

    def test_update_when_results_should_be_ready(self):
        start = NOW - timedelta(hours=2)
        sessions = [("FP1", iso(start))]
        ready = start + timedelta(minutes=60 + 15)
        self.assertTrue(self.p.due(iso(ready - timedelta(minutes=1)), sessions, ready + timedelta(minutes=1)))

    def test_saved_in_preferences(self):
        prefs = temp_app()[0].preferences()
        AutoUpdatePolicy(enabled=False, idle_min=60, weekend_min=10).save(prefs)
        self.assertEqual(AutoUpdatePolicy.load(prefs), AutoUpdatePolicy(False, 60, 10))


class AutoUpdaterTest(unittest.TestCase):
    """AutoUpdater su netikrais darbais: atnaujina tik atėjus laikui ir po to apmoko modelį."""

    def test_runs_update_then_training_only_when_due(self):
        import threading

        from ui_jobs import AutoUpdater

        app = temp_app()[0]
        calls = []

        class FakeJob:
            def __init__(self, name):
                calls.append(name)
                self.error, self.thread = None, threading.Thread(target=lambda: None)
                self.thread.start()

        class FakeJobs:
            updating = False

            def __init__(self):
                self.app = app

            def update(self, auto=False):
                app.preferences().set("atnaujinta", iso(NOW))
                return FakeJob("update")

            def train(self):
                return FakeJob("train")

        updater = AutoUpdater(FakeJobs(), clock=lambda: NOW)
        self.assertTrue(updater.tick())                       # niekada neatnaujinta -> iškart
        self.assertEqual(calls, ["update", "train"])
        self.assertFalse(updater.tick())                      # ką tik atnaujinta -> laukiama
        self.assertEqual(calls, ["update", "train"])


if __name__ == "__main__":
    unittest.main()
