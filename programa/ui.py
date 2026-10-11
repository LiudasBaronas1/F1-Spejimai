"""F1 spėjimų programa (sąsaja). Paleidimas: darbalaukio nuoroda „F1 Spėjimai“ arba F1 Spėjimai.vbs.

Šis failas tik sujungia dalis: sukuria `App` (kompozicijos šaknis), foninius darbus (`ui_jobs.Jobs` –
atnaujinimas, mokymas, automatinis atnaujinimas pagal grafiką), `Controller` (rodo darbų eigą) ir perduoda
puslapiams (`views/`) siaurą `Ctx` sąsają. Išvaizda – ui.css ir ui_style.py; tekstai – DB lentelė `vertimai`."""
import os
import threading
import time
from dataclasses import replace

import streamlit as st

import ui_progress as prog
import ui_style as ui
import views
from f1model import features
from f1model.app import App
from f1model.config import SEASON
from f1model.i18n import DEFAULT_LANGUAGE
from ui_jobs import AutoUpdater, Jobs
from views.common import local

STATUS_REFRESH_S = 5


@st.cache_resource
def services():
    """Viena programa ir jos foniniai darbai visiems langams; automatinis atnaujinimas paleidžiamas čia."""
    app = App.create()
    jobs = Jobs(app)
    updater = AutoUpdater(jobs)
    updater.start()
    return app, jobs, updater


class Controller:
    """Rodo foninių darbų eigą. Priklausomybės (darbai, vertėjas) perduodamos konstruktoriuje."""

    def __init__(self, jobs, t):
        self.jobs, self.t = jobs, t

    def _follow_training(self, job, title):
        names = {"quali": self.t("progress.model_quali"), "race": self.t("progress.model_race")}
        return prog.follow(job, st.empty(), lambda j: prog.render_training(j, self.t, title, names))

    def model(self):
        """(Dataset, {"quali"/"race": KindModel}) dabartinei duomenų versijai (jei reikia – apmokoma)."""
        ready = self.jobs.model()
        return ready or self._follow_training(self.jobs.train(), self.t("progress.training_title"))

    def model_before(self, kind, upto, data):
        """Modelis, išmoktas tik iš sesijų iki `upto` (įvykusios sesijos spėjimui)."""
        ready, job = self.jobs.train_before(data, kind, upto)
        return ready or self._follow_training(job, self.t("progress.training_before_title"))

    def update(self):
        """Duomenų atnaujinimas su eigos skydeliu (prisijungia ir prie vykstančio automatinio)."""
        job = self.jobs.update()
        sources = self.jobs.app.sources()
        keys = [type(s).__name__ for s in sources]
        names = [self.t.get(f"source.{k}", s.label) for k, s in zip(keys, sources)]
        descs = [self.t.get(f"source.{k}.desc", "") for k in keys]
        return prog.follow(job, st.empty(), lambda j: prog.render_update(j, self.t, names, descs))


def request_update():
    st.session_state["update_requested"] = True
    st.rerun()


@st.fragment(run_every=STATUS_REFRESH_S)
def auto_status(app, jobs, updater, t):
    """Šoninio meniu automatinio atnaujinimo būsena (persipiešia savaime). Kai automatinis atnaujinimas
    baigiasi ir modelis apmokytas – perkrauna visą puslapį su naujais duomenimis."""
    job = jobs.update_job
    if job is not None:
        frac, _ = job.tracker.overall(time.monotonic())
        st.progress(frac, text=t("auto.running", pct=f"{frac:.0%}"))
    else:
        last = app.last_update()
        ui.side_info(t("sidebar.last_update"), local(last, "%Y-%m-%d %H:%M") if last else t("sidebar.never"))
        nxt = updater.next_due()
        st.caption(t("auto.next", at=local(nxt.isoformat(), "%m-%d %H:%M")) if nxt else t("auto.off"))
    for name, err in jobs.last_errors:
        st.warning(f"{name}: {err}")
    if st.session_state.get("generation", jobs.generation) != jobs.generation and job is None and jobs.model():
        st.rerun(scope="app")


def auto_settings(app, t):
    policy = app.auto_update_policy()
    with st.expander(t("auto.settings")):
        enabled = st.toggle(t("auto.toggle"), value=policy.enabled)
        idle = st.number_input(t("auto.idle"), 15, 1440, policy.idle_min, step=15)
        weekend = st.number_input(t("auto.weekend"), 5, 240, policy.weekend_min, step=5)
        new = replace(policy, enabled=enabled, idle_min=int(idle), weekend_min=int(weekend))
        if new != policy:
            new.save(app.preferences())
            st.rerun()


def sidebar(app, jobs, updater, t, languages):
    with st.sidebar:
        if st.button(t("sidebar.update"), width="stretch", type="primary", key="update_side"):
            request_update()
        st.caption(t("sidebar.update_hint"))
        auto_status(app, jobs, updater, t)
        auto_settings(app, t)
        st.divider()
        st.selectbox(t("sidebar.language"), list(languages), format_func=languages.get, key="lang",
                     on_change=lambda: app.preferences().set("kalba", st.session_state["lang"]))
        if st.button(t("sidebar.quit"), width="stretch"):
            st.warning(t("sidebar.quit_done"))
            threading.Timer(1.0, os._exit, [0]).start()


def main():
    app, jobs, updater = services()
    languages = app.translations().languages()
    if st.session_state.get("lang") not in languages:
        saved = app.preferences().get("kalba", DEFAULT_LANGUAGE)
        st.session_state["lang"] = saved if saved in languages else DEFAULT_LANGUAGE
    t = app.translator(st.session_state["lang"])
    st.set_page_config(page_title=t("app.title"), page_icon="ikona.ico", layout="wide")
    ui.apply()
    ui.header(t("brand.accent"), t("brand.subtitle", season=SEASON))
    ctl = Controller(jobs, t)

    manual = jobs.update_job is not None and not jobs.update_job.auto
    if st.session_state.pop("update_requested", False) or manual:
        ctl.update()
        app.reload_settings()
        for k in [k for k in st.session_state if k.startswith("mult_")]:
            del st.session_state[k]
        st.rerun()

    st.session_state["generation"] = jobs.generation
    data, fitted = ctl.model()
    for f in features.names():  # slankiklių reikšmės pritaikomos prieš skaičiuojant spėjimą
        if f"mult_{f}" in st.session_state:
            data.settings.multipliers[f] = float(st.session_state[f"mult_{f}"])
    ctx = views.Ctx(app, t, data, fitted, lambda kind, upto: ctl.model_before(kind, upto, data), request_update)
    nav = st.navigation([st.Page(lambda fn=fn: fn(ctx), title=t(f"nav.{key}"), url_path=key, default=i == 0)
                         for i, (key, fn) in enumerate(views.pages())])
    sidebar(app, jobs, updater, t, languages)
    nav.run()


main()
