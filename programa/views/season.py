"""Sezonas: kalendorius, modelis prieš žaidėjus (sezono testas), atnaujinimų apžvalga."""
import html

import streamlit as st

import ui_style as ui
from f1model import backtest
from f1model.config import COMPETITIVE, DONE_STATUSES, SEASON

from .next_session import upcoming


def render(c):
    t, data = c.t, c.data
    seasons = sorted(data.events.season.unique(), reverse=True)
    col, _ = st.columns([1, 4])
    season = col.selectbox(t("predict.season"), seasons, index=seasons.index(SEASON) if SEASON in seasons else 0,
                           key="season_page")
    tabs = st.tabs([t("season.tab_calendar"), t("season.tab_backtest"), t("season.tab_upgrades")])
    with tabs[0]:
        calendar(c, season)
    with tabs[1]:
        backtest_view(c, season)
    with tabs[2]:
        upgrades_overview(c, season)


def calendar(c, season):
    t, data, ref = c.t, c.data, c.ref
    ui.section(t("season.calendar"), t("season.calendar_sub"))
    nr, _ = upcoming(data)
    teams, rows, hot = data.teams(season), [], []
    cell = lambda d: ui.driver_cell(d, teams.get(d, ""), ref.team_color)
    for e in data.events[data.events.season == season].sort_values("round").itertuples():
        s = data.session_rows(season, e.round)
        done = s[s.session.isin(COMPETITIVE)].status.isin(DONE_STATUSES)
        is_next = season == SEASON and e.round == nr
        state = (t("season.done") if len(done) and done.all() else t("season.next") if is_next else
                 t("season.live") if done.any() else t("predict.status_upcoming"))
        race, pole = data.top3(season, e.round, "R"), data.top3(season, e.round, "Q")[:1]
        rows.append([str(e.round), html.escape(e.name.replace(" Grand Prix", "")), html.escape(e.circuit), e.date,
                     html.escape(t("track.sprint" if e.format and "sprint" in e.format else "season.std")),
                     html.escape(state), cell(pole[0]) if pole else "–",
                     " ".join(cell(d) for d in race) if race else "–"])
        hot.append("hot" if is_next else "")
    ui.plain_table([t("season.col.round"), "Grand Prix", t("track.col.circuit"), t("season.col.date"),
                    t("track.format"), t("track.col.status"), t("track.col.pole"), t("season.col.podium")],
                   rows, classes=["b", "b", "m", "m", "m", "", "", ""], row_classes=hot)


def backtest_view(c, season):
    t = c.t
    with_players = c.has_excel and season == SEASON
    st.write(t("backtest.intro") + (" " + t("backtest.intro_players") if with_players else ""))
    st.caption(t("backtest.run_help"))
    if st.button(t("backtest.run"), type="primary"):
        bar = st.progress(0.0)
        st.session_state[f"bt_{season}"] = c.run_backtest(season, with_players,
                                                          lambda f: bar.progress(f, text=f"{f:.0%}"))
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


def upgrades_overview(c, season):
    t, brief = c.t, c.briefing
    if not brief.upgrade_rounds(season):
        st.caption(t("upgrades.none_yet"))
        return
    ui.section(t("upgrades.season_title"), t("upgrades.season_sub"))
    ui.heat_table(brief.upgrade_matrix(season), t("col.team"), c.ref.team_color)
    st.caption(t("upgrades.note"))
