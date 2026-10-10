"""Programos puslapiai (meniu kairėje): Artimiausia sesija · Etapas · Sezonas · Naujienos · Modelis · Duomenys.
Kiekvienas puslapis – funkcija, gaunanti `Ctx` (programa, vertėjas, duomenys, apmokytas modelis)."""
import html
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable

import pandas as pd
import streamlit as st

import ui_style as ui
from f1model import backtest, features, model, report, status
from f1model.config import COMPETITIVE, DONE_STATUSES, SEASON
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
CHECK_ORDER = ("results", "practice", "grid", "weather", "odds", "news")


@dataclass
class Ctx:
    app: object
    t: object
    data: object
    fitted: dict
    version: tuple
    weights_before: Callable          # (kind, upto) -> svoriai, mokant rodomas eigos skydelis
    request_update: Callable          # paleidžia duomenų atnaujinimą

    @property
    def S(self):
        return self.data.settings

    @property
    def ref(self):
        return self.data.ref

    @property
    def session_names(self):
        return self.t.prefixed("session", ["FP1", "FP2", "FP3", "SQ", "S", "Q", "R"])

    @property
    def labels(self):
        return {f: self.t.get(f"feature.{f}.label", x.label) for f, x in features.REGISTRY.items()}

    def visible(self, keys):
        return [k for k in keys if self.app.has_excel or k not in EXCEL_ONLY]


# ------------------------------------------------------------------ pagalbinės

def local(iso, fmt="%m-%d %H:%M"):
    return datetime.fromisoformat(iso).astimezone().strftime(fmt)


def when(c, iso):
    d = datetime.fromisoformat(iso).astimezone()
    return f"{c.t(f'weekday.{d.weekday()}')} {d:%m-%d %H:%M}"


def countdown(iso):
    left = datetime.fromisoformat(iso) - datetime.now(timezone.utc)
    secs = int(left.total_seconds())
    if secs <= 0:
        return None
    d, rem = divmod(secs, 86400)
    h, m = rem // 3600, rem % 3600 // 60
    return f"{d} d {h} h" if d else f"{h} h {m:02d} min" if h else f"{m} min"


def news_rows(c, df, team_names, summary_len=None):
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
                         chips=[(team_names.get(k, k), "", c.ref.team_color(team_names.get(k, k))) for k in keys]
                         + [(c.t(f"newstag.{g}"), "tag", None) for g in tags]))
    return rows


def predict(c, season, rnd, session):
    """Spėjimas; įvykusiai sesijai – tik su iki jos žinomais duomenimis."""
    srow = c.data.session_rows(season, rnd, session).iloc[0]
    if srow.status in DONE_STATUSES:
        w = c.weights_before(kind_of(session), srow.date_utc)
        return model.predict(c.data, season, rnd, session, before=srow.date_utc, weights=w)
    return model.predict(c.data, season, rnd, session, weights=c.fitted[kind_of(session)][0])


def reasons(c, out, n=2):
    """Kiekvienam spėtam vairuotojui – didžiausią teigiamą indėlį davę veiksniai."""
    ch, labels = 1.0 - c.S.wet_chaos * out["rain"], c.labels
    res = {}
    for d in out["pick"]:
        contrib = sorted(((out["table"].loc[d, f] * w * ch, f) for f, w in out["weights"].items()), reverse=True)
        res[d] = [labels[f] for v, f in contrib[:n] if v > 0.05]
    return res


def strategy_notes(c, location, street):
    tc, t = c.ref.tracks, c.t
    tyres, over = tc.tyre_severity(location), tc.overtaking(location)
    notes = [t("strategy.tyres_high" if tyres >= 4 else "strategy.tyres_low" if tyres <= 2 else "strategy.tyres_mid"),
             t("strategy.overtake_hard" if over >= 4 else "strategy.overtake_easy" if over <= 2
               else "strategy.overtake_mid")]
    return notes + ([t("strategy.street")] if street else [])


def checklist(c, season, rnd, session):
    """„Duomenys šiam spėjimui“ – kas surinkta, kas trūksta ir ką daryti."""
    t, names = c.t, c.session_names
    checks = {k.key: k for k in status.weekend_checks(c.data, c.app.db, season, rnd, session)}
    items = []
    for key in CHECK_ORDER:
        if key not in checks:
            continue
        k = checks[key]
        p = dict(k.params)
        if "sessions" in p:
            p["sessions"] = ", ".join(names.get(s, s) for s in p["sessions"])
        if "sources" in p:
            p["sources"] = ", ".join(p["sources"])
        if "age" in p:
            p["age"] = (f"{p['age'] * 60:.0f} min" if p["age"] < 1 else f"{p['age']:.0f} h")
        items.append((t(f"check.{key}"), k.state, t(k.text, **p)))
    ui.checklist(items, {s: t(f"state.{s}") for s in ("ok", "warn", "missing", "na")})
    return checks


def key_facts(c, season, rnd, session, ev, leaders, teams):
    """Svarbu šiam etapui: FIA starto baudos, komandų atnaujinimai, svarbios naujienos apie pirmaujančias komandas."""
    t, brief = c.t, c.app.briefing()
    ui.section(t("weekend.title"), t("weekend.sub"))
    if c.data.fia_grid(season, rnd, session):
        changes = brief.grid_changes(c.data, season, rnd, session)
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
    keys = {c.ref.team_key(teams.get(d)) for d in leaders} - {None}
    news = brief.weekend_news(ev["date"], keys)
    if news.empty:
        st.caption(t("weekend.no_news"))
    else:
        ui.news_list(news_rows(c, news, {k: v[0] for k, v in brief.teams(season).items()}, summary_len=160))


# ------------------------------------------------------------------ spėjimo blokas (pradžia ir etapas)

def prediction_block(c, season, rnd, session, key):
    t, S, ref, names, labels = c.t, c.S, c.ref, c.session_names, c.labels
    srow, ev = c.data.session_rows(season, rnd, session).iloc[0], c.data.event(season, rnd)
    out, teams = predict(c, season, rnd, session), c.data.teams(season)
    done = srow.status in DONE_STATUSES

    head, action = st.columns([4, 1.3], vertical_alignment="center")
    head.markdown(f"<div class='f1-label' style='margin:0'>{html.escape(t('predict.pick'))}</div>",
                  unsafe_allow_html=True)
    if action.button(t("predict.save"), width="stretch", key=f"save_{key}"):
        model.save_prediction(c.app.db, season, rnd, session, out)
        report.write(c.app.report_path, c.data, c.fitted, last=(ev["name"], session, out, ev.circuit))
        st.toast(t("predict.saved"))
    if done:
        actual = c.data.top3(season, rnd, session)
        ui.note(t("predict.done_title"), t("predict.done_text", actual=" – ".join(actual),
                                           points=model.score(out["pick"], actual)), color=ui.MUTED)
        if srow.status == "fia":
            ui.note(t("predict.prelim_title"), t("predict.prelim_text"), color="#F5A524")
    ui.pick_cards(out["pick"], out["table"], teams, ref.team_color, t("pick.exact"), t("pick.top3"),
                  reasons(c, out), t("pick.why"))
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
        key_facts(c, season, rnd, session, ev, out["table"].index[:8], teams)
    with st.expander(t("section.why_full")):
        st.caption(t("section.why_sub"))
        ch = 1.0 - S.wet_chaos * out["rain"]
        ui.contribution_chart(pd.DataFrame({labels[f]: out["table"][f] * w * ch
                                            for f, w in out["weights"].items()}).head(8),
                              t("col.driver"), t("why.value"), t("features.col.feature"))
        ui.label(t("features.values", event=ev["name"], session=names[session]))
        st.caption(t("features.values_sub"))
        st.dataframe(out["table"][features.names()].rename(columns=labels).round(2), width="stretch")


# ------------------------------------------------------------------ 1. Artimiausia sesija

def page_next(c):
    t, data, names = c.t, c.data, c.session_names
    nr, ns = data.next_session((datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat())
    if nr is None:  # sezonas baigėsi – paskutinė įvykusi sesija
        last = data.done_sessions([SEASON], COMPETITIVE, by_date=True)
        if last.empty:
            return ui.note(t("predict.no_data_title"), t("predict.no_data"))
        nr, ns = int(last.iloc[-1]["round"]), last.iloc[-1].session
    ev, srow = data.event(SEASON, nr), data.session_rows(SEASON, nr, ns).iloc[0]
    left, right = st.columns([5, 1.2], vertical_alignment="bottom")
    with left:
        ui.hero(t("next.kicker"), f"{ev['name']} · {names[ns]}",
                [when(c, srow.date_utc), ev.circuit, ev["country"],
                 t("track.sprint" if ev.format and "sprint" in ev.format else "track.conventional")],
                countdown(srow.date_utc), t("next.starts_in"))
    with right:
        if st.button(t("sidebar.update"), type="primary", width="stretch", key="update_hero"):
            c.request_update()
        st.caption(t("next.update_hint"))
    ui.label(t("next.data_title"))
    checklist(c, SEASON, nr, ns)
    prediction_block(c, SEASON, nr, ns, "next")


# ------------------------------------------------------------------ 2. Etapas

def page_weekend(c):
    t, data, names, ref = c.t, c.data, c.session_names, c.ref
    nr, ns = data.next_session((datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat())
    with st.container(key="context"):
        c0, c1 = st.columns([1, 4], vertical_alignment="bottom")
        seasons = sorted(data.events.season.unique(), reverse=True)
        season = c0.selectbox(t("predict.season"), seasons, index=seasons.index(SEASON) if SEASON in seasons else 0)
        evs = data.events[data.events.season == season].sort_values("round").set_index("round")
        rounds = list(evs.index)
        rnd = c1.selectbox(t("predict.gp"), rounds, index=rounds.index(nr) if season == SEASON and nr in rounds else 0,
                           format_func=lambda r: f"{r}. {evs.loc[r, 'name']} ({evs.loc[r, 'circuit']})",
                           key=f"gp_{season}")
        sess = data.session_rows(season, rnd)
        sess = sess[sess.session.isin(COMPETITIVE)].sort_values("date_utc").set_index("session")
        if sess.empty:
            ui.note(t("predict.no_data_title"), t("predict.no_data"))
            return
        codes = list(sess.index)
        default = ns if (season, rnd) == (SEASON, nr) and ns in codes else codes[-1]
        mark = lambda code: "" if sess.status[code] in DONE_STATUSES else " · " + t("predict.status_upcoming")
        session = st.segmented_control(t("predict.session"), codes, default=default, key=f"seg_{season}_{rnd}",
                                       format_func=lambda code: f"{names[code]} – {when(c, sess.date_utc[code])}"
                                                                f"{mark(code)}") or default
    ev = evs.loc[rnd]
    ui.event_title(f"{season} {ev['name']}", [names[session], when(c, sess.date_utc[session]), ev.circuit,
                                              t("predict.status_done" if sess.status[session] in DONE_STATUSES
                                                else "predict.status_upcoming")], highlight=names[session])
    tabs = st.tabs([t("weekend.tab_pick"), t("weekend.tab_track"), t("weekend.tab_news")])
    with tabs[0]:
        prediction_block(c, season, rnd, session, "weekend")
    with tabs[1]:
        track_view(c, season, rnd, session, ev)
    with tabs[2]:
        weekend_news_view(c, season, rnd, ev)


def track_view(c, season, rnd, session, ev):
    t, tc, names, ref = c.t, c.ref.tracks, c.session_names, c.ref
    info, teams = c.app.track_info(c.data), c.data.teams(season)
    profile = info.profile(ev.circuit)
    street = bool(profile.get("gatve"))
    left, right = st.columns([1.15, 1], gap="large")
    with left:
        ui.track_card(ev.circuit, f"{ev['country']} · {ev['name']}", ui.load_outline(c.app.db, ev.circuit), [
            (t("track.tyres"), f"{tc.tyre_severity(ev.location):g}/5 ", tc.tyre_severity(ev.location)),
            (t("track.overtaking"), f"{tc.overtaking(ev.location):g}/5 ", tc.overtaking(ev.location)),
            (t("track.similar"), ", ".join(f"{x} {s:.0%}" for x, s in tc.most_similar(ev.circuit, 3)), None),
            (t("track.format"), t("track.sprint" if ev.format and "sprint" in ev.format else "track.conventional"),
             None)], t("track.no_map"))
    with right:
        ui.section(t("track.character"), t("track.character_sub"))
        items = [(t(f"track.{key}"), f"{profile[col]:g}/5 ", profile[col], t(f"track.{key}_d"))
                 for key, col in (("speed", "greitis"), ("downforce", "prispaudimas"), ("tyres", "padangos"),
                                  ("overtaking", "lenkimo_sunkumas")) if col in profile]
        items.append((t("track.street"), t("track.yes" if street else "track.no"), None, t("track.street_d")))
        ui.profile_grid(items)
        ui.section(t("track.strategy"))
        for n in strategy_notes(c, ev.location, street):
            ui.note("", n, color=ui.LINE)

    ui.section(t("track.schedule"), t("track.schedule_sub"))
    wk = info.weekend(season, rnd)
    state = {"ok": t("predict.status_done"), "fia": t("state.prelim")}
    ui.plain_table(
        [t(f"track.col.{x}") for x in ("session", "time", "status", "rain", "temp", "source", "top3")],
        [[html.escape(names.get(r.session, r.session)), when(c, r.date_utc),
          html.escape(state.get(r.status, t("predict.status_upcoming"))),
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
                yt = c.data.teams(r.season)
                rows.append([str(r.season)] + [ui.driver_cell(d, yt.get(d, ""), ref.team_color)
                                               for d in (r.P1, r.P2, r.P3, r.pole)])
            ui.plain_table([t("track.col.year"), t("track.col.winner"), "P2", "P3", t("track.col.pole")], rows,
                           classes=["b", "", "", "", ""])
    with c_drv:
        ui.section(t("track.drivers"), t("track.drivers_sub"))
        drv = info.drivers(ev.circuit, season, c.data.entry_list(season, rnd, session))
        if drv.empty:
            st.caption(t("track.no_history"))
        else:
            fmt = lambda v: "–" if pd.isna(v) else f"{v:g}"
            ui.plain_table([t(f"track.col.{x}") if x != "driver" else t("col.driver")
                            for x in ("driver", "starts", "avg", "best", "podiums", "wins", "avg_quali")],
                           [[ui.driver_cell(d, teams.get(d, ""), ref.team_color), fmt(r.starts), fmt(r.avg),
                             fmt(r.best), fmt(r.podiums), fmt(r.wins), fmt(r.avg_quali)] for d, r in drv.iterrows()],
                           classes=["", "m", "b", "", "", "", "m"])


def weekend_news_view(c, season, rnd, ev):
    t, brief, ref = c.t, c.app.briefing(), c.ref
    ui.section(t("upgrades.team_title"), t("upgrades.round_sub"))
    reasons_ = {r: t(f"reason.{r}") for r in ("performance", "circuit", "reliability")}
    doc = brief.upgrade_document(season, rnd)
    if doc:
        st.markdown(f'{t("upgrades.source")}: <a class="f1-link" href="{doc}" target="_blank" rel="noopener">'
                    f'{t("upgrades.full_doc")}</a>', unsafe_allow_html=True)
    ups = brief.upgrades(season, rnd)
    if ups:
        ui.upgrade_cards(ups, reasons_, t("upgrades.empty"),
                         {"source": t("upgrades.source"), "doc": t("upgrades.doc"),
                          "doc_page": t("upgrades.doc_page"), "articles": t("upgrades.articles")})
    else:
        st.caption(t("weekend.no_upgrades"))
    ui.section(t("news.weekend_title"), t("news.weekend_sub"))
    news = brief.weekend_news(ev["date"], set(brief.teams(season)))
    if news.empty:
        st.caption(t("news.none"))
    else:
        ui.news_list(news_rows(c, news, {k: v[0] for k, v in brief.teams(season).items()}))


# ------------------------------------------------------------------ 3. Sezonas

def page_season(c):
    t, data, names, ref = c.t, c.data, c.session_names, c.ref
    seasons = sorted(data.events.season.unique(), reverse=True)
    season = st.selectbox(t("predict.season"), seasons, index=seasons.index(SEASON) if SEASON in seasons else 0,
                          key="season_page")
    tabs = st.tabs([t("season.tab_calendar"), t("season.tab_backtest"), t("season.tab_upgrades")])
    with tabs[0]:
        ui.section(t("season.calendar"), t("season.calendar_sub"))
        evs = data.events[data.events.season == season].sort_values("round")
        nr, _ = data.next_session((datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat())
        teams, rows, hot = data.teams(season), [], []
        cell = lambda d: ui.driver_cell(d, teams.get(d, ""), ref.team_color)
        for e in evs.itertuples():
            s = data.session_rows(season, e.round)
            done = s[s.session.isin(COMPETITIVE)].status.isin(DONE_STATUSES)
            state = (t("season.done") if len(done) and done.all() else
                     t("season.next") if season == SEASON and e.round == nr else
                     t("season.live") if done.any() else t("predict.status_upcoming"))
            race, pole = data.top3(season, e.round, "R"), data.top3(season, e.round, "Q")[:1]
            rows.append([str(e.round), html.escape(e.name.replace(" Grand Prix", "")), html.escape(e.circuit),
                         e.date, html.escape(t("track.sprint" if e.format and "sprint" in e.format else "season.std")),
                         html.escape(state), cell(pole[0]) if pole else "–",
                         " ".join(cell(d) for d in race) if race else "–"])
            hot.append("hot" if season == SEASON and e.round == nr else "")
        ui.plain_table([t("season.col.round"), "Grand Prix", t("track.col.circuit"), t("season.col.date"),
                        t("track.format"), t("track.col.status"), t("track.col.pole"), t("season.col.podium")],
                       rows, classes=["b", "b", "m", "m", "m", "", "", ""], row_classes=hot)
    with tabs[1]:
        backtest_view(c, season)
    with tabs[2]:
        brief = c.app.briefing()
        if not brief.upgrade_rounds(season):
            st.caption(t("upgrades.none_yet"))
        else:
            ui.section(t("upgrades.season_title"), t("upgrades.season_sub"))
            ui.heat_table(brief.upgrade_matrix(season), t("col.team"), ref.team_color)
            st.caption(t("upgrades.note"))


def backtest_view(c, season):
    t, app = c.t, c.app
    st.write(t("backtest.intro") + (" " + t("backtest.intro_players") if app.has_excel and season == SEASON else ""))
    st.caption(t("backtest.run_help"))
    if st.button(t("backtest.run"), type="primary"):
        bar = st.progress(0.0)
        fresh = app.dataset()
        picks = app.excel().read(fresh.events[fresh.events.season == SEASON]) if season == SEASON else \
            pd.DataFrame(columns=["round", "session", "player", "pos", "predicted"])
        st.session_state[f"bt_{season}"] = backtest.run(fresh, picks, season=season,
                                                        progress=lambda f: bar.progress(f, text=f"{f:.0%}"))
        bar.empty()
    df = st.session_state.get(f"bt_{season}")
    if df is not None and not df.empty:
        cols = backtest.score_columns(df, c.ref.players)
        ui.section(t("backtest.total"))
        st.bar_chart(df[cols].sum().sort_values(ascending=False), color=ui.RED)
        ui.section(t("backtest.sessions"))
        st.dataframe(df.drop(columns="round"), width="stretch", hide_index=True)
        ui.section(t("backtest.by_type"))
        st.dataframe(df.groupby("session")[cols].sum().rename(index=c.session_names), width="stretch")


# ------------------------------------------------------------------ 4. Naujienos

def page_news(c):
    t, brief = c.t, c.app.briefing()
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
        ui.news_list(news_rows(c, found, team_names))


# ------------------------------------------------------------------ 5. Modelis

def page_model(c):
    t, S, labels = c.t, c.S, c.labels
    tabs = st.tabs([t("model.tab_how"), t("model.tab_factors"), t("model.tab_params")])
    (w_q, n_q), (w_r, n_r) = c.fitted["quali"], c.fitted["race"]
    s_q, s_r = (model.importance(model.effective_weights(w, S)) for w in (w_q, w_r))
    with tabs[0]:
        for i in range(1, 6):
            ui.note(f"{i}.", t(f"model.how.{i}"), color=ui.RED)
        ui.section(t("model.importance"), t("model.importance_sub", q=n_q, r=n_r))
        ui.importance_chart(pd.DataFrame({t("features.col.quali"): s_q, t("features.col.race"): s_r})
                            .rename(index=labels), t("model.share"))
        st.caption(t("model.accuracy"))
    with tabs[1]:
        st.markdown(t("features.intro"))
        b1, b2, _ = st.columns([1, 1, 3])
        if b1.button(t("features.save"), width="stretch"):
            c.app.save_settings()
            st.toast(t("features.saved"))
        if b2.button(t("features.reset"), width="stretch"):
            for f in features.names():
                st.session_state[f"mult_{f}"] = S.multipliers[f] = 1.0
            st.rerun()
        widths = [2.5, 5, 1.4, 1.4, 2.5]
        for col, key in zip(st.columns(widths), ["feature", "meaning", "quali", "race", "multiplier"]):
            col.markdown(f"**{t(f'features.col.{key}')}**")
        for f in features.REGISTRY.values():
            cols = st.columns(widths, vertical_alignment="center")
            cols[0].markdown(f"**{labels[f.name]}**  \n`{f.name}`")
            cols[1].caption(t.get(f"feature.{f.name}.desc", f.description))
            for col, w, s in ((cols[2], w_q, s_q), (cols[3], w_r, s_r)):
                col.markdown(ui.weight_badge(w[f.name], t("features.share", share=f"{s[f.name]:.0%}")),
                             unsafe_allow_html=True)
            init = {} if f"mult_{f.name}" in st.session_state else {"value": S.multiplier(f.name)}
            cols[4].slider(labels[f.name], 0.0, 2.0, step=0.1, key=f"mult_{f.name}", label_visibility="collapsed",
                           **init)
            st.divider()
    with tabs[2]:
        if t.lang != DEFAULT_LANGUAGE:
            st.caption(t("params.language_note"))
        if st.button(t("params.refresh")) or not c.app.report_path.exists():
            report.write(c.app.report_path, c.data, c.fitted)
        st.markdown(c.app.report_path.read_text(encoding="utf-8"))


# ------------------------------------------------------------------ 6. Duomenys

def page_data(c):
    t, app, data = c.t, c.app, c.data
    tabs = st.tabs([t("data.tab_status"), t("data.tab_sql"), t("data.tab_reference")])
    with tabs[0]:
        ui.section(t("data.status_title"), t("data.status_sub"))
        st.write(t("data.status_help"))
        matrix = status.season_matrix(data, SEASON)
        matrix = matrix[[x for x in ("FP1", "FP2", "FP3", "SQ", "S", "Q", "R") if x in matrix.columns]]
        ui.state_table(matrix.rename(columns=c.session_names), t("season.col.round"),
                       {"ok": t("state.official"), "fia": t("state.prelim"), "missing": t("state.missing_data"),
                        "upcoming": t("predict.status_upcoming")})
        ui.section(t("data.collected"), t("data.collected_sub"))
        st.dataframe(data.sess[data.sess.status.isin(DONE_STATUSES)].groupby(["season", "session"]).size()
                     .unstack(fill_value=0), width="stretch")
    with tabs[1]:
        left, right = st.columns([3, 1], gap="large")
        with right:
            ui.section(t("sql.tables"), t("sql.tables_sub"))
            for name, cols in app.db.schema().items():
                if name not in c.visible([name]):
                    continue
                with st.expander(name):
                    st.caption(t.get(f"tableinfo.{name}", ""))
                    st.code(", ".join(cols), language=None, wrap_lines=True)
        with left:
            ex = st.selectbox(t("sql.examples"), [None, *c.visible(SQL_EXAMPLES)],
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
    with tabs[2]:
        ui.section(t("data.reference"), t("data.reference_sub"))
        table = st.selectbox(t("data.table"), c.visible(REFERENCE_TABLES), format_func=lambda k: t(f"reftable.{k}"))
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
