"""Požymių registras.

Kiekvienas požymis – funkcija, gaunanti `Context` (vienos sesijos duomenis) ir grąžinanti
neapdorotas reikšmes vairuotojams (didesnė = geriau, NaN = nežinoma). Reikšmės standartizuojamos
(z), o tada, jei nurodyta, padauginamos iš `scale(ctx)` (pvz. lietaus tikimybės).

NAUJAS POŽYMIS = nauja funkcija su @feature(...). Modelis, sąsaja, PARAMETRAI.md ir parametrai.json
jį pamato automatiškai – kito kodo keisti nereikia.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import cached_property
from typing import Callable, Optional

import numpy as np
import pandas as pd

from .config import COMPETITIVE, PRACTICE
from .dataset import kind_of


@dataclass(frozen=True)
class Feature:
    name: str
    label: str            # pavadinimas sąsajoje
    short: str            # trumpinys komandinėje eilutėje
    default_weight: float  # pradinis svoris mokymuisi
    description: str
    compute: Callable
    scale: Optional[Callable] = None


REGISTRY: dict[str, Feature] = {}


def feature(name, label, short, default_weight, description, scale=None):
    def register(fn):
        REGISTRY[name] = Feature(name, label, short, default_weight, description, fn, scale)
        return fn
    return register


def names():
    return list(REGISTRY)


# ------------------------------------------------------------------ sesijos kontekstas

class Context:
    """Vienos sesijos duomenų pjūviai, kuriuos naudoja požymiai (skaičiuojami tik prireikus)."""

    def __init__(self, data, season, rnd, session, before=None):
        self.data, self.season, self.rnd, self.session, self.before = data, season, rnd, session, before
        self.S, self.tracks = data.settings, data.ref.tracks   # priklausomybės – iš duomenų rinkinio
        self.kind = kind_of(session)
        self.target = data.session_rows(season, rnd, session)
        self.t0 = before or (self.target.date_utc.iloc[0] if not self.target.empty
                             else datetime.now(timezone.utc).isoformat())
        ev = data.event(season, rnd)
        self.circuit, self.location = ev.circuit, ev.location
        self.drivers = data.entry_list(season, rnd, session)

    def _target_value(self, col, default):
        v = self.target[col].iloc[0] if not self.target.empty else np.nan
        return float(v) if pd.notna(v) else default

    @cached_property
    def rain(self):
        return self._target_value("rain_prob", 0.0)

    @cached_property
    def temp(self):
        return self._target_value("temp_c", np.nan)

    @cached_property
    def kind_results(self):
        K = self.data.res[(self.data.res.kind == self.kind) & self.data.res.position.notna()]
        return K.assign(pos=K.position.clip(upper=20))

    @cached_property
    def weekend_results(self):
        r = self.data.res
        return r[(r.season == self.season) & (r["round"] == self.rnd) & (r.date_utc < self.t0)]

    @cached_property
    def practice(self):
        """Šio savaitgalio treniruotės, įvykusios iki sesijos, ir jų lietus."""
        before = self.data.session_rows(self.season, self.rnd)
        before = before[before.date_utc < self.t0]
        fp_done = set(before[before.session.isin(PRACTICE)].session)
        p = self.data.prac
        wp = p[(p.season == self.season) & (p["round"] == self.rnd) & p.session.isin(fp_done)]
        return wp, pd.to_numeric(before.set_index("session").rain_prob, errors="coerce").fillna(0).to_dict()

    @cached_property
    def odds(self):
        O = self.data.odds
        O = O[(O.season == self.season) & (O["round"] == self.rnd) & (O.session == self.session)]
        return O[O.price_ts.isna() | (O.price_ts <= self.t0)] if self.before is not None and not O.empty else O

    def residuals(self, frame, group):
        """Vietos nuokrypis nuo vairuotojo vidurkio grupėje (teigiamas = geriau nei įprastai)."""
        frame = frame.copy()
        frame["pos"] = frame.position.clip(upper=20)
        frame["resid"] = (frame.groupby(group).pos.transform("mean") - frame.pos).clip(-self.S.resid_clip, self.S.resid_clip)
        return frame

    @cached_property
    def history(self):
        """To paties tipo sesijos (be gedimų) per HISTORY_YEARS metų – trasų istorijai."""
        K = self.kind_results
        H = K[K.clean & (K.date_utc < self.t0) & (K.season >= self.season - self.S.history_years)]
        if H.empty:
            return H
        H = self.residuals(H, ["season", "driver"])
        H["yw"] = self.S.year_decay ** (self.season - H.season)
        return H

    @cached_property
    def all_clean_before(self):
        r = self.data.res
        return r[r.position.notna() & r.clean & (r.date_utc < self.t0)]

    def nan(self):
        return pd.Series(np.nan, index=self.drivers)


# ------------------------------------------------------------------ pagalbinės

def _z(s):
    """Standartizavimas; trūkstamos reikšmės = 0 (jokios informacijos)."""
    s = pd.Series(s, dtype=float)
    sd = s.std()
    if s.notna().sum() < 3 or not sd or np.isnan(sd):
        return s.fillna(0.0) * 0.0
    return ((s - s.mean()) / sd).clip(-3, 3).fillna(0.0)


def _fill_min(s):
    return s.fillna(s.min()) if s.notna().any() else s


def _recency_avg(df, value, halflife):
    order = sorted(df.date_utc.unique())
    age = {d: len(order) - 1 - i for i, d in enumerate(order)}
    w = df.date_utc.map(lambda d: 0.5 ** (age[d] / halflife))
    return (df[value] * w).groupby(df.driver).sum() / w.groupby(df.driver).sum()


def _weighted_mean(df, value, weight, shrink, drivers):
    return ((df[value] * weight).groupby(df.driver).sum() / (weight.groupby(df.driver).sum() + shrink)).reindex(drivers)


def combine_sources(o, drivers, S):
    """Kelių lažybų šaltinių tikimybių svertinis vidurkis. Naudojami tik šaltiniai su bent
    market_min_drivers vairuotojų; jei teigiamo svorio šaltinių nėra – imami atsarginiai (svoris 0)."""
    if o.empty:
        return pd.Series(np.nan, index=drivers)
    sizes = o.groupby("source").driver.nunique()
    good = [s for s, n in sizes.items() if n >= S.market_min_drivers]
    if not good:
        return pd.Series(np.nan, index=drivers)
    use = [s for s in good if S.source_weights.get(s, 0.5) > 0] or good
    P = o[o.source.isin(use)].pivot_table(index="driver", columns="source", values="prob", aggfunc="mean")
    W = pd.Series({s: (S.source_weights.get(s, 0.5) or 1.0) for s in P.columns})
    comb = (P.fillna(0) * W).sum(axis=1) / (P.notna() * W).sum(axis=1)
    return comb.reindex(drivers)


def _market(ctx, market, transform):
    p = combine_sources(ctx.odds[ctx.odds.market == market], ctx.drivers, ctx.S)
    return _fill_min(transform(p))


def _logit(p):
    p = p.clip(0.005, 0.98)
    return np.log(p / (1 - p))


def _gap_pct(v):
    return (v / v.min() - 1) * 100


def _is_race(ctx):
    return ctx.kind == "race"


# ------------------------------------------------------------------ požymiai (eilės tvarka svarbi)

@feature("form", "Sezono forma", "forma", 0.8,
         "Vidutinė vieta šio sezono to paties tipo sesijose (kvalifikacijos arba lenktynės); naujesnės "
         "sesijos sveriamos labiau (pusėjimo trukmė – forma_pusejimo_sesijos).")
def form(ctx):
    K = ctx.kind_results
    cur = K[(K.season == ctx.season) & (K.date_utc < ctx.t0)]
    f = -_recency_avg(cur, "pos", ctx.S.form_halflife) if not cur.empty else pd.Series(dtype=float)
    return _fill_min(f.reindex(ctx.drivers))


@feature("prev_season", "Praėjęs sezonas", "pr.sez", 0.3,
         "Vairuotojo vidutinė vieta praėjusiame sezone to paties tipo sesijose.")
def prev_season(ctx):
    K = ctx.kind_results
    return _fill_min(-K[K.season == ctx.season - 1].groupby("driver").pos.mean().reindex(ctx.drivers))


@feature("track", "Istorija šioje trasoje", "trasa", 0.2,
         "Kiek geriau/blogiau nei įprastai vairuotojui sekėsi šioje trasoje ankstesniais metais "
         "(vieta lyginama su to sezono vidurkiu; senesni metai sveriami mažiau).")
def track(ctx):
    H = ctx.history
    same = H[H.circuit == ctx.circuit] if not H.empty else H
    return ctx.nan() if same.empty else _weighted_mean(same, "resid", same.yw, ctx.S.track_shrink, ctx.drivers)


@feature("similar", "Panašios trasos", "pan.tr", 0.2,
         "Tas pats, tik panašiose trasose (pagal žinyno „trasos“ charakteristikas), įskaitant šį sezoną.")
def similar(ctx):
    H = ctx.history
    if H.empty:
        return ctx.nan()
    other = H[H.circuit != ctx.circuit]
    w = other.yw * other.circuit.map(lambda c: ctx.tracks.similarity(ctx.circuit, c))
    return _weighted_mean(other, "resid", w, ctx.S.similar_shrink, ctx.drivers) if w.sum() > 0 else ctx.nan()


@feature("pace", "Treniruočių tempas", "tempas", 0.5,
         "Šio savaitgalio treniruotės: kvalifikacijai – greitis vienu ratu (kvalifikacijos_tempo_matai), "
         "lenktynėms – ilgų serijų tempas (atsilikimas % nuo greičiausio). Treniruotės, kurių sąlygos "
         "(sausa/šlapia) neatitinka laukiamų, sveriamos mažiau.")
def pace(ctx):
    wp, fp_rain = ctx.practice
    if wp.empty:
        return ctx.nan()
    parts, weights = [], []
    for i, (fp, g) in enumerate(sorted(wp.groupby("session"), key=lambda x: x[0])):
        g = g.set_index("driver")
        if ctx.kind == "quali":
            gaps = [_gap_pct(g[c]) for c in ctx.S.quali_pace_metrics if c in g and g[c].notna().sum() >= 6]
            gap = pd.concat(gaps or [_gap_pct(g["best_lap_s"])], axis=1).mean(axis=1)
        else:
            gap = _gap_pct(g["long_run_s"] if g["long_run_s"].notna().sum() >= 6 else g["best_lap_s"])
        parts.append(-gap.reindex(ctx.drivers))
        weights.append((1.0 + i) * max(0.2, 1.0 - abs(fp_rain.get(fp, 0.0) - ctx.rain)))
    P = pd.concat(parts, axis=1)
    W = P.notna().mul(weights, axis=1).sum(axis=1)
    return (P.fillna(0).mul(weights, axis=1).sum(axis=1) / W).where(W > 0)


@feature("weekend", "Savaitgalio rezultatai", "savaitg", 0.8,
         "Lenktynėms/sprintui – starto pozicija; kvalifikacijai – ankstesnių šio savaitgalio sesijų "
         "(pvz. sprinto kvalifikacijos) rezultatai.")
def weekend(ctx):
    wk = ctx.weekend_results
    if ctx.kind == "race":
        tgt = ctx.data.results_of(ctx.season, ctx.rnd, ctx.session)
        fia_grid = ctx.data.fia_grid(ctx.season, ctx.rnd, ctx.session)
        if not tgt.empty and tgt.grid.notna().any():
            grid = tgt.set_index("driver").grid
        elif fia_grid:  # oficiali FIA rikiuotė su baudomis (lenktynės dar nevyko)
            grid = pd.Series(fia_grid)
        else:
            grid = wk[wk.session == ("Q" if ctx.session == "R" else "SQ")].set_index("driver").position
        return ctx.nan() if grid.empty else -grid.reindex(ctx.drivers).astype(float).fillna(20)
    prevs = wk[wk.session.isin(COMPETITIVE)]
    return ctx.nan() if prevs.empty else -prevs.groupby("driver").position.mean().reindex(ctx.drivers)


@feature("wet", "Lietus × sugebėjimas lyjant", "lietus", 0.3,
         "Kiek geriau/blogiau nei įprastai vairuotojui sekėsi praeities sesijose, kai trasoje lijo (pagal trasos "
         "jutiklius, 2023+), padauginta iš lietaus tikimybės šiai sesijai (kalibruota orų prognozė). Sausoje = 0.",
         scale=lambda ctx: ctx.rain)
def wet(ctx):
    A = ctx.all_clean_before
    if ctx.rain <= 0 or A.empty:
        return ctx.nan()
    W = ctx.residuals(A, ["season", "kind", "driver"])
    W = W[W.rain_prob >= ctx.S.wet_threshold]
    return ctx.nan() if W.empty else (W.resid.groupby(W.driver).sum() / (W.groupby("driver").size() + ctx.S.wet_shrink)).reindex(ctx.drivers)


def _heat_anomaly(ctx):
    return float(np.clip((ctx.temp - ctx.S.heat_ref_c) / ctx.S.heat_scale_c, -2.5, 2.5)) if pd.notna(ctx.temp) else 0.0


@feature("heat", "Temperatūra × vairuotojo jautrumas", "temp", 0.1,
         "Ar vairuotojui istoriškai sekasi geriau karštyje, ar vėsoje (nuokrypio priklausomybė nuo "
         "oro temperatūros), padauginta iš to, kiek prognozuojama temperatūra karštesnė/vėsesnė nei įprasta.",
         scale=_heat_anomaly)
def heat(ctx):
    T = ctx.all_clean_before
    T = T[T.temp_c.notna()]
    if _heat_anomaly(ctx) == 0 or T.empty:
        return ctx.nan()
    T = ctx.residuals(T, ["season", "kind", "driver"])
    tz = ((T.temp_c - ctx.S.heat_ref_c) / ctx.S.heat_scale_c).clip(-2.5, 2.5)
    return ((T.resid * tz).groupby(T.driver).sum() / ((tz ** 2).groupby(T.driver).sum() + ctx.S.heat_shrink)).reindex(ctx.drivers)


@feature("tyre_deg", "Strategija: padangų dėvėjimasis", "padang", 0.1,
         "Tik lenktynėms/sprintui. Kiek rato laikas blogėja per ratą šio savaitgalio ilgose treniruočių "
         "serijose (mažiau = geriau), padauginta iš trasos padangų apkrovos.",
         scale=lambda ctx: ctx.tracks.tyre_severity(ctx.location) / 3.0)
def tyre_deg(ctx):
    wp, _ = ctx.practice
    if not _is_race(ctx) or wp.empty or wp.deg_s_per_lap.notna().sum() < 6:
        return ctx.nan()
    d = wp.groupby("driver").deg_s_per_lap.median()
    return -d.clip(d.quantile(0.1), d.quantile(0.9)).reindex(ctx.drivers)


@feature("overtake", "Strategija: lenkimo sunkumas", "lenkim", 0.2,
         "Tik lenktynėms/sprintui. Starto pozicija × trasos lenkimo sunkumas: kur sunku lenkti (Monakas, "
         "Singapūras), starto vieta lemia daugiau; kur lengva (Spa, Baku) – mažiau.",
         scale=lambda ctx: (ctx.tracks.overtaking(ctx.location) - 3) / 2.0 if _is_race(ctx) else 0.0)
def overtake(ctx):
    return weekend(ctx) if _is_race(ctx) else ctx.nan()


# Išbandyta ir atmesta (2026-10): „Bolido atnaujinimai“ (FIA Car Presentation, našumo detalių skaičius šiame
# etape arba per 3 etapus) – 2025–2026 m. 296/295 tšk. vs 300 be jo. Atnaujinimai rodomi tik kaip informacija.

MARKET_FOR = {"Q": "pole", "SQ": "pole", "R": "win", "S": "win"}


@feature("market", "Lažybų rinka: laimėtojas", "rinka", 0.8,
         "Rinkos tikimybė laimėti sesiją (kvalifikacijai – pole, lenktynėms – pergalė): Kalshi ir "
         "Polymarket svertinis vidurkis (lažybininkai – atsarginis), paskutinė kaina prieš sesiją, log skalėje.")
def market(ctx):
    return _market(ctx, MARKET_FOR[ctx.session], lambda p: np.log(p.clip(lower=0.003)))


@feature("market_top3", "Lažybų rinka: podiumas", "rink.T3", 0.4,
         "Rinkos tikimybė patekti į TOP3 (lenktynėms), logit skalėje. Svarbi mūsų taškų sistemai.")
def market_top3(ctx):
    return _market(ctx, "podium", _logit)


@feature("market_top5", "Lažybų rinka: TOP5", "rink.T5", 0.2,
         "Kalshi rinkos tikimybė finišuoti TOP5 (lenktynėms ir sprintams), logit skalėje. "
         "Padeda atskirti, kas realiai kovoja dėl P3.")
def market_top5(ctx):
    return _market(ctx, "top5", _logit)


# ------------------------------------------------------------------ požymių matrica

def build(data, season, rnd, session, before=None):
    """Standartizuota požymių lentelė [vairuotojas × požymis] (rezultatas talpinamas data.cache)."""
    key = (season, rnd, session, before)
    if key in data.cache:
        return data.cache[key]
    ctx = Context(data, season, rnd, session, before)
    raw = pd.DataFrame({f.name: f.compute(ctx) for f in REGISTRY.values()}, index=ctx.drivers)
    X = raw.apply(_z)
    for f in REGISTRY.values():
        if f.scale:
            X[f.name] = X[f.name] * f.scale(ctx)
    X.index.name = "driver"
    X.attrs.update(raw=raw, rain=ctx.rain, temp=ctx.temp)
    data.cache[key] = X
    return X
