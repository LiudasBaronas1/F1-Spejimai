"""F1 spėjimų programa (sąsaja). Paleidimas: darbalaukio nuoroda „F1 Spėjimai“ arba F1 Spėjimai.vbs.

Šis failas tik sujungia dalis: sukuria `App` (kompozicijos šaknis), vertėją, `Controller` (foniniai darbai –
atnaujinimas ir mokymas su eigos skydeliu) ir perduoda puslapiams (`views/`) siaurą `Ctx` sąsają.
Išvaizda – ui.css ir ui_style.py; tekstai – DB lentelė `vertimai` (f1model/i18n.py)."""
import os
import threading
from datetime import datetime, timezone

import streamlit as st

import ui_progress as prog
import ui_style as ui
import views
from f1model import features, model
from f1model.app import App
from f1model.config import SEASON
from f1model.i18n import DEFAULT_LANGUAGE
from views.common import local


@st.cache_resource
def get_app():
    return App.create()


@st.cache_resource
def shared_state():
    """Vienos programos būsena tarp perkrovimų: apmokyti modeliai ir vykstantys foniniai darbai."""
    return {"models": {}, "jobs": {}}


class Controller:
    """Ilgi darbai su eigos skydeliu. Priklausomybės (programa, vertėjas, būsena) perduodamos konstruktoriuje."""

    def __init__(self, app, t, state):
        self.app, self.t, self.models, self.jobs = app, t, state["models"], state["jobs"]

    def version(self):
        """Keičiasi tik pasikeitus modelio duomenims arba Excel failui (ne kalbai ar išsaugotam spėjimui)."""
        x = self.app.excel_path
        return self.app.db.data_version(), x.stat().st_mtime if x.exists() else 0

    def _run(self, key, work, tracker, render):
        """Paleidžia (arba prisijungia prie jau vykstančio) foninį darbą ir rodo jo eigą, kol baigsis."""
        if key not in self.jobs:
            self.jobs[key] = prog.Job(work, tracker())
        try:
            return prog.follow(self.jobs[key], st.empty(), render)
        finally:
            if self.jobs.get(key) is not None and self.jobs[key].done:
                self.jobs.pop(key, None)

    def _trained(self, key, title, kinds, fit):
        if key not in self.models:
            names = {"quali": self.t("progress.model_quali"), "race": self.t("progress.model_race")}
            self.models[key] = self._run(key, fit, lambda: prog.TrainTracker(kinds),
                                         lambda job: prog.render_training(job, self.t, title, names))
        return self.models[key]

    def model(self):
        """(Dataset, apmokyti svoriai) dabartinei duomenų versijai."""
        def fit(tracker):
            data = self.app.dataset()
            fitted = model.fit_all(data, progress=tracker)
            model.save_weights(self.app.db, fitted)
            return data, fitted
        return self._trained(("model", self.version()), self.t("progress.training_title"), list(model.KINDS), fit)

    def weights_before(self, data):
        """Funkcija (rūšis, iki) -> svoriai, išmokti tik iš sesijų iki nurodyto laiko."""
        def get(kind, upto):
            return self._trained(("before", self.version(), kind, upto), self.t("progress.training_before_title"),
                                 [kind], lambda tracker: model.fit_weights(
                                     kind, data, upto=upto, progress=lambda f, d="": tracker(f, kind, f, d))[0])
        return get

    @property
    def updating(self):
        return "update" in self.jobs

    def update(self):
        """Duomenų atnaujinimas; grąžina [(šaltinis, klaida)]."""
        sources = self.app.sources()
        keys = [type(s).__name__ for s in sources]
        prefs = self.app.preferences()
        expected = {**{type(s).__name__: s.expected_s for s in sources}, **prog.load_durations(prefs)}
        names = [self.t.get(f"source.{k}", s.label) for k, s in zip(keys, sources)]
        descs = [self.t.get(f"source.{k}.desc", "") for k in keys]

        def work(tracker):
            errors = self.app.update(SEASON, progress=tracker)
            prog.save_durations(prefs, tracker.durations())
            prefs.set("atnaujinta", datetime.now(timezone.utc).isoformat())
            return errors
        return self._run("update", work, lambda: prog.UpdateTracker(keys, expected),
                         lambda job: prog.render_update(job, self.t, names, descs))


def request_update():
    st.session_state["update_requested"] = True
    st.rerun()


def sidebar(app, t, languages):
    with st.sidebar:
        st.caption(t("sidebar.update_info"))
        last = app.preferences().get("atnaujinta")
        ui.side_info(t("sidebar.last_update"), local(last, "%Y-%m-%d %H:%M") if last else t("sidebar.never"))
        for name, err in st.session_state.get("update_errors", []):
            st.warning(f"{name}: {err}")
        st.divider()
        st.selectbox(t("sidebar.language"), list(languages), format_func=languages.get, key="lang",
                     on_change=lambda: app.preferences().set("kalba", st.session_state["lang"]))
        if st.button(t("sidebar.quit"), width="stretch"):
            st.warning(t("sidebar.quit_done"))
            threading.Timer(1.0, os._exit, [0]).start()


def main():
    app = get_app()
    languages = app.translations().languages()
    if st.session_state.get("lang") not in languages:
        saved = app.preferences().get("kalba", DEFAULT_LANGUAGE)
        st.session_state["lang"] = saved if saved in languages else DEFAULT_LANGUAGE
    t = app.translator(st.session_state["lang"])
    st.set_page_config(page_title=t("app.title"), page_icon="ikona.ico", layout="wide")
    ui.apply()
    ui.header(t("brand.accent"), t("brand.subtitle", season=SEASON))
    ctl = Controller(app, t, shared_state())

    with st.sidebar:
        if st.button(t("sidebar.update"), width="stretch", type="primary", key="update_side"):
            st.session_state["update_requested"] = True
    if st.session_state.pop("update_requested", False) or ctl.updating:
        st.session_state["update_errors"] = [(name, str(e)) for name, e in ctl.update()]
        app.reload_settings()
        for k in [k for k in st.session_state if k.startswith("mult_")]:
            del st.session_state[k]
        st.rerun()

    data, fitted = ctl.model()
    for f in features.names():  # slankiklių reikšmės pritaikomos prieš skaičiuojant spėjimą
        if f"mult_{f}" in st.session_state:
            data.settings.multipliers[f] = float(st.session_state[f"mult_{f}"])
    ctx = views.Ctx(app, t, data, fitted, ctl.weights_before(data), request_update)
    nav = st.navigation([st.Page(lambda fn=fn: fn(ctx), title=t(f"nav.{key}"), url_path=key, default=i == 0)
                         for i, (key, fn) in enumerate(views.pages())])
    sidebar(app, t, languages)
    nav.run()


main()
