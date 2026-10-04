"""Programos išvaizda F1 transliacijų stiliumi: tamsus fonas, raudoni akcentai, kursyvinis šriftas,
komandų spalvos, trasų žemėlapiai. Be emoji ir simbolių. (Oficialūs F1 logotipai nenaudojami.)"""
import html
import json
import math

import streamlit as st

RED, DARK, CARD, LINE, MUTED = "#E10600", "#15151E", "#1F1F27", "#38383F", "#B4B4BE"

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Titillium+Web:ital,wght@0,400;0,600;0,700;0,900;1,700;1,900&display=swap');
html, body, .stApp, button, input, textarea, select, [data-testid="stMarkdownContainer"], [data-baseweb] {{
    font-family: 'Titillium Web', sans-serif !important; }}
html {{ font-size: 17px; }}
.stApp {{ background: {DARK}; }}
p, li {{ line-height: 1.55; }}
[data-testid="stCaptionContainer"], .stCaption {{ color: {MUTED} !important; font-size: .92rem !important; }}
header[data-testid="stHeader"] {{ background: transparent; }}
.block-container {{ padding-top: 2.4rem; max-width: 1500px; }}
h1, h2, h3, h4 {{ text-transform: uppercase; font-weight: 900 !important; font-style: italic; letter-spacing: .02em;
    padding-right: .2em; }}
h3 {{ border-left: 4px solid {RED}; padding-left: .7rem; font-size: 1.25rem !important; margin-top: .6rem; }}
section[data-testid="stSidebar"] {{ background: #0F0F17; border-right: 1px solid {LINE}; }}
button[data-baseweb="tab"] p {{ text-transform: uppercase; font-weight: 700; font-style: italic; font-size: 1.05rem;
    padding-right: .15em; }}
div[data-baseweb="tab-highlight"] {{ background: {RED}; height: 3px; }}
div[data-baseweb="tab-border"] {{ background: {LINE}; }}
.stButton button, .stDownloadButton button {{ border-radius: 6px; border: 1px solid {LINE}; background: {CARD};
    min-height: 2.6rem; padding: .35rem 1.1rem; transition: border-color .15s, background .15s; }}
.stButton button p, .stDownloadButton button p {{ text-transform: uppercase; font-weight: 700; font-size: .82rem;
    letter-spacing: .07em; white-space: nowrap; }}
.stButton button:hover, .stDownloadButton button:hover {{ border-color: {RED}; color: #fff; }}
.stButton button[kind="primary"] {{ background: {RED}; border-color: {RED}; }}
.stButton button[kind="primary"]:hover {{ background: #FF2A1F; border-color: #FF2A1F; }}
hr {{ margin: .35rem 0 !important; border-color: #26262F !important; }}
label p {{ color: {MUTED} !important; text-transform: uppercase; font-weight: 700; font-size: .8rem !important;
    letter-spacing: .05em; }}

/* programos antraštė */
.f1-head {{ display: flex; align-items: center; gap: 1.1rem; padding: .2rem 0 1rem; margin-bottom: 1.2rem;
    border-bottom: 1px solid {LINE}; position: relative; }}
.f1-head::after {{ content: ""; position: absolute; left: 0; bottom: -1px; width: 140px; height: 3px; background: {RED}; }}
.f1-head .mark {{ display: flex; flex-direction: column; gap: 4px; padding-left: 6px; }}
.f1-head .mark i {{ display: block; height: 6px; background: {RED}; transform: skewX(-35deg); border-radius: 1px; }}
.f1-head .mark i:nth-child(1) {{ width: 44px; }}
.f1-head .mark i:nth-child(2) {{ width: 34px; opacity: .75; }}
.f1-head .mark i:nth-child(3) {{ width: 24px; opacity: .5; }}
.f1-head .title {{ font-size: 1.9rem; font-weight: 900; font-style: italic; text-transform: uppercase; line-height: 1.15;
    letter-spacing: .01em; padding-right: .2em; }}
.f1-head .title span {{ color: {RED}; }}
.f1-head .sub {{ color: {MUTED}; text-transform: uppercase; font-weight: 600; letter-spacing: .12em; font-size: .75rem;
    margin-top: .1rem; }}

/* etapo antraštė */
.f1-event {{ margin: .4rem 0 .2rem; }}
.f1-event .name {{ font-size: 2rem; font-weight: 900; font-style: italic; text-transform: uppercase; line-height: 1.15;
    padding-right: .2em; }}
.f1-event .meta {{ display: flex; flex-wrap: wrap; gap: .4rem; margin-top: .45rem; }}
.f1-event .meta span {{ background: {CARD}; border: 1px solid {LINE}; border-radius: 4px; padding: .1rem .55rem;
    color: {MUTED}; text-transform: uppercase; font-weight: 600; font-size: .78rem; letter-spacing: .06em; }}
.f1-event .meta span.hot {{ color: #fff; border-color: {RED}; background: rgba(225, 6, 0, .18); }}
.f1-label {{ color: {MUTED}; text-transform: uppercase; font-weight: 700; letter-spacing: .1em; font-size: .78rem;
    margin: 1rem 0 .5rem; }}

/* skyriaus antraštė */
.f1-sec {{ margin: 1.6rem 0 .8rem; }}
.f1-sec .t {{ display: flex; align-items: center; gap: .6rem; font-size: 1.2rem; font-weight: 900; font-style: italic;
    text-transform: uppercase; letter-spacing: .03em; line-height: 1.2; }}
.f1-sec .t::before {{ content: ""; width: 14px; height: 14px; flex: none; background: {RED}; transform: skewX(-20deg); }}
.f1-sec .s {{ color: {MUTED}; font-size: .88rem; margin: .2rem 0 0 calc(14px + .6rem); }}

/* TOP3 kortelės */
.f1-picks {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: .8rem; margin-bottom: .8rem; }}
.f1-pick {{ background: {CARD}; border-radius: 0 14px 0 0; padding: .8rem 1rem; display: flex; align-items: center;
    gap: .9rem; border-top: 4px solid var(--team); }}
.f1-pick .pos {{ font-size: 3rem; font-weight: 900; font-style: italic; line-height: 1; min-width: 2.2rem; }}
.f1-pick .stripe {{ width: 5px; height: 3rem; background: var(--team); border-radius: 2px; }}
.f1-pick .code {{ font-size: 1.8rem; font-weight: 900; font-style: italic; line-height: 1; }}
.f1-pick .team {{ color: {MUTED}; font-size: .85rem; text-transform: uppercase; font-weight: 600; }}
.f1-pick .probs {{ margin-left: auto; display: grid; grid-template-columns: auto auto; align-items: baseline;
    gap: .15rem .5rem; padding-left: .8rem; border-left: 1px solid {LINE}; }}
.f1-pick .probs b {{ color: #fff; font-size: 1.2rem; font-weight: 900; font-style: italic; text-align: right;
    padding-right: .1em; }}
.f1-pick .probs span {{ color: {MUTED}; font-size: .7rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: .08em; }}

/* rodiklių plytelės */
.f1-tiles {{ display: grid; grid-template-columns: repeat(var(--n), 1fr); gap: .8rem; margin-bottom: .8rem; }}
.f1-tile {{ background: {CARD}; border-left: 4px solid {RED}; padding: .7rem 1rem; border-radius: 0 12px 0 0; }}
.f1-tile .k {{ color: {MUTED}; text-transform: uppercase; font-weight: 700; font-size: .8rem; letter-spacing: .06em; }}
.f1-tile .v {{ font-size: 2rem; font-weight: 900; font-style: italic; line-height: 1.15; }}
.f1-tile .s {{ color: {MUTED}; font-size: .85rem; }}

/* pranešimai */
.f1-note {{ background: {CARD}; border-left: 4px solid var(--c); padding: .7rem 1rem; margin: .4rem 0 .8rem;
    border-radius: 0 10px 0 0; }}
.f1-note b {{ text-transform: uppercase; font-style: italic; margin-right: .5rem; color: var(--c); }}

/* trasos kortelė */
.f1-track {{ background: {CARD}; border-radius: 0 16px 0 0; padding: 1rem 1.1rem; border-top: 4px solid {RED}; }}
.f1-track .tname {{ font-size: 1.4rem; font-weight: 900; font-style: italic; text-transform: uppercase; }}
.f1-track .tsub {{ color: {MUTED}; text-transform: uppercase; font-size: .8rem; font-weight: 600; letter-spacing: .08em; }}
.f1-track svg {{ width: 100%; height: auto; margin: .4rem 0; }}
.f1-facts {{ display: grid; grid-template-columns: 1fr 1fr; gap: .4rem .9rem; }}
.f1-facts div {{ border-top: 1px solid {LINE}; padding-top: .35rem; }}
.f1-facts .k {{ color: {MUTED}; text-transform: uppercase; font-size: .75rem; font-weight: 700; }}
.f1-facts .v {{ font-weight: 700; }}
.f1-bar {{ display: inline-flex; gap: 3px; vertical-align: middle; margin-left: .3rem; }}
.f1-bar i {{ width: 14px; height: 7px; background: {LINE}; transform: skewX(-20deg); }}
.f1-bar i.on {{ background: {RED}; }}

/* požymio svoris */
.f1-w {{ background: {CARD}; border-left: 3px solid var(--c); padding: .3rem .6rem; border-radius: 0 8px 0 0; }}
.f1-w b {{ font-size: 1.25rem; font-weight: 900; font-style: italic; }}
.f1-w span {{ display: block; color: {MUTED}; font-size: .75rem; text-transform: uppercase; }}

/* rezultatų lentelė */
table.f1-table {{ width: 100%; border-collapse: collapse; font-size: 1rem; }}
table.f1-table th {{ text-align: left; color: {MUTED}; text-transform: uppercase; font-size: .78rem;
    font-weight: 700; padding: .45rem .5rem; border-bottom: 1px solid {LINE}; }}
table.f1-table td {{ padding: .5rem .5rem; border-bottom: 1px solid #26262F; }}
table.f1-table tr:hover td {{ background: #24242E; }}
table.f1-table .rank {{ font-weight: 900; font-style: italic; width: 2rem; }}
table.f1-table .drv {{ font-weight: 900; font-style: italic; border-left: 4px solid var(--team); padding-left: .6rem; }}
table.f1-table .team {{ color: {MUTED}; font-size: .85rem; text-transform: uppercase; }}
table.f1-table .bar {{ position: relative; min-width: 70px; }}
table.f1-table .bar i {{ position: absolute; left: 0; top: 22%; height: 56%; background: var(--c); opacity: .4;
    width: var(--w); border-radius: 0 3px 3px 0; }}
table.f1-table .bar span {{ position: relative; font-weight: 700; }}
</style>
"""


def _md(s):
    st.markdown(s, unsafe_allow_html=True)


def apply():
    _md(CSS)


def header(accent, subtitle):
    _md(f'<div class="f1-head"><div class="mark"><i></i><i></i><i></i></div><div>'
        f'<div class="title">F1 <span>{html.escape(accent)}</span></div>'
        f'<div class="sub">{html.escape(subtitle)}</div></div></div>')


def event_title(name, meta_parts, highlight=None):
    """meta_parts – žymės po pavadinimu; highlight – kuri iš jų paryškinama."""
    meta = "".join(f'<span class="{"hot" if m == highlight else ""}">{html.escape(m)}</span>' for m in meta_parts)
    _md(f'<div class="f1-event"><div class="name">{html.escape(name)}</div><div class="meta">{meta}</div></div>')


def label(text):
    _md(f'<div class="f1-label">{html.escape(text)}</div>')


def section(title, subtitle=None):
    """Skyriaus antraštė su paaiškinimu (vietoj „### “ – kad kursyvas neužliptų ant juostos)."""
    sub = f'<div class="s">{html.escape(subtitle)}</div>' if subtitle else ""
    _md(f'<div class="f1-sec"><div class="t">{html.escape(title)}</div>{sub}</div>')


def note(title, text, color=RED):
    _md(f'<div class="f1-note" style="--c:{color}"><b>{html.escape(title)}</b>{html.escape(text)}</div>')


def tiles(items):
    """items – [(pavadinimas, reikšmė, paaiškinimas)]."""
    cells = "".join(f'<div class="f1-tile"><div class="k">{html.escape(k)}</div><div class="v">{html.escape(v)}</div>'
                    f'<div class="s">{html.escape(s)}</div></div>' for k, v, s in items)
    _md(f'<div class="f1-tiles" style="--n:{len(items)}">{cells}</div>')


def weight_badge(weight, caption):
    color = RED if weight >= 0 else MUTED
    return f'<div class="f1-w" style="--c:{color}"><b>{weight:+.2f}</b><span>{html.escape(caption)}</span></div>'


def pick_cards(pick, table, teams, color_of, exact_label, top3_label):
    """color_of – funkcija komanda -> spalva (žinynas „komandos“)."""
    cards = []
    for i, d in enumerate(pick, 1):
        r, team = table.loc[d], teams.get(d, "")
        cards.append(f'<div class="f1-pick" style="--team:{color_of(team)}"><div class="pos">{i}</div>'
                     f'<div class="stripe"></div><div><div class="code">{d}</div>'
                     f'<div class="team">{html.escape(team)}</div></div>'
                     f'<div class="probs"><b>{r[f"P{i}"]:.0%}</b><span>{html.escape(exact_label)}</span>'
                     f'<b>{r.TOP3:.0%}</b><span>{html.escape(top3_label)}</span></div></div>')
    _md(f'<div class="f1-picks">{"".join(cards)}</div>')


def probability_table(table, teams, color_of, driver_label, team_label, n=12):
    """Tikimybių lentelė kaip F1 rezultatų lentelė."""
    head = "".join(f"<th>{html.escape(h)}</th>" for h in ["", driver_label, team_label, "P1", "P2", "P3", "TOP3"])
    rows = []
    for k, (d, r) in enumerate(table.head(n).iterrows(), 1):
        team = teams.get(d, "")
        bars = "".join(f'<td class="bar" style="--w:{r[c] * 100:.0f}%;--c:{RED if c == "TOP3" else MUTED}">'
                       f'<i></i><span>{r[c]:.0%}</span></td>' for c in ("P1", "P2", "P3", "TOP3"))
        rows.append(f'<tr style="--team:{color_of(team)}"><td class="rank">{k}</td><td class="drv">{d}</td>'
                    f'<td class="team">{html.escape(team)}</td>{bars}</tr>')
    _md(f'<table class="f1-table"><thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table>')


def contribution_chart(contrib, driver_label, value_label, feature_label):
    """contrib – DataFrame (vairuotojas x požymis), eilutės tikimybių tvarka. Horizontalios sukrautos juostos,
    legenda apačioje keliais stulpeliais (kad netrumpėtų)."""
    import altair as alt
    order = list(contrib.index)
    long = contrib.reset_index(names="d").melt("d", var_name="f", value_name="v")
    chart = alt.Chart(long).mark_bar().encode(
        y=alt.Y("d:N", sort=order, title=None, axis=alt.Axis(labelFontWeight="bold", labelFontSize=13)),
        x=alt.X("sum(v):Q", title=value_label),
        color=alt.Color("f:N", title=None, legend=alt.Legend(orient="bottom", columns=3, labelFontSize=12,
                                                             labelLimit=320, symbolType="square")),
        tooltip=[alt.Tooltip("d:N", title=driver_label), alt.Tooltip("f:N", title=feature_label),
                 alt.Tooltip("v:Q", title=value_label, format="+.2f")],
    ).properties(height=34 * len(order))
    st.altair_chart(chart, width="stretch", height=34 * len(order) + 170)   # + ašis ir legenda


def _scale_bar(value, of=5):
    return '<span class="f1-bar">' + "".join(f'<i class="{"on" if i < round(value) else ""}"></i>'
                                           for i in range(of)) + "</span>"


def track_svg(points, corners, width=520):
    """Trasos kontūras SVG: balta linija ant tamsaus fono, raudona starto linija, posūkių numeriai."""
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    pad, W = 0.09, width
    H = int(W * (h + 2 * pad) / (w + 2 * pad))
    sx = lambda x: (x - min(xs) + pad) / (w + 2 * pad) * W
    sy = lambda y: H - (y - min(ys) + pad) / (h + 2 * pad) * H        # Y aukštyn
    path = "M" + " L".join(f"{sx(x):.1f},{sy(y):.1f}" for x, y in points) + " Z"
    cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
    labels = []
    for num, x, y in corners:
        dx, dy = x - cx, y - cy
        norm = max((dx * dx + dy * dy) ** 0.5, 1e-6)
        lx, ly = sx(x + dx / norm * 0.055), sy(y + dy / norm * 0.055)   # numeris – už trasos ribų
        labels.append(f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="14" fill="{DARK}" stroke="#55555F"/>'
                      f'<text x="{lx:.1f}" y="{ly + 5:.1f}" text-anchor="middle" font-size="14" font-weight="700" '
                      f'fill="{MUTED}">{html.escape(str(num))}</text>')
    (x0, y0), (x1, y1) = points[0], points[2]
    ang = math.degrees(math.atan2(sy(y1) - sy(y0), sx(x1) - sx(x0)))
    start = (f'<g transform="translate({sx(x0):.1f},{sy(y0):.1f}) rotate({ang:.0f})">'
             f'<rect x="-3" y="-13" width="6" height="26" fill="{RED}"/></g>')
    return (f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">'
            f'<path d="{path}" fill="none" stroke="#2C2C36" stroke-width="16" stroke-linejoin="round"/>'
            f'<path d="{path}" fill="none" stroke="#FFFFFF" stroke-width="5" stroke-linejoin="round"/>'
            f'{start}{"".join(labels)}</svg>')


def track_card(name, subtitle, outline, facts, no_map_text):
    """outline – (taškai, posūkiai) arba None; facts – [(pavadinimas, reikšmė, skalė 1–5 arba None)]."""
    svg = track_svg(*outline) if outline else f'<div class="tsub" style="padding:2rem 0">{html.escape(no_map_text)}</div>'
    rows = "".join(f'<div><div class="k">{html.escape(k)}</div><div class="v">{html.escape(v)}'
                   f'{_scale_bar(s) if s is not None else ""}</div></div>' for k, v, s in facts)
    _md(f'<div class="f1-track"><div class="tname">{html.escape(name)}</div><div class="tsub">{html.escape(subtitle)}</div>'
        f'{svg}<div class="f1-facts">{rows}</div></div>')


def load_outline(db, circuit):
    r = db.query("SELECT taskai, posukiai FROM trasu_konturai WHERE trasa=?", (circuit,))
    return (json.loads(r.taskai.iloc[0]), json.loads(r.posukiai.iloc[0])) if not r.empty else None
