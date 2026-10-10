"""Programos išvaizda F1 transliacijų stiliumi: tamsus fonas, raudoni akcentai, kursyvinis šriftas,
komandų spalvos, trasų žemėlapiai. Be emoji ir simbolių. (Oficialūs F1 logotipai nenaudojami.)"""
import html
import math
from pathlib import Path

import streamlit as st

RED, DARK, CARD, LINE, MUTED = "#E10600", "#15151E", "#1F1F27", "#38383F", "#B4B4BE"

CSS_PATH = Path(__file__).with_name("ui.css")


def _md(s):
    st.markdown(s, unsafe_allow_html=True)


def apply():
    _md(f"<style>{CSS_PATH.read_text(encoding='utf-8')}</style>")


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


def pick_cards(pick, table, teams, color_of, exact_label, top3_label, reasons=None, why_label=""):
    """color_of – funkcija komanda -> spalva (žinynas „komandos“); reasons – {vairuotojas: [priežastys]}."""
    cards = []
    for i, d in enumerate(pick, 1):
        r, team = table.loc[d], teams.get(d, "")
        why = (f'<div class="why"><span>{html.escape(why_label)}</span>{html.escape(" · ".join(reasons[d]))}</div>'
               if reasons and reasons.get(d) else "")
        cards.append(f'<div class="f1-pick-wrap" style="--team:{color_of(team)}"><div class="f1-pick">'
                     f'<div class="pos">{i}</div><div class="stripe"></div><div><div class="code">{d}</div>'
                     f'<div class="team">{html.escape(team)}</div></div>'
                     f'<div class="probs"><b>{r[f"P{i}"]:.0%}</b><span>{html.escape(exact_label)}</span>'
                     f'<b>{r.TOP3:.0%}</b><span>{html.escape(top3_label)}</span></div></div>{why}</div>')
    _md(f'<div class="f1-picks">{"".join(cards)}</div>')


def hero(kicker, title, meta, countdown=None, countdown_label=""):
    """Pradžios puslapio antraštė: kas artėja, kada, ir atgalinis laikmatis."""
    chips = "".join(f"<span>{html.escape(m)}</span>" for m in meta)
    cd = (f'<div class="cd"><div class="k">{html.escape(countdown_label)}</div><div class="v">{html.escape(countdown)}'
          f'</div></div>') if countdown else ""
    _md(f'<div class="f1-hero"><div><div class="kick">{html.escape(kicker)}</div><div class="name">{html.escape(title)}'
        f'</div><div class="meta">{chips}</div></div>{cd}</div>')


STATE_COLOR = {"ok": "#3CCB7F", "warn": "#F5A524", "missing": RED, "na": "#55555F"}


def checklist(items, state_labels):
    """items – [(pavadinimas, būsena ok/warn/missing/na, paaiškinimas)]."""
    cells = "".join(f'<div style="--c:{STATE_COLOR[s]}"><div class="k">{html.escape(k)}'
                    f'<span>{html.escape(state_labels[s])}</span></div><div class="d">{html.escape(d)}</div></div>'
                    for k, s, d in items)
    _md(f'<div class="f1-check">{cells}</div>')


def state_table(matrix, row_label, state_labels):
    """Sezono duomenų suvestinė: etapas × sesija, langelio spalva pagal būseną."""
    colors = {"ok": STATE_COLOR["ok"], "fia": STATE_COLOR["warn"], "missing": RED, "upcoming": "#3A3A44"}
    head = f"<th>{html.escape(row_label)}</th>" + "".join(f"<th>{html.escape(str(c))}</th>" for c in matrix.columns)
    rows = []
    for rnd, r in matrix.iterrows():
        cells = "".join(f'<td title="{html.escape(state_labels.get(v, ""))}"><i style="background:{colors[v]}"></i></td>'
                        if isinstance(v, str) else "<td></td>" for v in r)
        rows.append(f"<tr><td class='b'>{rnd}</td>{cells}</tr>")
    legend = "".join(f'<span><i style="background:{colors[k]}"></i>{html.escape(state_labels[k])}</span>'
                     for k in colors)
    _md(f'<div class="f1-legend">{legend}</div><table class="f1-plain f1-states"><thead><tr>{head}</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table>')


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


def importance_chart(shares, value_label):
    """shares – DataFrame (veiksnys × modelis) su dalimis 0..1; grupuotos horizontalios juostos."""
    import altair as alt
    long = shares.reset_index(names="f").melt("f", var_name="m", value_name="v")
    order = list(shares.sum(axis=1).sort_values(ascending=False).index)
    chart = alt.Chart(long).mark_bar(cornerRadiusEnd=2).encode(
        y=alt.Y("f:N", sort=order, title=None, axis=alt.Axis(labelLimit=320, labelFontSize=13, labelFontWeight="bold")),
        yOffset="m:N",
        x=alt.X("v:Q", title=value_label, axis=alt.Axis(format="%")),
        color=alt.Color("m:N", title=None, scale=alt.Scale(range=[MUTED, RED]),
                        legend=alt.Legend(orient="top", labelFontSize=13)),
        tooltip=[alt.Tooltip("f:N", title=""), alt.Tooltip("m:N", title=""), alt.Tooltip("v:Q", format=".0%")],
    ).properties(height=34 * len(order))
    st.altair_chart(chart, width="stretch")


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


