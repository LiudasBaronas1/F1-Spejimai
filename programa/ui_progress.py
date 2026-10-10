"""Eigos skydelis: ilgas darbas (duomenų atnaujinimas, modelio mokymas) vyksta foniniame sraute, o sąsaja
kas ~0,25 s perpiešia skydelį – laikrodžiai eina tolygiai, juosta juda ir tarp įvykių.

Laiko prognozė remiasi tuo, kiek kiekvienas šaltinis užtruko ankstesniais kartais (nustatymas
`saltiniu_trukmes`), o šaltinio viduje – vidutine vieno elemento trukme."""
import json
import threading
import time

import ui_style as ui

TICK_S = 0.25
DURATIONS_KEY = "saltiniu_trukmes"


def clock(seconds):
    seconds = max(0, int(round(seconds)))
    m, s = divmod(seconds, 60)
    return f"{m // 60}:{m % 60:02d}:{s:02d}" if m >= 60 else f"{m}:{s:02d}"


class Job:
    """Darbas foniniame sraute. tracker sukuriamas prieš paleidžiant (kad skydelis jį turėtų iškart);
    work(tracker) jį pildo (tik paprasti duomenys, be st.*)."""

    def __init__(self, work, tracker):
        self.tracker, self.result, self.error, self.t0 = tracker, None, None, time.monotonic()
        self.thread = threading.Thread(target=self._run, args=(work,), daemon=True)
        self.thread.start()

    def _run(self, work):
        try:
            self.result = work(self.tracker)
        except Exception as e:  # klaida parodoma sąsajoje
            self.error = e

    @property
    def done(self):
        return not self.thread.is_alive()

    def elapsed(self):
        return time.monotonic() - self.t0


def follow(job, slot, render):
    """Kol darbas vyksta – perpiešia skydelį; baigus skydelį paslepia ir grąžina darbo rezultatą
    (arba iškelia jo klaidą)."""
    while not job.done:
        slot.markdown(render(job), unsafe_allow_html=True)
        time.sleep(TICK_S)
    slot.empty()
    if job.error:
        raise job.error
    return job.result


# ------------------------------------------------------------------ duomenų atnaujinimas

class UpdateTracker:
    """Iš `sources.Progress` įvykių kaupia kiekvieno šaltinio būseną ir laikus (kviečiama foniniame sraute)."""

    def __init__(self, keys, expected):
        """keys – šaltinių raktai; expected – {raktas: laukiama trukmė s} (išmatuota anksčiau arba šaltinio
        numatytoji DataSource.expected_s)."""
        self.keys, self.expected = keys, [expected[k] for k in keys]
        self.status = ["wait"] * len(keys)
        self.started, self.finished = [None] * len(keys), [None] * len(keys)
        self.current, self.step, self.detail, self.item_t0 = None, (0, 0), "", None
        self.errors = {}

    def __call__(self, ev):
        k, now = ev.index, time.monotonic()
        if ev.status == "running":
            if self.started[k] is None:
                self.started[k], self.status[k] = now, "run"
            if ev.step != self.step or k != self.current:
                self.item_t0 = now
            self.current, self.step, self.detail = k, ev.step, ev.detail
        else:
            self.finished[k], self.status[k] = now, "done" if ev.status == "done" else "err"
            if ev.error is not None:
                self.errors[k] = str(ev.error)

    def durations(self):
        return {k: f - s for k, s, f in zip(self.keys, self.started, self.finished) if s and f}

    def source_frac(self, k, now):
        """Šaltinio dalis: (i + dalis dabartinio elemento) / n; be žingsnių – pagal laukiamą trukmę."""
        if self.status[k] != "run":
            return 1.0 if self.status[k] in ("done", "err") else 0.0
        i, n = self.step if k == self.current else (0, 0)
        spent = now - self.started[k]
        if n:
            per_item = (self.item_t0 - self.started[k]) / i if i else self.expected[k] / n
            inside = min(0.95, (now - self.item_t0) / per_item) if per_item > 0 else 0.0
            return min(0.99, (i + inside) / n)
        return min(0.9, spent / self.expected[k]) if self.expected[k] else 0.0

    def remaining(self, k, now):
        if self.status[k] in ("done", "err"):
            return 0.0
        if self.status[k] == "wait":
            return self.expected[k]
        frac, spent = self.source_frac(k, now), now - self.started[k]
        by_rate = spent / frac * (1 - frac) if frac > 0.15 else None
        return max(0.0, by_rate if by_rate is not None else self.expected[k] - spent)

    def overall(self, now):
        """(dalis 0..1, likęs laikas s) – šaltiniai sveriami pagal laukiamą trukmę."""
        total = sum(self.expected)
        done = sum(e * self.source_frac(k, now) for k, e in enumerate(self.expected))
        return (min(done / total, 0.999) if total else 0.0), sum(self.remaining(k, now) for k in range(len(self.keys)))


def render_update(job, t, names, descs):
    tr, now = job.tracker, time.monotonic()
    frac, left = tr.overall(now)
    if job.done:
        frac, left = 1.0, 0.0
    steps = []
    for k, name in enumerate(names):
        s = tr.status[k]
        if s == "run":
            txt = t("progress.running_for", s=clock(now - tr.started[k]))
        elif s == "done":
            txt = t("progress.done", s=f"{tr.finished[k] - tr.started[k]:.1f}")
        elif s == "err":
            txt = t("progress.failed", s=f"{tr.finished[k] - tr.started[k]:.1f}")
        else:
            txt = t("progress.expected", s=clock(tr.expected[k]))
        steps.append((name, s, txt))
    now_box = None
    k = tr.current
    if k is not None and tr.status[k] == "run":
        i, n = tr.step
        now_box = dict(name=names[k], desc=descs[k], detail=tr.detail or t("progress.starting"),
                       step=(t("progress.item", i=i + 1, n=n) + " · " if n else "") + clock(now - tr.started[k]),
                       frac=tr.source_frac(k, now))
    running = sum(s in ("done", "err") for s in tr.status) + (1 if k is not None and tr.status[k] == "run" else 0)
    sub = (f'{t("progress.update_sub", k=min(running, len(names)), n=len(names))} · '
           f'{t("progress.elapsed", t=clock(job.elapsed()))}'
           + ("" if job.done else f' · {t("progress.left", t=clock(left))}'))
    return ui.progress_html(t("progress.update_title"), frac, sub, steps, now_box, t("progress.now"))


def load_durations(prefs):
    try:
        return json.loads(prefs.get(DURATIONS_KEY, "{}"))
    except ValueError:
        return {}


def save_durations(prefs, measured, alpha=0.5):
    """Slenkantis vidurkis, kad viena lėta (ar greita) kartas prognozės nesugadintų."""
    old = load_durations(prefs)
    new = {k: round(alpha * v + (1 - alpha) * old.get(k, v), 2) for k, v in measured.items()}
    prefs.set(DURATIONS_KEY, json.dumps({**old, **new}))


# ------------------------------------------------------------------ modelio mokymas

class TrainTracker:
    """Mokymosi eiga: progress(dalis, modelis, dalis modelio viduje, detalė)."""

    def __init__(self, kinds):
        self.kinds, self.kind, self.kind_frac, self.frac, self.detail = kinds, kinds[0], 0.0, 0.0, ""
        self.t_kind, self.marks = {}, []

    def __call__(self, frac, kind, kind_frac, detail):
        now = time.monotonic()
        self.t_kind.setdefault(kind, now)
        self.kind, self.kind_frac, self.frac, self.detail = kind, kind_frac, frac, detail
        self.marks.append((now, frac))

    def left(self, now, elapsed):
        """Likęs laikas pagal pastarųjų ~10 s greitį (tiksliau nei vidurkis nuo pradžios)."""
        recent = [(t, f) for t, f in self.marks if t >= now - 10]
        if len(recent) >= 2 and recent[-1][1] > recent[0][1]:
            rate = (recent[-1][1] - recent[0][1]) / (recent[-1][0] - recent[0][0])
            return (1 - self.frac) / rate
        return elapsed / self.frac * (1 - self.frac) if self.frac > 0.05 else None


def render_training(job, t, title, names):
    tr, now = job.tracker, time.monotonic()
    k = tr.kinds.index(tr.kind)
    steps = []
    for i, x in enumerate(tr.kinds):
        if i < k or job.done:
            steps.append((names[x], "done", t("progress.finished")))
        elif i == k:
            steps.append((names[x], "run", t("progress.running_for", s=clock(now - tr.t_kind.get(x, now)))))
        else:
            steps.append((names[x], "wait", t("progress.waiting")))
    now_box = None if job.done else dict(
        name=names[tr.kind], desc=t("progress.training_desc"),
        detail=t("progress.session", d=tr.detail) if tr.detail else t("progress.fitting"), frac=tr.kind_frac,
        step=clock(now - tr.t_kind.get(tr.kind, now)))
    left = tr.left(now, job.elapsed())
    sub = (f'{t("progress.training_sub", k=k + 1, n=len(tr.kinds))} · {t("progress.elapsed", t=clock(job.elapsed()))}'
           + (f' · {t("progress.left", t=clock(left))}' if left is not None and not job.done else ""))
    return ui.progress_html(title, 1.0 if job.done else tr.frac, sub, steps, now_box, t("progress.now"))
