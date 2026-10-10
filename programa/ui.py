"""F1 spėjimų programa (sąsaja). Paleidimas: darbalaukio nuoroda „F1 Spėjimai“ arba F1 Spėjimai.vbs.
Visi sąsajos tekstai – per vertėją `t` (DB lentelė `vertimai`, žr. f1model/i18n.py).

Skyriai: Spėjimas · Trasa · Atnaujinimai · Naujienos · Modelis ir duomenys (paaiškinimas, požymiai, testas,
parametrai, SQL, žinynai). Etapas ir sesija pasirenkami vieną kartą – virš skyrių."""
import html
import os
import threading
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st

import ui_style as ui
from f1model import backtest, features, model, report
from f1model.app import App
from f1model.config import COMPETITIVE, SEASON
from f1model.dataset import kind_of
from f1model.i18n import DEFAULT_LANGUAGE

SQL_EXAMPLES = {  # raktas -> užklausa; pavadinimas – vertimas „sql.example.<raktas>“
    "round_results":
        "SELECT vieta, vairuotojas, komanda, starto_vieta, oficiali_vieta, statusas\nFROM v_rezultatai\n"
        "WHERE metai = 2026 AND etapas = 15 AND sesija = 'R'\nORDER BY vieta;",
    "driver_summary": "SELECT * FROM v_vairuotojai\nWHERE metai = 2026\nORDER BY taskai DESC;",
    "driver_results":
        "SELECT metai, grand_prix, sesija, vieta, starto_vieta, lietus, temperatura\nFROM v_rezultatai\n"
        "WHERE vairuotojas = 'NOR' AND sesija IN ('Q', 'R')\nORDER BY data DESC;",
    "wet_winners":
        "SELECT metai, grand_prix, sesija, ROUND(lietus, 2) AS lietus, vairuotojas AS nugaletojas\n"
        "FROM v_rezultatai\nWHERE lietus >= 0.5 AND vieta = 1\nORDER BY data DESC;",
    "weather":
        "SELECT grand_prix, sesija, data, ROUND(lietaus_tikimybe, 2) AS lietus, lijo_trasoje_laiko_dalis,\n"
        "       krituliai_regione_mm, ROUND(temperatura, 1) AS temperatura, saltinis\nFROM v_orai\n"
        "WHERE metai = 2026\nORDER BY data;",
    "best_at_track":
        "SELECT vairuotojas, COUNT(*) AS lenktynes, ROUND(AVG(vieta), 1) AS vid_vieta, SUM(vieta <= 3) AS podiumai\n"
        "FROM v_rezultatai\nWHERE trasa = 'Marina Bay' AND sesija = 'R'\n"
        "GROUP BY vairuotojas HAVING lenktynes >= 2\nORDER BY vid_vieta;",
    "odds":
        "SELECT sesija, rinka, saltinis, vairuotojas, tikimybe, koeficientas, tikra_vieta\nFROM v_koeficientai\n"
        "WHERE metai = 2026 AND etapas = (SELECT MAX(etapas) FROM v_koeficientai WHERE metai = 2026)\n"
        "ORDER BY sesija, rinka, tikimybe DESC;",
    "tracks": "SELECT * FROM trasos\nORDER BY trasa;",
    "players":
        "SELECT z.zaidejas, z.round AS etapas, z.session AS sesija, z.vieta, z.spejimas, r.vairuotojas AS tikras\n"
        "FROM zaideju_spejimai z\nLEFT JOIN v_rezultatai r ON r.metai = z.season AND r.etapas = z.round\n"
        "     AND r.sesija = z.session AND r.vieta = z.vieta\nWHERE z.season = 2026\n"
        "ORDER BY z.round, z.session, z.zaidejas, z.vieta;",
    "model": "SELECT * FROM v_modelio_spejimai\nORDER BY sukurta DESC\nLIMIT 50;",
}
REFERENCE_TABLES = ["trasos", "trasu_sinonimai", "komandos", "zaidejai", "gp_pavadinimai", "vairuotoju_vardai",
                    "naujienu_saltiniai", "naujienu_zymes", "vertimai", "kalbos"]
# Žinynai, lentelės ir SQL pavyzdžiai, susiję su asmenine totalizatoriaus Excel lentele – rodomi tik jei ji yra
EXCEL_ONLY = {"zaidejai", "gp_pavadinimai", "zaideju_spejimai", "players"}


def visible(keys):
    return [k for k in keys if app.has_excel or k not in EXCEL_ONLY]


# ------------------------------------------------------------------ priklausomybės (vienos programai)

@st.cache_resource
def get_app():
    return App.create()


@st.cache_resource
def memo():
    """Apmokyti modeliai (išvaloma kartu su st.cache_resource.clear()). Ne @st.cache_resource funkcijos,
    nes jų viduje negalima atnaujinti eigos skydelio."""
    return {}


def version(app):
    """Keičiasi tik pasikeitus modelio duomenims arba Excel failui (ne kalbai ar išsaugotam spėjimui)."""
    return app.db.data_version(), app.excel_path.stat().st_mtime if app.excel_path.exists() else 0


def local(iso, fmt="%m-%d %H:%M"):
    return datetime.fromisoformat(iso).astimezone().strftime(fmt)


def clock(seconds):
    m, s = divmod(int(seconds), 60)
    return f"{m // 60}:{m % 60:02d}:{s:02d}" if m >= 60 else f"{m}:{s:02d}"


# ------------------------------------------------------------------ eigos skydelis

class Panel:
    """Didelis eigos skydelis vietoje `slot` (st.empty): bendra juosta, kas daroma dabar, žingsnių sąrašas."""

    def __init__(self, slot, title):
        self.slot, self.title, self.t0, self.shown = slot, title, time.monotonic(), 0.0

    def timing(self, frac):
        elapsed = time.monotonic() - self.t0
        text = t("progress.elapsed", t=clock(elapsed))
        if 0.04 < frac < 1:
            text += " · " + t("progress.left", t=clock(elapsed / frac * (1 - frac)))
        return text

    def show(self, frac, subtitle, steps, now=None, force=False):
        if not force and time.monotonic() - self.shown < 0.12:   # ne dažniau nei ~8 kartus per sekundę
            return
        self.shown = time.monotonic()
        self.slot.markdown(ui.progress_html(self.title, frac, f"{subtitle} · {self.timing(frac)}", steps, now,
                                            t("progress.now")), unsafe_allow_html=True)


def cached(key, title, compute):
    """compute(panel) skaičiuojamas tik pirmą kartą; tuo metu rodomas eigos skydelis."""
    store = memo()
    if key not in store:
        slot = st.empty()
        store[key] = compute(Panel(slot, title))
        slot.empty()
    return store[key]


def training_progress(panel, kinds):
    """Mokymosi eigos funkcija: progress(dalis, modelis, dalis modelio viduje, detalė)."""
    names = {"quali": t("progress.model_quali"), "race": t("progress.model_race")}

    def on(frac, kind, kind_frac, detail):
        k = kinds.index(kind)
        steps = [(names[x], *(("done", t("progress.finished")) if i < k else ("run", t("progress.running")) if i == k
                              else ("wait", t("progress.waiting")))) for i, x in enumerate(kinds)]
        now = dict(name=names[kind], desc=t("progress.training_desc"),
                   detail=t("progress.session", d=detail) if detail else t("progress.fitting"), frac=kind_frac)
        panel.show(frac, t("progress.training_sub", k=k + 1, n=len(kinds)), steps, now, force=not detail)
    return on


def load(app, version):
    def compute(panel):
        try:
            app.excel().sync_to_db(app.db, app.dataset().events, SEASON)
        except Exception:  # pvz. Excel atidarytas – ne kritiška
            pass
        data = app.dataset()
        fitted = model.fit_all(data, progress=training_progress(panel, list(model.KINDS)))
        model.save_weights(app.db, fitted)
        return data, fitted
    return cached(("model", version), t("progress.training_title"), compute)


def weights_before(version, kind, upto, data):
    def compute(panel):
        on = training_progress(panel, [kind])
        return model.fit_weights(kind, data, upto=upto, progress=lambda f, d="": on(f, kind, f, d))[0]
    return cached(("before", version, kind, upto), t("progress.training_before_title"), compute)


def update_data(slot):
    """Duomenų atnaujinimas su eigos skydeliu: kiekvieno šaltinio būsena, trukmė ir ką jis dabar renka."""
    sources = app.sources()
    keys = [type(s).__name__ for s in sources]
    names = [t.get(f"source.{k}", s.label) for k, s in zip(keys, sources)]
    state, info, started = ["wait"] * len(sources), [t("progress.waiting")] * len(sources), {}
    panel = Panel(slot, t("progress.update_title"))

    def on(ev):
        k = ev.index
        started.setdefault(k, time.monotonic())
        if ev.status == "running":
            state[k], info[k] = "run", t("progress.running")
        else:
            secs = f"{time.monotonic() - started[k]:.0f}"
            state[k], info[k] = ("done", t("progress.done", s=secs)) if ev.status == "done" else \
                ("err", t("progress.failed", s=secs))
        i, n = ev.step
        now = dict(name=names[k], desc=t.get(f"source.{keys[k]}.desc", ""), detail=ev.detail or t("progress.starting"),
                   step=t("progress.item", i=i + 1, n=n) if n else "", frac=ev.source_frac) \
            if ev.status == "running" else None
        panel.show(ev.frac, t("progress.update_sub", k=k + 1, n=ev.total), list(zip(names, state, info)), now,
                   force=ev.status != "running" or not ev.detail)
    errors = app.update(SEASON, progress=on)
    app.preferences().set("atnaujinta", datetime.now(timezone.utc).isoformat())
    return errors


# ------------------------------------------------------------------ pagalbinės

def news_rows(df, team_names, summary_len=None):
    """Naujienų DataFrame -> eilutės ui.news_list (komandų žymės – komandos spalva)."""
    rows = []
    for _, n in df.iterrows():
        keys = [k for k in (n.komandos or "").split(",") if k]
        tags = [k for k in (n.zymes or "").split(",") if k]
        summary = n.santrauka or ""
        if summary_len and len(summary) > summary_len:
            summary = summary[:summary_len].rsplit(" ", 1)[0] + "…"
        rows.append(dict(title=n.pavadinimas, url=n.url, summary=summary,
                         meta=f"{local(n.paskelbta, '%Y-%m-%d %H:%M')} · {n.saltinis}",
                         chips=[(team_names.get(k, k), "", ref.team_color(team_names.get(k, k))) for k in keys]
                         + [(t(f"newstag.{g}"), "tag", None) for g in tags]))
    return rows


def weekend_panel(season, rnd, session, ev, leaders, teams):
    """Svarbu šiam etapui: FIA starto baudos, komandų atnaujinimai, svarbios naujienos apie pirmaujančias komandas."""
    brief = app.briefing()
    ui.section(t("weekend.title"), t("weekend.sub"))
    if data.fia_grid(season, rnd, session):
        changes = brief.grid_changes(data, season, rnd, session)
        if changes:
            ui.note(t("weekend.grid_title"), t("weekend.grid_text", changes=", ".join(
                f"{d} P{q} → P{g}" for d, q, g in changes)))
        else:
            st.caption(t("weekend.grid_ok"))
    ups = brief.upgrades(season, rnd)
    if ups:
        perf = [(f"{u.name} {u.counts['performance']}", "", u.color) for u in ups if u.counts["performance"]]
        ui.label(t("weekend.upgrades"))
        st.markdown(ui.chips(perf) or "–", unsafe_allow_html=True)
    elif season >= 2024:
        st.caption(t("weekend.no_upgrades"))
    keys = {ref.team_key(teams.get(d)) for d in leaders} - {None}
    news = brief.weekend_news(ev["date"], keys)
    if news.empty:
        st.caption(t("weekend.no_news"))
    else:
        ui.news_list(news_rows(news, {k: v[0] for k, v in brief.teams(season).items()}, summary_len=160))


def strategy_notes(location, street):
    tc = ref.tracks
    tyres, over = tc.tyre_severity(location), tc.overtaking(location)
    notes = [t("strategy.tyres_high" if tyres >= 4 else "strategy.tyres_low" if tyres <= 2 else "strategy.tyres_mid"),
             t("strategy.overtake_hard" if over >= 4 else "strategy.overtake_easy" if over <= 2
               else "strategy.overtake_mid")]
    return notes + ([t("strategy.street")] if street else [])


def save_language():
    app.preferences().set("kalba", st.session_state["lang"])


# ------------------------------------------------------------------ paleidimas

app = get_app()
languages = app.translations().languages()
if st.session_state.get("lang") not in languages:
    saved = app.preferences().get("kalba", DEFAULT_LANGUAGE)
    st.session_state["lang"] = saved if saved in languages else DEFAULT_LANGUAGE
t = app.translator(st.session_state["lang"])
SESSION = t.prefixed("session", ["FP1", "FP2", "FP3", "SQ", "S", "Q", "R"])
LABEL = {f: t.get(f"feature.{f}.label", x.label) for f, x in features.REGISTRY.items()}

st.set_page_config(page_title=t("app.title"), page_icon="ikona.ico", layout="wide")
ui.apply()

with st.sidebar:
    ui.side_brand(t("brand.accent"))
    st.selectbox(t("sidebar.language"), list(languages), format_func=languages.get, key="lang",
                 on_change=save_language)
    st.divider()
    update_clicked = st.button(t("sidebar.update"), width="stretch", type="primary")
    st.caption(t("sidebar.update_info"))

ui.header(t("brand.accent"), t("brand.subtitle", season=SEASON))
progress_slot = st.empty()
if update_clicked:
    st.session_state["update_errors"] = [(name, str(e)) for name, e in update_data(progress_slot)]
    app.reload_settings()
    st.cache_resource.clear()
    for k in [k for k in st.session_state if k.startswith("mult_")]:
        del st.session_state[k]
    st.rerun()

data, fitted = load(app, version(app))
S, ref = data.settings, data.ref
for f in features.names():  # slankiklių reikšmės pritaikomos prieš skaičiuojant spėjimą
    if f"mult_{f}" in st.session_state:
        S.multipliers[f] = float(st.session_state[f"mult_{f}"])

with st.sidebar:
    last = app.preferences().get("atnaujinta")
    ui.side_info(t("sidebar.last_update"), local(last, "%Y-%m-%d %H:%M") if last else t("sidebar.never"))
    now_utc = datetime.now(timezone.utc)
    nr, ns = data.next_session((now_utc - timedelta(minutes=30)).isoformat())
    if nr:
        nrow = data.session_rows(SEASON, nr, ns).iloc[0]
        left = datetime.fromisoformat(nrow.date_utc) - now_utc
        hours = max(left.total_seconds(), 0) / 3600
        ui.side_info(t("sidebar.next"), f"{data.event(SEASON, nr)['name']} · {SESSION[ns]} · "
                     f"{local(nrow.date_utc)} ({t('sidebar.in', t=f'{hours:.0f} h' if hours >= 1 else f'{hours * 60:.0f} min')})")
    for name, err in st.session_state.get("update_errors", []):
        st.warning(f"{name}: {err}")
    st.caption(t("sidebar.model_hint"))
    st.divider()
    if st.button(t("sidebar.quit"), width="stretch"):
        st.warning(t("sidebar.quit_done"))
        threading.Timer(1.0, os._exit, [0]).start()

# ------------------------------------------------------------------ etapo ir sesijos pasirinkimas (bendras)

with st.container(key="context"):
    seasons = sorted(data.events.season.unique(), reverse=True)
    c0, c1, c2 = st.columns([1, 3, 2], vertical_alignment="bottom")
    season = c0.selectbox(t("predict.season"), seasons, index=seasons.index(SEASON) if SEASON in seasons else 0)
    evs = data.events[data.events.season == season].sort_values("round").set_index("round")
    rounds = list(evs.index)
    rnd = c1.selectbox(t("predict.gp"), rounds, index=rounds.index(nr) if season == SEASON and nr in rounds else 0,
                       format_func=lambda r: f"{r}. {evs.loc[r, 'name']} ({evs.loc[r, 'circuit']})", key=f"gp_{season}")
    ev_sess = data.session_rows(season, rnd)
    ev_sess = ev_sess[ev_sess.session.isin(COMPETITIVE)].sort_values("date_utc").set_index("session")
    if ev_sess.empty:
        ui.note(t("predict.no_data_title"), t("predict.no_data"))
        st.stop()
    codes = list(ev_sess.index)
    session = c2.selectbox(t("predict.session"), codes,
                           index=codes.index(ns) if (season, rnd) == (SEASON, nr) and ns in codes else 0,
                           format_func=lambda c: f"{SESSION[c]} – {local(ev_sess.date_utc[c])}",
                           key=f"ses_{season}_{rnd}")

srow, ev, kind = ev_sess.loc[session], evs.loc[rnd], kind_of(session)
done = srow.status == "ok"
start = datetime.fromisoformat(srow.date_utc).astimezone()
event_meta = [SESSION[session], f"{t(f'weekday.{start.weekday()}')} {start:%m-%d %H:%M}", ev.circuit,
              t("predict.status_done" if done else "predict.status_upcoming")]
teams = data.teams(season)
TABS = ("predict", "track", "upgrades", "news", "model")
tab = dict(zip(TABS, st.tabs([t(f"tab.{k}") for k in TABS])))

# ------------------------------------------------------------------ spėjimas

with tab["predict"]:
    if done:  # įvykusi sesija – spėjame taip, lyg būtume prieš ją
        w = weights_before(version(app), kind, srow.date_utc, data)
        out = model.predict(data, season, rnd, session, before=srow.date_utc, weights=w)
    else:
        out = model.predict(data, season, rnd, session, weights=fitted[kind][0])
    head, action = st.columns([4, 1.3], vertical_alignment="bottom")
    with head:
        ui.event_title(f"{season} {ev['name']}", event_meta, highlight=SESSION[session])
    if action.button(t("predict.save"), width="stretch"):
        model.save_prediction(app.db, season, rnd, session, out)
        report.write(app.report_path, data, fitted, last=(ev["name"], session, out, ev.circuit))
        st.toast(t("predict.saved"))
    if done:
        actual = data.top3(season, rnd, session)
        ui.note(t("predict.done_title"), t("predict.done_text", actual=" – ".join(actual),
                                           points=model.score(out["pick"], actual)), color=ui.MUTED)
    ui.label(t("predict.pick"))
    ui.pick_cards(out["pick"], out["table"], teams, ref.team_color, t("pick.exact"), t("pick.top3"))
    if pd.notna(srow.track_rain_frac):
        rain_sub = t("rain.track", frac=f"{srow.track_rain_frac:.0%}")
    elif pd.notna(srow.fc_pop):
        rain_sub = t("rain.forecast", mm=f"{srow.rain_mm or 0:.1f}", region=f"{srow.region_rain_mm:.1f}")
    else:
        rain_sub = t("rain.none")
    ui.tiles([(t("tile.expected"), f"{out['expected']:.2f}", t("tile.expected_sub")),
              (t("tile.rain"), f"{out['rain']:.0%}", rain_sub),
              (t("tile.temp"), f"{srow.temp_c:.0f} °C" if pd.notna(srow.temp_c) else "–", t("tile.temp_sub")),
              (t("track.overtaking"), f"{ref.tracks.overtaking(ev.location):g}/5", t("track.overtaking_d"))])
    if out["rain"] >= 0.5:
        ui.note(t("rain.note_title"), t("rain.note"))
    left, right = st.columns([3, 2], gap="large")
    with left:
        ui.section(t("section.probabilities"), t("section.probabilities_sub"))
        ui.probability_table(out["table"], teams, ref.team_color, t("col.driver"), t("col.team"))
    with right:
        weekend_panel(season, rnd, session, ev, out["table"].index[:8], teams)
        st.caption(t("track.hint"))

# ------------------------------------------------------------------ trasa

with tab["track"]:
    tc, info = ref.tracks, app.track_info(data)
    profile = info.profile(ev.circuit)
    street = bool(profile.get("gatve"))
    left, right = st.columns([1.15, 1], gap="large")
    with left:
        ui.track_card(ev.circuit, f"{ev['country']} · {ev['name']}", ui.load_outline(app.db, ev.circuit), [
            (t("track.tyres"), f"{tc.tyre_severity(ev.location):g}/5 ", tc.tyre_severity(ev.location)),
            (t("track.overtaking"), f"{tc.overtaking(ev.location):g}/5 ", tc.overtaking(ev.location)),
            (t("track.similar"), ", ".join(f"{c} {s:.0%}" for c, s in tc.most_similar(ev.circuit, 3)), None),
            (t("track.format"), t("track.sprint" if ev.format and "sprint" in ev.format else "track.conventional"),
             None)], t("track.no_map"))
        ui.section(t("track.strategy"))
        for n in strategy_notes(ev.location, street):
            ui.note("", n, color=ui.LINE)
    with right:
        ui.section(t("track.character"), t("track.character_sub"))
        items = [(t(f"track.{key}"), f"{profile[col]:g}/5 ", profile[col], t(f"track.{key}_d"))
                 for key, col in (("speed", "greitis"), ("downforce", "prispaudimas"), ("tyres", "padangos"),
                                  ("overtaking", "lenkimo_sunkumas")) if col in profile]
        items.append((t("track.street"), t("track.yes" if street else "track.no"), None, t("track.street_d")))
        ui.profile_grid(items)

    ui.section(t("track.schedule"), t("track.schedule_sub"))
    wk = info.weekend(season, rnd)
    status = {"ok": t("predict.status_done")}
    ui.plain_table(
        [t(f"track.col.{c}") for c in ("session", "time", "status", "rain", "temp", "source", "top3")],
        [[html.escape(SESSION.get(r.session, r.session)),
          f"{t(f'weekday.{datetime.fromisoformat(r.date_utc).astimezone().weekday()}')} {local(r.date_utc)}",
          html.escape(status.get(r.status, t("predict.status_upcoming"))),
          f"{r.rain_prob:.0%}" if pd.notna(r.rain_prob) else "–",
          f"{r.temp_c:.0f} °C" if pd.notna(r.temp_c) else "–",
          html.escape(t.get(f"wsource.{r.weather_source}", r.weather_source) if r.weather_source else "–"),
          html.escape(r.top3) or "–"] for r in wk.itertuples()],
        classes=["b", "", "m", "b", "", "m", "b"],
        row_classes=["hot" if r.session == session else "" for r in wk.itertuples()])

    c_pod, c_drv = st.columns([1, 1.3], gap="large")
    with c_pod:
        ui.section(t("track.podiums"), t("track.podiums_sub"))
        pod = info.podiums(ev.circuit, season)
        if pod.empty:
            st.caption(t("track.no_history"))
        else:
            rows = []
            for r in pod.itertuples():   # komandos spalva – tų metų komandos
                yt = data.teams(r.season)
                rows.append([str(r.season)] + [ui.driver_cell(d, yt.get(d, ""), ref.team_color)
                                               for d in (r.P1, r.P2, r.P3, r.pole)])
            ui.plain_table([t("track.col.year"), t("track.col.winner"), "P2", "P3", t("track.col.pole")], rows,
                           classes=["b", "", "", "", ""])
    with c_drv:
        ui.section(t("track.drivers"), t("track.drivers_sub"))
        drv = info.drivers(ev.circuit, season, data.entry_list(season, rnd, session))
        if drv.empty:
            st.caption(t("track.no_history"))
        else:
            fmt = lambda v: "–" if pd.isna(v) else f"{v:g}"
            ui.plain_table([t(f"track.col.{c}") if c != "driver" else t("col.driver")
                            for c in ("driver", "starts", "avg", "best", "podiums", "wins", "avg_quali")],
                           [[ui.driver_cell(d, teams.get(d, ""), ref.team_color), fmt(r.starts), fmt(r.avg),
                             fmt(r.best), fmt(r.podiums), fmt(r.wins), fmt(r.avg_quali)] for d, r in drv.iterrows()],
                           classes=["", "m", "b", "", "", "", "m"])

# ------------------------------------------------------------------ bolidų atnaujinimai

with tab["upgrades"]:
    brief = app.briefing()
    st.write(t("upgrades.intro"))
    up_seasons = [s for s in sorted(data.events.season.unique(), reverse=True) if brief.upgrade_rounds(s)]
    if not up_seasons:
        st.caption(t("upgrades.none_yet"))
    else:
        u0, u1, _ = st.columns([1, 3, 2], vertical_alignment="bottom")
        up_season = u0.selectbox(t("predict.season"), up_seasons, key="up_season")
        up_rounds = dict(brief.upgrade_rounds(up_season))
        up_rnd = u1.selectbox(t("upgrades.round"), list(up_rounds)[::-1], format_func=lambda r: f"{r}. {up_rounds[r]}",
                              key=f"up_round_{up_season}")
        reasons = {r: t(f"reason.{r}") for r in ("performance", "circuit", "reliability")}
        doc = brief.upgrade_document(up_season, up_rnd)
        if doc:
            st.markdown(f'{t("upgrades.source")}: <a class="f1-link" href="{doc}" target="_blank" rel="noopener">'
                        f'{t("upgrades.full_doc")}</a>', unsafe_allow_html=True)
        ui.section(t("upgrades.team_title"), t("upgrades.team_sub"))
        ui.upgrade_cards(brief.upgrades(up_season, up_rnd), reasons, t("upgrades.empty"),
                         {"source": t("upgrades.source"), "doc": t("upgrades.doc"),
                          "doc_page": t("upgrades.doc_page"), "articles": t("upgrades.articles")})
        ui.section(t("upgrades.season_title"), t("upgrades.season_sub"))
        ui.heat_table(brief.upgrade_matrix(up_season), t("col.team"), ref.team_color)
        st.caption(t("upgrades.note"))

# ------------------------------------------------------------------ naujienos

with tab["news"]:
    brief = app.briefing()
    st.write(t("news.intro"))
    team_names = {k: v[0] for k, v in brief.teams(SEASON).items()}
    n0, n1, n2, n3, n4 = st.columns([2, 2, 2, 2, 1], vertical_alignment="bottom")
    f_teams = n0.multiselect(t("news.teams"), list(team_names), format_func=team_names.get, placeholder=t("news.all"))
    f_tags = n1.multiselect(t("news.tags"), brief.news_tags(), format_func=lambda g: t(f"newstag.{g}"),
                            placeholder=t("news.all"))
    f_src = n2.multiselect(t("news.sources"), brief.news_sources(), placeholder=t("news.all"))
    f_text = n3.text_input(t("news.search"))
    f_days = n4.selectbox(t("news.period"), [7, 30, 120], index=1, format_func=lambda n: t("news.days", n=n))
    found = brief.news(f_days, f_teams, f_tags, f_src, f_text.strip())
    st.caption(t("news.count", n=len(found)))
    if found.empty:
        st.caption(t("news.none"))
    else:
        ui.news_list(news_rows(found, team_names))

# ------------------------------------------------------------------ modelis ir duomenys

with tab["model"]:
    st.caption(t("model.intro"))
    with st.container(key="model_area"):
        SUB = ("why", "features", "backtest", "params", "sql", "data")
        sub = dict(zip(SUB, st.tabs([t(f"tab.{k}") for k in SUB])))

with sub["why"]:
    ui.event_title(f"{season} {ev['name']}", event_meta, highlight=SESSION[session])
    ui.section(t("section.why"), t("section.why_sub"))
    ch = 1.0 - S.wet_chaos * out["rain"]
    ui.contribution_chart(pd.DataFrame({LABEL[f]: out["table"][f] * w * ch for f, w in out["weights"].items()}).head(8),
                          t("col.driver"), t("why.value"), t("features.col.feature"))
    ui.section(t("features.values", event=ev["name"], session=SESSION[session]), t("features.values_sub"))
    st.dataframe(out["table"][features.names()].rename(columns=LABEL).round(2), width="stretch")

with sub["features"]:
    (w_q, _), (w_r, _) = fitted["quali"], fitted["race"]
    s_q, s_r = (model.importance(model.effective_weights(w, S)) for w in (w_q, w_r))
    st.markdown(t("features.intro"))
    b1, b2, _ = st.columns([1, 1, 3])
    if b1.button(t("features.save"), width="stretch"):
        app.save_settings()
        st.toast(t("features.saved"))
    if b2.button(t("features.reset"), width="stretch"):
        for f in features.names():
            st.session_state[f"mult_{f}"] = S.multipliers[f] = 1.0
        st.rerun()
    widths = [2.5, 5, 1.4, 1.4, 2.5]
    for col, key in zip(st.columns(widths), ["feature", "meaning", "quali", "race", "multiplier"]):
        col.markdown(f"**{t(f'features.col.{key}')}**")
    for f in features.REGISTRY.values():
        c = st.columns(widths, vertical_alignment="center")
        c[0].markdown(f"**{LABEL[f.name]}**  \n`{f.name}`")
        c[1].caption(t.get(f"feature.{f.name}.desc", f.description))
        for col, w, s in ((c[2], w_q, s_q), (c[3], w_r, s_r)):
            col.markdown(ui.weight_badge(w[f.name], t("features.share", share=f"{s[f.name]:.0%}")),
                         unsafe_allow_html=True)
        init = {} if f"mult_{f.name}" in st.session_state else {"value": S.multiplier(f.name)}
        c[4].slider(LABEL[f.name], 0.0, 2.0, step=0.1, key=f"mult_{f.name}", label_visibility="collapsed", **init)
        st.divider()

with sub["backtest"]:
    st.write(t("backtest.intro") + (" " + t("backtest.intro_players") if app.has_excel else ""))
    st.caption(t("backtest.run_help"))
    if st.button(t("backtest.run"), type="primary"):
        bar = st.progress(0.0)
        fresh = app.dataset()
        st.session_state["bt"] = backtest.run(fresh, app.excel().read(fresh.events[fresh.events.season == SEASON]),
                                              progress=lambda f: bar.progress(f, text=f"{f:.0%}"))
        bar.empty()
    if "bt" in st.session_state:
        df = st.session_state["bt"]
        cols = backtest.score_columns(df, ref.players)
        ui.section(t("backtest.total"))
        st.bar_chart(df[cols].sum().sort_values(ascending=False), color=ui.RED)
        ui.section(t("backtest.sessions"))
        st.dataframe(df.drop(columns="round"), width="stretch", hide_index=True)
        ui.section(t("backtest.by_type"))
        st.dataframe(df.groupby("session")[cols].sum().rename(index=SESSION), width="stretch")

with sub["params"]:
    if t.lang != DEFAULT_LANGUAGE:
        st.caption(t("params.language_note"))
    if st.button(t("params.refresh")) or not app.report_path.exists():
        report.write(app.report_path, data, fitted)
    st.markdown(app.report_path.read_text(encoding="utf-8"))

with sub["sql"]:
    left, right = st.columns([3, 1], gap="large")
    with right:
        ui.section(t("sql.tables"), t("sql.tables_sub"))
        for name, cols in app.db.schema().items():
            if name not in visible([name]):
                continue
            with st.expander(name):
                st.caption(t.get(f"tableinfo.{name}", ""))
                st.code(", ".join(cols), language=None, wrap_lines=True)
    with left:
        ex = st.selectbox(t("sql.examples"), [None, *visible(SQL_EXAMPLES)],
                          format_func=lambda k: t(f"sql.example.{k}") if k else t("sql.pick_example"))
        if ex in SQL_EXAMPLES and st.session_state.get("sql_example") != ex:
            st.session_state.update(sql_example=ex, sql_text=SQL_EXAMPLES[ex])
        sql = st.text_area(t("sql.query"), key="sql_text", height=200,
                           placeholder="SELECT * FROM v_rezultatai WHERE metai = 2026 LIMIT 100;")
        st.caption(t("sql.readonly"))
        if st.button(t("sql.run"), type="primary") and sql.strip():
            try:
                st.session_state["sql_result"] = app.db.read_only_query(sql.strip().rstrip(";"))
            except Exception as e:
                st.session_state.pop("sql_result", None)
                st.error(t("sql.error", error=e))
        if "sql_result" in st.session_state:
            df, more = st.session_state["sql_result"]
            st.caption(t("sql.rows", n=len(df)) + (t("sql.truncated") if more else ""))
            st.dataframe(df, width="stretch", hide_index=True, height=480)
            st.download_button(t("sql.download"), df.to_csv(index=False).encode("utf-8-sig"), "uzklausa.csv",
                               "text/csv")

with sub["data"]:
    ui.section(t("data.reference"), t("data.reference_sub"))
    table = st.selectbox(t("data.table"), visible(REFERENCE_TABLES), format_func=lambda k: t(f"reftable.{k}"))
    edited = st.data_editor(app.db.query(f"SELECT * FROM {table}"), num_rows="dynamic", width="stretch",
                            hide_index=True, key=f"edit_{table}")
    e1, e2, _ = st.columns([1, 1, 3])
    if e1.button(t("data.save"), type="primary", width="stretch"):
        app.save_reference(table, edited.dropna(subset=[edited.columns[0]]).to_dict("records"))
        st.cache_resource.clear()
        st.rerun()
    if e2.button(t("data.defaults"), width="stretch"):
        app.save_reference(table, app.default_rows(table))
        st.cache_resource.clear()
        st.rerun()
    ui.section(t("data.collected"), t("data.collected_sub"))
    st.dataframe(data.sess[data.sess.status == "ok"].groupby(["season", "session"]).size().unstack(fill_value=0),
                 width="stretch")
