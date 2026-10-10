"""Artimiausia sesija (atsidaro pirma): kas artėja, ar surinkti duomenys, siūlomas spėjimas."""
from datetime import datetime, timedelta, timezone

import streamlit as st

import ui_style as ui
from f1model.config import COMPETITIVE, SEASON

from .common import checklist, countdown, prediction_block, when


def upcoming(data):
    """(etapas, sesija) artimiausios sesijos; sezonui pasibaigus – paskutinės įvykusios (arba (None, None))."""
    nr, ns = data.next_session((datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat())
    if nr is None:
        last = data.done_sessions([SEASON], COMPETITIVE, by_date=True)
        if not last.empty:
            nr, ns = int(last.iloc[-1]["round"]), last.iloc[-1].session
    return nr, ns


def render(c):
    t, data, names = c.t, c.data, c.session_names
    nr, ns = upcoming(data)
    if nr is None:
        return ui.note(t("predict.no_data_title"), t("predict.no_data"))
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
