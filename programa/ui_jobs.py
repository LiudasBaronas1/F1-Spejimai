"""Foniniai darbai, bendri visiems programos langams: duomenų atnaujinimas, modelio mokymas ir automatinis
atnaujinimas pagal grafiką (f1model/scheduler.py). Čia nėra Streamlit – tik srautai ir jų būsena;
eigą rodo ui_progress.py, o sąsaja (ui.py) tik paleidžia darbus ir seka jų eigą."""
import logging
import threading
import time
from datetime import datetime, timezone

import ui_progress as prog
from f1model import model
from f1model.config import SEASON

log = logging.getLogger("f1")


class Job:
    """Darbas foniniame sraute. tracker sukuriamas prieš paleidžiant (kad eigos skydelis jį turėtų iškart);
    work(tracker) jį pildo. on_done(job) kviečiamas baigus (tame pačiame sraute)."""

    def __init__(self, work, tracker, on_done=None, auto=False):
        self.tracker, self.result, self.error, self.t0, self.auto = tracker, None, None, time.monotonic(), auto
        self._on_done = on_done
        self.thread = threading.Thread(target=self._run, args=(work,), daemon=True)
        self.thread.start()

    def _run(self, work):
        try:
            self.result = work(self.tracker)
        except Exception as e:  # klaida parodoma sąsajoje
            log.exception("Foninis darbas nepavyko")
            self.error = e
        if self._on_done:
            self._on_done(self)

    @property
    def done(self):
        return not self.thread.is_alive()

    def elapsed(self):
        return time.monotonic() - self.t0


class Jobs:
    """Vykstantys darbai (po vieną kiekvienam raktui) ir apmokyti modeliai."""

    def __init__(self, app):
        self.app = app
        self._lock = threading.RLock()
        self._running = {}          # raktas -> Job
        self._models = {}           # raktas -> rezultatas (Dataset, modeliai) arba KindModel
        self._version = None
        self.generation = 0         # kiek kartų baigtas duomenų atnaujinimas (sąsaja pagal tai persikrauna)
        self.last_errors = []       # [(šaltinis, klaidos tekstas)] – paskutinio atnaujinimo

    # --- būsena
    def get(self, key):
        return self._running.get(key)

    @property
    def update_job(self):
        return self._running.get("update")

    @property
    def updating(self):
        return self.update_job is not None

    def data_version(self):
        """Modelio duomenų versija. Kol vyksta atnaujinimas – paskutinė iki jo (nemokoma iš pusės duomenų)."""
        with self._lock:
            if self._version is None or not self.updating:
                x = self.app.excel_path
                self._version = (self.app.db.data_version(), x.stat().st_mtime if x.exists() else 0)
            return self._version

    def start(self, key, work, tracker, store=False, on_done=None, auto=False):
        """Paleidžia darbą (arba grąžina jau vykstantį tuo pačiu raktu). store – rezultatą įsiminti pagal raktą."""
        with self._lock:
            job = self._running.get(key)
            if job is not None:
                return job

            def finish(job):
                with self._lock:
                    self._running.pop(key, None)
                    if store and job.error is None:
                        self._models[key] = job.result
                if on_done and job.error is None:
                    on_done(job.result)
            job = self._running[key] = Job(work, tracker, finish, auto)
            return job

    # --- duomenų atnaujinimas
    def update(self, auto=False):
        sources = self.app.sources()
        keys = [type(s).__name__ for s in sources]
        prefs = self.app.preferences()
        expected = {**{k: s.expected_s for k, s in zip(keys, sources)}, **prog.load_durations(prefs)}

        def work(tracker):
            errors = self.app.update(SEASON, progress=tracker)
            prog.save_durations(prefs, tracker.durations())
            return errors

        def done(errors):
            self.last_errors = [(name, str(e)) for name, e in errors]
            self.generation += 1
        job = self.start("update", work, prog.UpdateTracker(keys, expected), on_done=done, auto=auto)
        if not auto:
            job.auto = False     # vartotojas prisijungė prie automatinio – toliau rodomas visas skydelis
        return job

    # --- modeliai
    def model_key(self):
        return ("model", self.data_version())

    def model(self):
        """(Dataset, {"quali"/"race": KindModel}) dabartinei duomenų versijai arba None (dar neapmokyta)."""
        return self._models.get(self.model_key())

    def train(self):
        """Mokymo darbas dabartinei versijai (None – jau apmokyta). Seni modeliai pamirštami."""
        key = self.model_key()
        if key in self._models:
            return None
        with self._lock:
            for k in [k for k in self._models if k[1] != key[1]]:
                del self._models[k]

        def work(tracker):
            data = self.app.dataset()
            return data, self.app.train(data, progress=tracker)
        return self.start(key, work, prog.TrainTracker(list(model.KINDS)), store=True)

    def train_before(self, data, kind, upto):
        """(rezultatas arba None, darbas) – modelis, išmoktas tik iš sesijų iki `upto` (įvykusios sesijos spėjimui)."""
        key = ("before", self.data_version()[0], kind, upto)
        if key in self._models:
            return self._models[key], None
        work = lambda tracker: model.fit_weights(kind, data, upto=upto,
                                                 progress=lambda f, d="": tracker(f, kind, f, d))
        return None, self.start(key, work, prog.TrainTracker([kind]), store=True)


class AutoUpdater(threading.Thread):
    """Kas CHECK_S sekundžių tikrina grafiką; atėjus laikui atnaujina duomenis ir iškart apmoko modelį,
    kad atsidarius programai viskas jau būtų paruošta. Veikia, kol veikia programos serveris."""
    CHECK_S = 30
    RETRY_MIN = 10              # nepavykus – kitas bandymas ne anksčiau nei po tiek minučių

    def __init__(self, jobs, clock=lambda: datetime.now(timezone.utc)):
        super().__init__(daemon=True, name="auto-atnaujinimas")
        self.jobs, self.clock, self._failed_at = jobs, clock, None

    def sessions(self):
        s = self.jobs.app.db.query("SELECT session, date_utc FROM sessions WHERE season=?", (SEASON,))
        return list(zip(s.session, s.date_utc))

    def next_due(self):
        app = self.jobs.app
        return app.auto_update_policy().next_due(app.last_update(), self.sessions(), self.clock())

    def tick(self):
        now = self.clock()
        if self.jobs.updating or (self._failed_at and (now - self._failed_at).total_seconds() < self.RETRY_MIN * 60):
            return False
        nxt = self.next_due()
        if nxt is None or nxt > now:
            return False
        job = self.jobs.update(auto=True)
        job.thread.join()
        self._failed_at = now if job.error else None
        training = self.jobs.train()
        if training:
            training.thread.join()
        return True

    def run(self):
        while True:
            try:
                self.tick()
            except Exception:
                log.exception("Automatinis atnaujinimas nepavyko")
                self._failed_at = self.clock()
            time.sleep(self.CHECK_S)
