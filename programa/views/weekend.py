"""Etapas: bet kuris Grand Prix ir sesija. Skirtukai: Spėjimas · Trasa ir orai · Atnaujinimai ir naujienos."""
import html

import pandas as pd
import streamlit as st

import ui_style as ui
from f1model.config import COMPETITIVE, DONE_STATUSES, SEASON

from .common import news_rows, prediction_block, team_names, when
from .next_session import upcoming


def render(c):
    t, data, names = c.t, c.data, c.session_names
    nr, ns = upcoming(data)
    with st.container(key="context"):
        c0, c1, _ = st.columns([1, 3, 2], vertical_alignment="bottom")
        seasons = sorted(data.events.season.unique(), reverse=True)
        season = c0.selectbox(t("predict.season"), seasons, index=seasons.index(SEASON) if SEASON in seasons else 0)
        evs = data.events[data.events.season == season].sort_values("round").set_index("round")
        rounds = list(evs.index)
        rnd = c1.selectbox(t("predict.gp"), rounds, index=rounds.index(nr) if season == SEASON and nr in rounds else 0,
                           format_func=lambda r: f"{r}. {evs.loc[r, 'name']}", key=f"gp_{season}")
        sess = data.session_rows(season, rnd)
        sess = sess[sess.session.isin(COMPETITIVE)].sort_values("date_utc").set_index("session")
        if sess.empty:
            ui.note(t("predict.no_data_title"), t("predict.no_data"))
            return
        codes = list(sess.index)
        default = ns if (season, rnd) == (SEASON, nr) and ns in codes else codes[-1]
        session = st.segmented_control(t("predict.session"), codes, default=default, key=f"seg_{season}_{rnd}",
                                       format_func=lambda code: f"{names[code]} · {when(c, sess.date_utc[code], True)}"
                                       ) or default
    ev = evs.loc[rnd]
    done = sess.status[session] in DONE_STATUSES
    ui.event_title(f"{season} {ev['name']}", [names[session], when(c, sess.date_utc[session]), ev.circuit,
                                              t("predict.status_done" if done else "predict.status_upcoming")],
                   highlight=names[session])
    tabs = st.tabs([t("weekend.tab_pick"), t("weekend.tab_track"), t("weekend.tab_news")])
    with tabs[0]:
        prediction_block(c, season, rnd, session, "weekend")
    with tabs[1]:
        track_view(c, season, rnd, session, ev)
    with tabs[2]:
        news_view(c, season, rnd, ev)


def strategy_notes(c, location, street):
    tc, t = c.ref.tracks, c.t
    tyres, over = tc.tyre_severity(location), tc.overtaking(location)
    notes = [t("strategy.tyres_high" if tyres >= 4 else "strategy.tyres_low" if tyres <= 2 else "strategy.tyres_mid"),
             t("strategy.overtake_hard" if over >= 4 else "strategy.overtake_easy" if over <= 2
               else "strategy.overtake_mid")]
    return notes + ([t("strategy.street")] if street else [])


def track_view(c, season, rnd, session, ev):
    t, tc, names, ref, info = c.t, c.ref.tracks, c.session_names, c.ref, c.track_info
    teams, profile = c.data.teams(season), tc.character(ev.location)
    street = bool(profile.get("gatve"))
    left, right = st.columns([1.15, 1], gap="large")
    with left:
        ui.track_card(ev.circuit, f"{ev['country']} · {ev['name']}", c.track_outline(ev.circuit), [
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


def news_view(c, season, rnd, ev):
    t, brief = c.t, c.briefing
    ui.section(t("upgrades.team_title"), t("upgrades.round_sub"))
    doc = brief.upgrade_document(season, rnd)
    if doc:
        st.markdown(f'{t("upgrades.source")}: <a class="f1-link" href="{doc}" target="_blank" rel="noopener">'
                    f'{t("upgrades.full_doc")}</a>', unsafe_allow_html=True)
    ups = brief.upgrades(season, rnd)
    if ups:
        ui.upgrade_cards(ups, {r: t(f"reason.{r}") for r in ("performance", "circuit", "reliability")},
                         t("upgrades.empty"), {"source": t("upgrades.source"), "doc": t("upgrades.doc"),
                                               "doc_page": t("upgrades.doc_page"), "articles": t("upgrades.articles")})
    else:
        st.caption(t("weekend.no_upgrades"))
    ui.section(t("news.weekend_title"), t("news.weekend_sub"))
    names = team_names(c, season)
    news = brief.weekend_news(ev["date"], set(names))
    if news.empty:
        st.caption(t("news.none"))
    else:
        ui.news_list(news_rows(c, news, names))
