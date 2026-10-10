"""Duomenys: kiekvienos sezono sesijos duomenų būklė ir redaguojami žinynai."""
import streamlit as st

import ui_style as ui
from f1model import status
from f1model.config import DONE_STATUSES, SEASON

REFERENCE_TABLES = ["trasos", "trasu_sinonimai", "komandos", "zaidejai", "gp_pavadinimai", "vairuotoju_vardai",
                    "naujienu_saltiniai", "naujienu_zymes", "vertimai", "kalbos"]
EXCEL_ONLY = {"zaidejai", "gp_pavadinimai"}   # rodomi tik turint asmeninę totalizatoriaus Excel lentelę


def render(c):
    t = c.t
    tabs = st.tabs([t("data.tab_status"), t("data.tab_reference")])
    with tabs[0]:
        season_status(c)
    with tabs[1]:
        reference_tables(c)


def season_status(c):
    t, data = c.t, c.data
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


def reference_tables(c):
    t = c.t
    ui.section(t("data.reference"), t("data.reference_sub"))
    tables = [x for x in REFERENCE_TABLES if c.has_excel or x not in EXCEL_ONLY]
    col, _ = st.columns([2, 3])
    table = col.selectbox(t("data.table"), tables, format_func=lambda k: t(f"reftable.{k}"))
    edited = st.data_editor(c.reference_rows(table), num_rows="dynamic", width="stretch", hide_index=True,
                            key=f"edit_{table}")
    e1, e2, _ = st.columns([1, 1, 3])
    if e1.button(t("data.save"), type="primary", width="stretch"):
        c.save_reference(table, edited.dropna(subset=[edited.columns[0]]).to_dict("records"))
        st.cache_resource.clear()
        st.rerun()
    if e2.button(t("data.defaults"), width="stretch"):
        c.save_reference(table, c.default_reference_rows(table))
        st.cache_resource.clear()
        st.rerun()
