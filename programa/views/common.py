"""Bendros puslapių dalys: laiko formatai, spėjimo blokas, duomenų patikra, svarbūs etapo faktai."""
import html
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

import ui_style as ui
from f1model import features, model
from f1model.config import DONE_STATUSES
from f1model.dataset import kind_of

CHECK_ORDER = ("results", "practice", "grid", "weather", "odds", "news")


# ------------------------------------------------------------------ laikas

def local(iso, fmt="%m-%d %H:%M"):
    return datetime.fromisoformat(iso).astimezone().strftime(fmt)


def when(c, iso, short=False):
    """„šeštadienis 10-10 16:00“ (short – „Št 16:00“)."""
    d = datetime.fromisoformat(iso).astimezone()
    if short:
        return f"{c.t(f'weekday_short.{d.weekday()}')} {d:%H:%M}"
    return f"{c.t(f'weekday.{d.weekday()}')} {d:%m-%d %H:%M}"


def countdown(iso):
    secs = int((datetime.fromisoformat(iso) - datetime.now(timezone.utc)).total_seconds())
    if secs <= 0:
        return None
    d, rem = divmod(secs, 86400)
    h, m = rem // 3600, rem % 3600 // 60
    return f"{d} d {h} h" if d else f"{h} h {m:02d} min" if h else f"{m} min"


# ------------------------------------------------------------------ naujienos ir faktai

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


def team_names(c, season):
    return {k: v[0] for k, v in c.briefing.teams(season).items()}


def key_facts(c, season, rnd, session, ev, leaders, teams):
    """Svarbu šiam etapui: FIA starto baudos, komandų atnaujinimai, svarbios naujienos apie pirmaujančias komandas."""
    t, brief = c.t, c.briefing
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
        ui.news_list(news_rows(c, news, team_names(c, season), summary_len=160))


def checklist(c, season, rnd, session):
    """„Duomenys šiam spėjimui“ – kas surinkta, kas trūksta ir ką daryti."""
    t, names = c.t, c.session_names
    checks = {k.key: k for k in c.checks(season, rnd, session)}
    items = []
    for key in (k for k in CHECK_ORDER if k in checks):
        k, p = checks[key], dict(checks[key].params)
        if "sessions" in p:
            p["sessions"] = ", ".join(names.get(s, s) for s in p["sessions"])
        if "sources" in p:
            p["sources"] = ", ".join(p["sources"])
        if "age" in p:
            p["age"] = f"{p['age'] * 60:.0f} min" if p["age"] < 1 else f"{p['age']:.0f} h"
        items.append((t(f"check.{key}"), k.state, t(k.text, **p)))
    ui.checklist(items, {s: t(f"state.{s}") for s in ("ok", "warn", "missing", "na")})


# ------------------------------------------------------------------ spėjimas

def predict(c, season, rnd, session):
    """Spėjimas; įvykusiai sesijai – tik su iki jos žinomais duomenimis."""
    srow = c.data.session_rows(season, rnd, session).iloc[0]
    if srow.status in DONE_STATUSES:
        w = c.weights_before(kind_of(session), srow.date_utc)
        return model.predict(c.data, season, rnd, session, before=srow.date_utc, weights=w)
    return model.predict(c.data, season, rnd, session, weights=c.fitted[kind_of(session)][0])


def contributions(c, out):
    """Kiek kiekvienas veiksnys prideda prie vairuotojo stiprumo (svoris × reikšmė × lietaus suspaudimas)."""
    ch = 1.0 - c.S.wet_chaos * out["rain"]
    return pd.DataFrame({f: out["table"][f] * w * ch for f, w in out["weights"].items()})


def reasons(c, out, contrib, n=2):
    """Kiekvienam spėtam vairuotojui – didžiausią teigiamą indėlį davę veiksniai."""
    res = {}
    for d in out["pick"]:
        top = contrib.loc[d].sort_values(ascending=False)
        res[d] = [c.labels[f] for f, v in top.head(n).items() if v > 0.05]
    return res


def rain_note(c, srow):
    t = c.t
    if pd.notna(srow.track_rain_frac):
        return t("rain.track", frac=f"{srow.track_rain_frac:.0%}")
    if pd.notna(srow.fc_pop):
        return t("rain.forecast", mm=f"{srow.rain_mm or 0:.1f}", region=f"{srow.region_rain_mm:.1f}")
    return t("rain.none")


def prediction_block(c, season, rnd, session, key):
    """Siūlomas trejetas, rodikliai, tikimybės, svarbūs faktai ir (išskleidžiamas) išsamus paaiškinimas."""
    t, ref, names = c.t, c.ref, c.session_names
    srow, ev = c.data.session_rows(season, rnd, session).iloc[0], c.data.event(season, rnd)
    out, teams = predict(c, season, rnd, session), c.data.teams(season)
    contrib = contributions(c, out)

    head, action = st.columns([4, 1.3], vertical_alignment="center")
    head.markdown(f"<div class='f1-label' style='margin:0'>{html.escape(t('predict.pick'))}</div>",
                  unsafe_allow_html=True)
    if action.button(t("predict.save"), width="stretch", key=f"save_{key}"):
        c.save_prediction(season, rnd, session, out)
        st.toast(t("predict.saved"))
    if srow.status in DONE_STATUSES:
        actual = c.data.top3(season, rnd, session)
        ui.note(t("predict.done_title"), t("predict.done_text", actual=" – ".join(actual),
                                           points=model.score(out["pick"], actual)), color=ui.MUTED)
        if srow.status == "fia":
            ui.note(t("predict.prelim_title"), t("predict.prelim_text"), color="#F5A524")
    ui.pick_cards(out["pick"], out["table"], teams, ref.team_color, t("pick.exact"), t("pick.top3"),
                  reasons(c, out, contrib), t("pick.why"))
    ui.tiles([(t("tile.expected"), f"{out['expected']:.2f}", t("tile.expected_sub")),
              (t("tile.rain"), f"{out['rain']:.0%}", rain_note(c, srow)),
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
        ui.contribution_chart(contrib.rename(columns=c.labels).head(8), t("col.driver"), t("why.value"),
                              t("features.col.feature"))
        ui.label(t("features.values", event=ev["name"], session=names[session]))
        st.caption(t("features.values_sub"))
        st.dataframe(out["table"][features.names()].rename(columns=c.labels).round(2), width="stretch")
