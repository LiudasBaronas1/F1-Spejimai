"""Naujienos: visos naujienos su filtrais (komanda, tema, šaltinis, paieška, laikotarpis)."""
import streamlit as st

import ui_style as ui
from f1model.config import SEASON

from .common import news_rows, team_names


def render(c):
    t, brief = c.t, c.briefing
    st.write(t("news.intro"))
    names = team_names(c, SEASON)
    n0, n1, n2, n3, n4 = st.columns([2, 2, 2, 2, 1], vertical_alignment="bottom")
    f_teams = n0.multiselect(t("news.teams"), list(names), format_func=names.get, placeholder=t("news.all"))
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
        ui.news_list(news_rows(c, found, names))
