"""F1 spėjimų programa (sąsaja). Paleidimas: darbalaukio nuoroda „F1 Spėjimai“ arba F1 Spėjimai.vbs.
Visi sąsajos tekstai – per vertėją `t` (DB lentelė `vertimai`, žr. f1model/i18n.py).

Meniu kairėje (ui_pages.py): Artimiausia sesija · Etapas · Sezonas · Naujienos · Modelis · Duomenys.
Ilgi darbai (atnaujinimas, mokymas) vyksta foniniame sraute su eigos skydeliu (ui_progress.py)."""
import os
import threading
from datetime import datetime, timezone

import streamlit as st

import ui_pages as pages
import ui_progress as prog
import ui_style as ui
from f1model import features, model
from f1model.app import App
from f1model.config import SEASON
from f1model.i18n import DEFAULT_LANGUAGE


@st.cache_resource
def get_app():
    return App.create()


@st.cache_resource
def memo():
    """Apmokyti modeliai (pagal duomenų versiją)."""
    return {}


@st.cache_resource
def jobs():
    """Vykstantys foniniai darbai – išlieka perkrovus puslapį ar perėjus į kitą meniu punktą."""
    return {}


def version(app):
    """Keičiasi tik pasikeitus modelio duomenims arba Excel failui (ne kalbai ar išsaugotam spėjimui)."""
    return app.db.data_version(), app.excel_path.stat().st_mtime if app.excel_path.exists() else 0


def run_job(key, work, tracker, render):
    """Paleidžia (arba prisijungia prie jau vykstančio) foninį darbą ir rodo jo eigą, kol baigsis."""
    store = jobs()
    if key not in store:
        store[key] = prog.Job(work, tracker())
    try:
        return prog.follow(store[key], st.empty(), render)
    finally:
        if store.get(key) is not None and store[key].done:
            store.pop(key, None)


def trained(key, title, kinds, fit):
    """Modelio mokymas su eigos skydeliu; rezultatas įsimenamas."""
    store = memo()
    if key not in store:
        names = {"quali": t("progress.model_quali"), "race": t("progress.model_race")}
        store[key] = run_job(key, fit, lambda: prog.TrainTracker(kinds),
                             lambda job: prog.render_training(job, t, title, names))
    return store[key]


def load_model(app, ver):
    def fit(tracker):
        try:
            app.excel().sync_to_db(app.db, app.dataset().events, SEASON)
        except Exception:  # pvz. Excel atidarytas – ne kritiška
            pass
        data = app.dataset()
        fitted = model.fit_all(data, progress=tracker)
        model.save_weights(app.db, fitted)
        return data, fitted
    return trained(("model", ver), t("progress.training_title"), list(model.KINDS), fit)


def weights_before(kind, upto):
    return trained(("before", version(app), kind, upto), t("progress.training_before_title"), [kind],
                   lambda tracker: model.fit_weights(kind, data, upto=upto,
                                                     progress=lambda f, d="": tracker(f, kind, f, d))[0])


def request_update():
    st.session_state["update_requested"] = True
    st.rerun()


def update_data():
    """Duomenų atnaujinimas foniniame sraute; skydelis rodo kiekvieno šaltinio būseną ir laiką."""
    sources = app.sources()
    keys = [type(s).__name__ for s in sources]
    names = [t.get(f"source.{k}", s.label) for k, s in zip(keys, sources)]
    descs = [t.get(f"source.{k}.desc", "") for k in keys]
    prefs = app.preferences()

    def work(tracker):
        errors = app.update(SEASON, progress=tracker)
        prog.save_durations(prefs, tracker.durations())
        prefs.set("atnaujinta", datetime.now(timezone.utc).isoformat())
        return errors
    return run_job("update", work, lambda: prog.UpdateTracker(keys, prog.load_durations(prefs)),
                   lambda job: prog.render_update(job, t, names, descs))


def save_language():
    app.preferences().set("kalba", st.session_state["lang"])


# ------------------------------------------------------------------ paleidimas

app = get_app()
languages = app.translations().languages()
if st.session_state.get("lang") not in languages:
    saved = app.preferences().get("kalba", DEFAULT_LANGUAGE)
    st.session_state["lang"] = saved if saved in languages else DEFAULT_LANGUAGE
t = app.translator(st.session_state["lang"])

st.set_page_config(page_title=t("app.title"), page_icon="ikona.ico", layout="wide")
ui.apply()
ui.header(t("brand.accent"), t("brand.subtitle", season=SEASON))

with st.sidebar:
    if st.button(t("sidebar.update"), width="stretch", type="primary", key="update_side"):
        st.session_state["update_requested"] = True
if st.session_state.pop("update_requested", False) or "update" in jobs():
    errors = update_data()
    st.session_state["update_errors"] = [(name, str(e)) for name, e in errors]
    app.reload_settings()
    for k in [k for k in st.session_state if k.startswith("mult_")]:
        del st.session_state[k]
    st.rerun()

data, fitted = load_model(app, version(app))
for f in features.names():  # slankiklių reikšmės pritaikomos prieš skaičiuojant spėjimą
    if f"mult_{f}" in st.session_state:
        data.settings.multipliers[f] = float(st.session_state[f"mult_{f}"])

ctx = pages.Ctx(app, t, data, fitted, version(app), weights_before, request_update)
PAGES = [("next", pages.page_next), ("weekend", pages.page_weekend), ("season", pages.page_season),
         ("news", pages.page_news), ("model", pages.page_model), ("data", pages.page_data)]
nav = st.navigation([st.Page(lambda fn=fn: fn(ctx), title=t(f"nav.{key}"), url_path=key, default=key == "next")
                     for key, fn in PAGES])

with st.sidebar:
    st.caption(t("sidebar.update_info"))
    last = app.preferences().get("atnaujinta")
    ui.side_info(t("sidebar.last_update"), pages.local(last, "%Y-%m-%d %H:%M") if last else t("sidebar.never"))
    for name, err in st.session_state.get("update_errors", []):
        st.warning(f"{name}: {err}")
    st.divider()
    st.selectbox(t("sidebar.language"), list(languages), format_func=languages.get, key="lang",
                 on_change=save_language)
    if st.button(t("sidebar.quit"), width="stretch"):
        st.warning(t("sidebar.quit_done"))
        threading.Timer(1.0, os._exit, [0]).start()

nav.run()
