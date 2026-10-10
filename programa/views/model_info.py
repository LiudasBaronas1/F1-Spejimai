"""Modelis: kaip veikia, veiksniai ir svoriai (su daugikliais), parametrai."""
import pandas as pd
import streamlit as st

import ui_style as ui
from f1model import features, model
from f1model.i18n import DEFAULT_LANGUAGE


def render(c):
    t = c.t
    tabs = st.tabs([t("model.tab_how"), t("model.tab_factors"), t("model.tab_params")])
    (w_q, n_q), (w_r, n_r) = c.fitted["quali"], c.fitted["race"]
    shares = [model.importance(model.effective_weights(w, c.S)) for w in (w_q, w_r)]
    with tabs[0]:
        how_it_works(c, shares, n_q, n_r)
    with tabs[1]:
        factors(c, (w_q, w_r), shares)
    with tabs[2]:
        if t.lang != DEFAULT_LANGUAGE:
            st.caption(t("params.language_note"))
        refresh = st.button(t("params.refresh"))
        st.markdown(c.report_text(refresh))


def how_it_works(c, shares, n_q, n_r):
    t = c.t
    for i in range(1, 6):
        ui.note(f"{i}.", t(f"model.how.{i}"), color=ui.RED)
    ui.section(t("model.importance"), t("model.importance_sub", q=n_q, r=n_r))
    ui.importance_chart(pd.DataFrame({t("features.col.quali"): shares[0], t("features.col.race"): shares[1]})
                        .rename(index=c.labels), t("model.share"))
    st.caption(t("model.accuracy"))


def factors(c, weights, shares):
    t, S = c.t, c.S
    st.markdown(t("features.intro"))
    b1, b2, _ = st.columns([1, 1, 3])
    if b1.button(t("features.save"), width="stretch"):
        c.save_settings()
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
        cols[0].markdown(f"**{c.labels[f.name]}**  \n`{f.name}`")
        cols[1].caption(t.get(f"feature.{f.name}.desc", f.description))
        for col, w, s in zip(cols[2:4], weights, shares):
            col.markdown(ui.weight_badge(w[f.name], t("features.share", share=f"{s[f.name]:.0%}")),
                         unsafe_allow_html=True)
        init = {} if f"mult_{f.name}" in st.session_state else {"value": S.multiplier(f.name)}
        cols[4].slider(c.labels[f.name], 0.0, 2.0, step=0.1, key=f"mult_{f.name}", label_visibility="collapsed",
                       **init)
        st.divider()
