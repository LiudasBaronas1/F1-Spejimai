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

/* žymės */
.f1-chip {{ display: inline-block; padding: .08rem .5rem; margin: 0 .3rem .3rem 0; border-radius: 4px;
    font-size: .72rem; font-weight: 700; text-transform: uppercase; letter-spacing: .06em; white-space: nowrap;
    border: 1px solid var(--c, {LINE}); color: #fff; background: color-mix(in srgb, var(--c, {LINE}) 22%, transparent); }}
.f1-chip.perf {{ --c: {RED}; }}
.f1-chip.circ {{ --c: #3E8EDE; }}
.f1-chip.rel {{ --c: #8A8A96; }}
.f1-chip.tag {{ --c: #55555F; color: {MUTED}; }}

/* bolidų atnaujinimai */
.f1-upg {{ columns: 2 420px; column-gap: .9rem; }}
.f1-upg-card {{ break-inside: avoid; margin-bottom: .9rem; }}
.f1-upg-card {{ background: {CARD}; border-top: 4px solid var(--team); border-radius: 0 14px 0 0; padding: .9rem 1.1rem; }}
.f1-upg-card .h {{ display: flex; align-items: baseline; justify-content: space-between; gap: .6rem; flex-wrap: wrap;
    margin-bottom: .5rem; }}
.f1-upg-card .tn {{ font-size: 1.15rem; font-weight: 900; font-style: italic; text-transform: uppercase;
    padding-right: .2em; }}
.f1-upg-card .it {{ border-top: 1px solid {LINE}; padding: .45rem 0 .35rem; }}
.f1-upg-card .it b {{ margin-right: .4rem; }}
.f1-upg-card .it .d {{ color: {MUTED}; font-size: .86rem; line-height: 1.45; margin-top: .15rem; }}
.f1-upg-card .none {{ color: {MUTED}; font-size: .9rem; font-style: italic; }}
.f1-upg-card .src {{ border-top: 1px solid {LINE}; margin-top: .4rem; padding-top: .5rem; font-size: .85rem;
    line-height: 1.5; }}
.f1-upg-card .src .k {{ color: {MUTED}; font-size: .7rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: .08em; margin-right: .4rem; }}
.f1-upg-card .src a, [data-testid="stMarkdownContainer"] a.f1-link {{ color: #fff !important;
    text-decoration: underline; text-decoration-color: {RED}; text-underline-offset: 3px; }}
.f1-upg-card .src a:hover, [data-testid="stMarkdownContainer"] a.f1-link:hover {{ color: {RED} !important; }}
.f1-upg-card .src .a {{ display: block; margin-top: .2rem; }}
.f1-upg-card .src .a span {{ color: {MUTED}; font-size: .75rem; margin-left: .3rem; }}

/* naujienos */
.f1-news .n {{ border-bottom: 1px solid #26262F; padding: .75rem 0 .6rem; }}
.f1-news .meta {{ color: {MUTED}; font-size: .74rem; font-weight: 700; text-transform: uppercase; letter-spacing: .07em; }}
.f1-news a.t {{ display: block; color: #fff; font-weight: 700; font-size: 1.05rem; text-decoration: none;
    margin: .15rem 0 .2rem; line-height: 1.35; }}
.f1-news a.t:hover {{ color: {RED}; }}
.f1-news .s {{ color: {MUTED}; font-size: .9rem; line-height: 1.45; margin-bottom: .35rem; }}

/* sezono atnaujinimų lentelė */
.f1-heat-wrap {{ overflow-x: auto; }}
table.f1-heat {{ border-collapse: collapse; font-size: .85rem; }}
table.f1-heat th {{ color: {MUTED}; font-size: .7rem; font-weight: 700; text-transform: uppercase; padding: .3rem .35rem;
    white-space: nowrap; writing-mode: vertical-rl; transform: rotate(180deg); text-align: left; }}
table.f1-heat th.team {{ writing-mode: horizontal-tb; transform: none; }}
table.f1-heat td {{ text-align: center; min-width: 2rem; padding: .3rem .2rem; border: 1px solid #1A1A22; font-weight: 700; }}
table.f1-heat td.team {{ text-align: left; white-space: nowrap; padding-right: .8rem; border-left: 4px solid var(--team);
    font-weight: 700; font-style: italic; text-transform: uppercase; }}

/* iššokantys langai: patarimai, išskleidžiami sąrašai, pranešimai */
[data-testid="stTooltipContent"] {{ background: #262630 !important; color: #fff !important; border: 1px solid {LINE};
    border-left: 3px solid {RED}; border-radius: 6px; padding: .55rem .85rem !important; max-width: 300px;
    box-shadow: 0 10px 28px rgba(0, 0, 0, .55); }}
[data-testid="stTooltipContent"] p {{ font-size: .86rem; line-height: 1.45; margin: 0; white-space: normal; }}
[data-testid="stToast"] {{ background: #262630 !important; border: 1px solid {LINE}; border-left: 4px solid {RED};
    border-radius: 6px; box-shadow: 0 10px 28px rgba(0, 0, 0, .55); }}
[data-testid="stToast"] p {{ color: #fff; font-weight: 600; }}
[data-testid="stAlert"] {{ border-radius: 6px; }}

/* šoninė juosta */
.f1-side-brand {{ font-size: 1.25rem; font-weight: 900; font-style: italic; text-transform: uppercase;
    padding-right: .2em; margin: -.6rem 0 .2rem; }}
.f1-side-brand span {{ color: {RED}; }}
.f1-side-info {{ background: {CARD}; border-left: 3px solid {LINE}; border-radius: 0 8px 0 0; padding: .55rem .8rem;
    margin: .6rem 0; font-size: .86rem; color: {MUTED}; line-height: 1.45; }}
.f1-side-info b {{ display: block; color: #fff; font-size: .72rem; text-transform: uppercase; letter-spacing: .08em; }}

/* pasirinkimo juosta virš skyrių */
.st-key-context {{ background: {CARD}; border-radius: 0 14px 0 0; border-top: 3px solid {RED};
    padding: .7rem 1rem .9rem; margin-bottom: .6rem; }}
/* vidiniai skirtukai (Modelis ir duomenys) – mažesni */
.st-key-model_area button[data-baseweb="tab"] p {{ font-size: .9rem; color: {MUTED}; }}
.st-key-model_area button[data-baseweb="tab"][aria-selected="true"] p {{ color: #fff; }}

/* eigos skydelis */
.f1-prog {{ background: {CARD}; border-radius: 0 18px 0 0; border-top: 4px solid {RED}; padding: 1.3rem 1.5rem 1.2rem;
    margin: .4rem 0 1.4rem; box-shadow: 0 12px 34px rgba(0, 0, 0, .35); }}
.f1-prog .top {{ display: flex; align-items: flex-end; justify-content: space-between; gap: 1rem; }}
.f1-prog .ttl {{ font-size: 1.6rem; font-weight: 900; font-style: italic; text-transform: uppercase; line-height: 1.1;
    padding-right: .2em; }}
.f1-prog .sub {{ color: {MUTED}; font-size: .95rem; margin-top: .25rem; }}
.f1-prog .pct {{ font-size: 3.2rem; font-weight: 900; font-style: italic; line-height: 1; padding-right: .1em; }}
.f1-prog .bar {{ background: #2C2C36; border-radius: 3px; overflow: hidden; margin: .8rem 0 1rem;
    transform: skewX(-12deg); }}
.f1-prog .bar i {{ display: block; height: 100%; background: linear-gradient(90deg, #B00500, {RED} 60%, #FF3B2F);
    transition: width .3s ease; }}
.f1-prog .bar.big {{ height: 22px; }}
.f1-prog .bar.small {{ height: 9px; margin: .55rem 0 0; }}
.f1-prog .now {{ background: #191920; border: 1px solid {LINE}; border-left: 4px solid {RED}; border-radius: 0 10px 0 0;
    padding: .8rem 1rem; }}
.f1-prog .now .k {{ color: {RED}; font-size: .72rem; font-weight: 700; text-transform: uppercase; letter-spacing: .12em; }}
.f1-prog .now .name {{ font-size: 1.25rem; font-weight: 900; font-style: italic; text-transform: uppercase;
    padding-right: .2em; }}
.f1-prog .now .desc {{ color: {MUTED}; font-size: .92rem; line-height: 1.45; }}
.f1-prog .now .detail {{ display: flex; justify-content: space-between; gap: 1rem; margin-top: .45rem; font-weight: 700;
    font-size: .95rem; }}
.f1-prog .now .detail span {{ color: {MUTED}; font-weight: 600; white-space: nowrap; }}
.f1-prog .steps {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: .35rem .9rem;
    margin-top: 1rem; }}
.f1-prog .st {{ display: flex; align-items: center; gap: .6rem; padding: .35rem 0; border-bottom: 1px solid #26262F;
    font-size: .92rem; }}
.f1-prog .st .dot {{ width: 11px; height: 11px; flex: none; transform: skewX(-20deg); background: #3A3A44; }}
.f1-prog .st .n {{ flex: 1; color: {MUTED}; }}
.f1-prog .st .s {{ color: {MUTED}; font-size: .72rem; font-weight: 700; text-transform: uppercase; letter-spacing: .07em;
    white-space: nowrap; }}
.f1-prog .st.run .dot {{ background: {RED}; animation: f1pulse 1s ease-in-out infinite; }}
.f1-prog .st.run .n, .f1-prog .st.done .n {{ color: #fff; font-weight: 600; }}
.f1-prog .st.run .s {{ color: {RED}; }}
.f1-prog .st.done .dot {{ background: #E8E8EE; }}
.f1-prog .st.err .dot {{ background: #F5A524; }}
.f1-prog .st.err .s, .f1-prog .st.err .n {{ color: #F5A524; }}
@keyframes f1pulse {{ 50% {{ opacity: .35; }} }}

/* trasos skyrius */
.f1-profile {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: .7rem; }}
.f1-profile div {{ background: {CARD}; border-radius: 0 10px 0 0; padding: .6rem .8rem; }}
.f1-profile .k {{ color: {MUTED}; font-size: .74rem; font-weight: 700; text-transform: uppercase; letter-spacing: .06em; }}
.f1-profile .v {{ font-size: 1.35rem; font-weight: 900; font-style: italic; }}
.f1-profile .d {{ color: {MUTED}; font-size: .8rem; line-height: 1.35; margin-top: .15rem; }}
table.f1-plain th, table.f1-plain td, table.f1-table th, table.f1-table td {{ border-left: none; border-right: none;
    border-top: none; }}
table.f1-plain, table.f1-table {{ border: none; }}
div[data-baseweb="tab-list"] {{ gap: 1.4rem; }}
table.f1-plain {{ width: 100%; border-collapse: collapse; font-size: .95rem; }}
table.f1-plain th {{ text-align: left; color: {MUTED}; text-transform: uppercase; font-size: .74rem; font-weight: 700;
    padding: .45rem .5rem; border-bottom: 1px solid {LINE}; white-space: nowrap; }}
table.f1-plain td {{ padding: .5rem .5rem; border-bottom: 1px solid #26262F; }}
table.f1-plain tr:hover td {{ background: #24242E; }}
table.f1-plain td.b {{ font-weight: 900; font-style: italic; }}
table.f1-plain td.m {{ color: {MUTED}; }}
table.f1-plain td .drv {{ border-left: 4px solid var(--team); padding-left: .45rem; font-weight: 900; font-style: italic; }}
table.f1-plain tr.hot td {{ background: rgba(225, 6, 0, .1); }}

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
    head = f"<b>{html.escape(title)}</b>" if title else ""
    _md(f'<div class="f1-note" style="--c:{color}">{head}{html.escape(text)}</div>')


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


REASON_CLASS = {"performance": "perf", "circuit": "circ", "reliability": "rel"}


def chips(items):
    """items – [(tekstas, klasė, spalva arba None)]."""
    out = []
    for text, cls, color in items:
        style = f' style="--c:{color}"' if color else ""
        out.append(f'<span class="f1-chip {cls}"{style}>{html.escape(text)}</span>')
    return "".join(out)


def _link(url, text):
    return f'<a href="{html.escape(url)}" target="_blank" rel="noopener">{html.escape(text)}</a>'


def _upgrade_sources(t, labels):
    """Kortelės apačia: FIA dokumentas (ties komandos puslapiu) ir straipsniai apie atnaujinimus."""
    parts = []
    if t.source_url:
        doc = labels["doc_page"].format(page=t.page) if t.page else labels["doc"]
        parts.append(f'<div><span class="k">{html.escape(labels["source"])}</span>{_link(t.source_url, doc)}</div>')
    if t.articles:
        links = "".join(f'<span class="a">{_link(url, title)}<span>{html.escape(src)}</span></span>'
                        for title, url, src in t.articles)
        parts.append(f'<div><span class="k">{html.escape(labels["articles"])}</span>{links}</div>')
    return f'<div class="src">{"".join(parts)}</div>' if parts else ""


def upgrade_cards(teams, reason_labels, empty_text, labels):
    """teams – [briefing.TeamUpgrades]; reason_labels – {priežastis: pavadinimas};
    labels – nuorodų tekstai: source, doc, doc_page (su {page}), articles."""
    cards = []
    for t in teams:
        counts = chips([(f"{reason_labels[r]} {n}", REASON_CLASS[r], None) for r, n in t.counts.items() if n])
        items = "".join(
            f'<div class="it"><b>{html.escape(comp or "")}</b>'
            f'{chips([(reason_labels[r], REASON_CLASS[r], None)]) if r in REASON_CLASS else ""}'
            f'<div class="d">{html.escape(desc or "")}</div></div>' for comp, r, desc in t.items)
        cards.append(f'<div class="f1-upg-card" style="--team:{t.color}"><div class="h">'
                     f'<span class="tn">{html.escape(t.name)}</span><span>{counts}</span></div>'
                     f'{items or f"<div class=none>{html.escape(empty_text)}</div>"}'
                     f'{_upgrade_sources(t, labels)}</div>')
    _md(f'<div class="f1-upg">{"".join(cards)}</div>')


def news_list(rows):
    """rows – [dict(title, url, meta, summary, chips=[(tekstas, klasė, spalva)])]."""
    items = []
    for r in rows:
        summary = f'<div class="s">{html.escape(r["summary"])}</div>' if r.get("summary") else ""
        items.append(f'<div class="n"><div class="meta">{html.escape(r["meta"])}</div>'
                     f'<a class="t" href="{html.escape(r["url"])}" target="_blank" rel="noopener">'
                     f'{html.escape(r["title"])}</a>{summary}{chips(r.get("chips", []))}</div>')
    _md(f'<div class="f1-news">{"".join(items)}</div>')


def heat_table(matrix, team_label, color_of):
    """matrix – DataFrame komanda x etapas (skaičiai); spalvos intensyvumas pagal reikšmę."""
    top = max(int(matrix.values.max()), 1)
    head = f'<th class="team">{html.escape(team_label)}</th>' + "".join(f"<th>{html.escape(str(c))}</th>"
                                                                      for c in matrix.columns)
    rows = []
    for team, r in matrix.iterrows():
        cells = "".join(f'<td style="background:rgba(225,6,0,{0.12 + 0.75 * v / top:.2f})">{v}</td>' if v
                        else '<td style="color:#44444C">·</td>' for v in r.astype(int))
        rows.append(f'<tr><td class="team" style="--team:{color_of(team)}">{html.escape(team)}</td>{cells}</tr>')
    _md(f'<div class="f1-heat-wrap"><table class="f1-heat"><thead><tr>{head}</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div>')


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


def progress_html(title, frac, subtitle, steps, now=None, now_label=""):
    """Didelis eigos skydelis. steps – [(pavadinimas, būsena run/done/err/wait, būsenos tekstas)];
    now – dict(name, desc, detail, step, frac) apie tai, kas daroma dabar (arba None)."""
    e = html.escape
    pct = max(0.0, min(frac, 1.0))
    current = ""
    if now:
        current = (f'<div class="now"><div class="k">{e(now_label)}</div><div class="name">{e(now["name"])}</div>'
                   f'<div class="desc">{e(now.get("desc", ""))}</div>'
                   f'<div class="detail">{e(now.get("detail", ""))}<span>{e(now.get("step", ""))}</span></div>'
                   f'<div class="bar small"><i style="width:{max(0.0, min(now.get("frac", 0), 1.0)) * 100:.1f}%"></i>'
                   f'</div></div>')
    rows = "".join(f'<div class="st {s}"><span class="dot"></span><span class="n">{e(n)}</span>'
                   f'<span class="s">{e(txt)}</span></div>' for n, s, txt in steps)
    return (f'<div class="f1-prog"><div class="top"><div><div class="ttl">{e(title)}</div>'
            f'<div class="sub">{e(subtitle)}</div></div><div class="pct">{pct:.0%}</div></div>'
            f'<div class="bar big"><i style="width:{pct * 100:.1f}%"></i></div>{current}'
            f'<div class="steps">{rows}</div></div>')


def side_brand(accent):
    _md(f'<div class="f1-side-brand">F1 <span>{html.escape(accent)}</span></div>')


def side_info(title, text):
    _md(f'<div class="f1-side-info"><b>{html.escape(title)}</b>{html.escape(text)}</div>')


def profile_grid(items):
    """items – [(pavadinimas, reikšmė tekstu, skalė 1–5 arba None, paaiškinimas)]."""
    cells = "".join(f'<div><div class="k">{html.escape(k)}</div><div class="v">{html.escape(v)}'
                    f'{_scale_bar(s) if s is not None else ""}</div><div class="d">{html.escape(d)}</div></div>'
                    for k, v, s, d in items)
    _md(f'<div class="f1-profile">{cells}</div>')


def plain_table(headers, rows, classes=None, row_classes=None):
    """headers – stulpelių pavadinimai; rows – eilutės (reikšmės jau HTML saugios arba paprastas tekstas);
    classes – stulpelio CSS klasė (b – paryškinta, m – blanki); row_classes – eilutės klasė (pvz. hot)."""
    classes = classes or [""] * len(headers)
    row_classes = row_classes or [""] * len(rows)
    head = "".join(f"<th>{html.escape(h)}</th>" for h in headers)
    body = "".join(f'<tr class="{rc}">' + "".join(f'<td class="{c}">{v}</td>' for v, c in zip(r, classes)) + "</tr>"
                   for r, rc in zip(rows, row_classes))
    _md(f'<table class="f1-plain"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>')


def driver_cell(code, team, color_of):
    return f'<span class="drv" style="--team:{color_of(team)}">{html.escape(code)}</span>' if code else "–"


def load_outline(db, circuit):
    r = db.query("SELECT taskai, posukiai FROM trasu_konturai WHERE trasa=?", (circuit,))
    return (json.loads(r.taskai.iloc[0]), json.loads(r.posukiai.iloc[0])) if not r.empty else None
