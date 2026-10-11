"""Plackett-Luce spėjimų modelis.

Stiprumas  theta = Σ svoris_i · požymis_i × (1 − chaosas · lietus) × (sprinto daugiklis, jei sprintas)
P(rezultatų eilė) ~ exp(theta); svoriai ir sprinto daugiklis išmokstami iš tikrų TOP3 rezultatų
(maks. tikėtinumas), chaosas – nustatymas. Lenktynėms tikimybė, kad vairuotojas nefinišuos
(`features.dnf_probability`), įskaičiuojama simuliacijoje.
Monte Carlo simuliacija -> P(P1), P(P2), P(P3). Spėjimas – trejetas su daugiausiai tikėtinų taškų:
Σ [P(TOP3) + P(tiksli vieta)]  (2 tšk. už tikslią vietą, 1 tšk. už TOP3).

Išbandyta ir atmesta (2026-10, porinis bootstrap 2025–2026 m.): chaoso mokymasis iš duomenų (nepagerino),
mokymasis tik iš finišavusių (pablogino log-loss).

Nustatymai imami iš `data.settings`, duomenų bazė perduodama įrašymo funkcijoms – globalios būsenos nėra.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import permutations

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from . import features
from .config import QUALI_TYPE, RACE_TYPE, SPRINT_TYPE
from .dataset import kind_of

KINDS = {"quali": QUALI_TYPE, "race": RACE_TYPE}
SPRINT_L2 = 1.0             # sprinto daugiklio traukimas link 1 (kai sprintų mažai – lieka arti 1)
MIN_SAMPLES = 6


@dataclass
class KindModel:
    """Išmoktas vienos rūšies (kvalifikacijos / lenktynių) modelis."""
    weights: dict           # požymis -> svoris
    n_samples: int
    chaos: float            # lyjant stiprumų skirtumai mažinami ×(1 − chaos · lietus) (nustatymas)
    sprint: float = 1.0     # sprinto sesijose stiprumų skirtumai ×sprint (trumpesnė = atsitiktinesnė, jei < 1)

    def scale(self, session, rain):
        return (1.0 - self.chaos * rain) * (self.sprint if session in SPRINT_TYPE else 1.0)

    def effective(self, S):
        """Išmokti svoriai × rankiniai daugikliai (išjungti požymiai – 0)."""
        active = set(S.active(features.names()))
        return {f: self.weights.get(f, 0.0) * S.multiplier(f) if f in active else 0.0 for f in features.names()}


def default_model(S, n=0):
    return KindModel({f: features.REGISTRY[f].default_weight for f in S.active(features.names())}, n, S.wet_chaos)


def plackett_luce_loglik(theta, top3_idx):
    ll, remaining = 0.0, np.ones(len(theta), bool)
    for i in top3_idx:
        ll += theta[i] - np.log(np.exp(theta[remaining]).sum())
        remaining[i] = False
    return ll


# ------------------------------------------------------------------ mokymasis

@dataclass
class Sample:
    X: np.ndarray           # [vairuotojai × aktyvūs požymiai] × lietaus suspaudimas
    top3: list              # TOP3 eilučių indeksai X
    weight: float
    sprint: bool


def training_samples(kind, data, upto=None, progress=None):
    S = data.settings
    names = S.active(features.names())
    done = data.done_sessions(S.train_seasons, KINDS[kind], before=upto)
    latest = done.season.max() if not done.empty else None
    samples = []
    for i, (_, s) in enumerate(done.iterrows()):
        if progress:
            progress(i / len(done), f"{i + 1}/{len(done)} · {s.season} R{s['round']:02d} {s.session}")
        top = data.top3(s.season, s["round"], s.session)
        X = features.build(data, s.season, s["round"], s.session, before=s.date_utc)
        idx = [X.index.get_loc(d) for d in top if d in X.index]
        if len(idx) == 3:
            sw = S.current_season_sample_weight if s.season == latest else 1.0
            rain_scale = 1.0 - S.wet_chaos * X.attrs["rain"]
            samples.append(Sample(X[names].values * rain_scale, idx, sw, s.session in SPRINT_TYPE))
    return samples


def fit_weights(kind, data, upto=None, progress=None):
    """KindModel, išmoktas iš sesijų iki `upto`. progress(dalis 0..1, detalė) – eigos juostai (nebūtina)."""
    S = data.settings
    names = S.active(features.names())
    start = default_model(S)
    samples = training_samples(kind, data, upto, progress)
    if progress:
        progress(1.0, "")   # požymiai paruošti, toliau – svorių optimizavimas
    if len(samples) < MIN_SAMPLES:
        return default_model(S, len(samples))
    n, k = sum(s.weight for s in samples), len(names)
    has_sprint = any(s.sprint for s in samples)

    def nll(p):
        w, log_sprint = p[:k], p[k]   # sprinto daugiklis – log skalėje (visada teigiamas)
        ll = sum(s.weight * plackett_luce_loglik((s.X @ w) * (np.exp(log_sprint) if s.sprint else 1.0), s.top3)
                 for s in samples)
        return -ll + n * S.l2 * (w @ w) + n * SPRINT_L2 * log_sprint ** 2

    p0 = np.r_[[start.weights[f] for f in names], 0.0]
    bounds = [(None, None)] * k + [(-1.5, 1.5) if has_sprint else (0.0, 0.0)]
    p = minimize(nll, p0, method="L-BFGS-B", bounds=bounds).x
    return KindModel(dict(zip(names, map(float, p[:k]))), len(samples), S.wet_chaos, float(np.exp(p[k])))


def fit_all(data, progress=None):
    """{"quali"/"race": KindModel}. progress(dalis 0..1, modelis, dalis to modelio viduje, detalė)."""
    part = lambda i, k: (lambda f, detail="": progress((i + f) / len(KINDS), k, f, detail))
    return {k: fit_weights(k, data, progress=part(i, k) if progress else None) for i, k in enumerate(KINDS)}


def importance(w):
    """Kokią dalį sprendimo lemia kiekvienas požymis (pagal |svorį|)."""
    tot = sum(abs(v) for v in w.values()) or 1
    return {k: abs(v) / tot for k, v in w.items()}


# ------------------------------------------------------------------ spėjimas

def simulate(theta, n, dnf=None, seed=0):
    """Plackett-Luce = stiprumas + Gumbel triukšmas, vieta po vietos (P1, tada P2 iš likusių, tada P3).
    dnf – kiekvieno vairuotojo tikimybė nefinišuoti (tokie į vietas nepatenka). Grąžina [vairuotojas × vieta]."""
    n, d = int(n), len(theta)
    rng = np.random.default_rng(seed)
    rows = np.arange(n)
    taken = rng.random((n, d)) < dnf[None, :] if dnf is not None else np.zeros((n, d), bool)
    taken[taken.sum(axis=1) > d - 3] = False      # (praktiškai neįmanoma) – kad liktų bent trys
    probs = np.zeros((d, 3))
    for k in range(3):
        perf = theta[None, :] + rng.gumbel(size=(n, d))
        perf[taken] = -np.inf
        pick = perf.argmax(axis=1)
        probs[:, k] = np.bincount(pick, minlength=d) / n
        taken[rows, pick] = True
    return probs


def best_pick(probs, drivers):
    """Trejetas su didžiausiais tikėtinais taškais."""
    p_top3 = probs.sum(axis=1)
    value = lambda trio: sum(p_top3[d] + probs[d, pos] for pos, d in enumerate(trio))
    best = max(permutations(np.argsort(-p_top3)[:10], 3), key=value)
    return [drivers[i] for i in best], value(best)


def predict(data, season, rnd, session, fitted=None, before=None):
    """fitted – KindModel (None – išmokoma iš sesijų iki `before`). Grąžina spėjimą, tikimybių lentelę ir
    kiekvieno požymio indėlį į vairuotojo stiprumą (contrib)."""
    S = data.settings
    X = features.build(data, season, rnd, session, before=before)
    rain, temp, dnf = X.attrs["rain"], X.attrs["temp"], X.attrs["dnf"].values
    X = X.copy()
    X.attrs = {}    # grąžinamos lentelės be X.attrs: pandas jas lygina sujungiant, o lentelių lyginimas – klaida
    fitted = fitted or fit_weights(kind_of(session), data, upto=before)
    w, names = fitted.effective(S), features.names()
    scale = fitted.scale(session, rain)
    contrib = X[names] * np.array([w[f] for f in names]) * scale
    probs = simulate(contrib.sum(axis=1).values, S.n_sim, dnf)
    pick, ev = best_pick(probs, list(X.index))
    table = pd.DataFrame(probs, index=X.index, columns=["P1", "P2", "P3"]).assign(TOP3=probs.sum(axis=1), DNF=dnf)
    table = table.join(X).sort_values("TOP3", ascending=False)
    return dict(pick=pick, expected=ev, table=table, contrib=contrib.loc[table.index], weights=w,
                rain=rain, temp=temp)


def score(pick, actual_top3):
    """Taškai pagal mūsų taisykles."""
    return sum(2 if pos < len(actual_top3) and actual_top3[pos] == d else int(d in actual_top3)
               for pos, d in enumerate(pick))


# ------------------------------------------------------------------ įrašymas

def save_weights(db, fitted):
    now = datetime.now(timezone.utc).isoformat()
    rows = []
    for kind, m in fitted.items():
        values = {**m.weights, "_sprinto_daugiklis": m.sprint}
        rows += [dict(kind=kind, name=k, value=float(v), n_samples=m.n_samples, fitted_at=now) for k, v in values.items()]
    db.write("model_params", rows, replace_where=("1=1", ()))


def save_prediction(db, season, rnd, session, out):
    now = datetime.now(timezone.utc).isoformat()
    db.write("predictions", [dict(created_at=now, season=season, round=rnd, session=session, driver=d,
                                  p1=float(r.P1), p2=float(r.P2), p3=float(r.P3), p_top3=float(r.TOP3),
                                  pick_pos=(out["pick"].index(d) + 1) if d in out["pick"] else None)
                             for d, r in out["table"].iterrows()])
