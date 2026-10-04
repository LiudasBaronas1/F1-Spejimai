"""Plackett-Luce spėjimų modelis.

Stiprumas  theta = Σ svoris_i · požymis_i   (požymiai – features.py registre)
P(rezultatų eilė) ~ exp(theta); svoriai išmokstami iš tikrų TOP3 rezultatų (maks. tikėtinumas).
Monte Carlo simuliacija -> P(P1), P(P2), P(P3). Spėjimas – trejetas su daugiausiai tikėtinų
taškų: Σ [P(TOP3) + P(tiksli vieta)]  (2 tšk. už tikslią vietą, 1 tšk. už TOP3).

Nustatymai imami iš `data.settings`, duomenų bazė perduodama įrašymo funkcijoms – globalios būsenos nėra.
"""
from datetime import datetime, timezone
from itertools import permutations

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from . import features
from .config import QUALI_TYPE, RACE_TYPE
from .dataset import kind_of

KINDS = {"quali": QUALI_TYPE, "race": RACE_TYPE}


def chaos(X, S):
    """Lyjant rezultatai atsitiktinesni: stiprumų skirtumai sumažinami."""
    return 1.0 - S.wet_chaos * X.attrs.get("rain", 0.0)


def top3_loglik(theta, top3_idx):
    ll, remaining = 0.0, np.ones(len(theta), bool)
    for i in top3_idx:
        ll += theta[i] - np.log(np.exp(theta[remaining]).sum())
        remaining[i] = False
    return ll


# ------------------------------------------------------------------ mokymasis

def training_samples(kind, data, upto=None):
    S, names = data.settings, features.names()
    done = data.done_sessions(S.train_seasons, KINDS[kind], before=upto)
    latest = done.season.max() if not done.empty else None
    samples = []
    for _, s in done.iterrows():
        top = data.top3(s.season, s["round"], s.session)
        X = features.build(data, s.season, s["round"], s.session, before=s.date_utc)
        idx = [X.index.get_loc(d) for d in top if d in X.index]
        if len(idx) == 3:
            sw = S.current_season_sample_weight if s.season == latest else 1.0
            samples.append((X[names].values * chaos(X, S), idx, sw))
    return samples


def fit_weights(kind, data, upto=None):
    """Svoriai, išmokti iš sesijų iki `upto`. Grąžina (svoriai, imčių skaičius)."""
    names = features.names()
    default = {f: features.REGISTRY[f].default_weight for f in names}
    samples = training_samples(kind, data, upto)
    if len(samples) < 6:
        return default, len(samples)
    n = sum(sw for _, _, sw in samples)
    penalised = np.array([0.0 if f in data.settings.l2_free else data.settings.l2 for f in names])

    def nll(w):
        return -sum(sw * top3_loglik(X @ w, idx) for X, idx, sw in samples) + n * (penalised * w) @ w

    opt = minimize(nll, np.array(list(default.values())), method="L-BFGS-B")
    return dict(zip(names, map(float, opt.x))), len(samples)


def fit_all(data):
    return {k: fit_weights(k, data) for k in KINDS}


def effective_weights(w, S):
    """Išmokti svoriai × rankiniai daugikliai."""
    return {f: w[f] * S.multiplier(f) for f in features.names()}


def importance(w):
    """Kokią dalį sprendimo lemia kiekvienas požymis (pagal |svorį|)."""
    tot = sum(abs(v) for v in w.values()) or 1
    return {k: abs(v) / tot for k, v in w.items()}


# ------------------------------------------------------------------ spėjimas

def simulate(theta, n, seed=0):
    """Plackett-Luce = stiprumas + Gumbel triukšmas, vieta po vietos (P1, tada P2 iš likusių, tada P3).
    Grąžina [vairuotojas × vieta] tikimybes."""
    n, d = int(n), len(theta)
    rng = np.random.default_rng(seed)
    taken, rows = np.zeros((n, d), bool), np.arange(n)
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


def predict(data, season, rnd, session, weights=None, before=None):
    S = data.settings
    X = features.build(data, season, rnd, session, before=before)
    if weights is None:
        weights = fit_weights(kind_of(session), data, upto=before)[0]
    w = effective_weights(weights, S)
    names = features.names()
    theta = X[names].values @ np.array([w[f] for f in names]) * chaos(X, S)
    probs = simulate(theta, S.n_sim)
    pick, ev = best_pick(probs, list(X.index))
    table = pd.DataFrame(probs, index=X.index, columns=["P1", "P2", "P3"]).assign(TOP3=probs.sum(axis=1))
    table = table.join(X).sort_values("TOP3", ascending=False)
    return dict(pick=pick, expected=ev, table=table, weights=w, rain=X.attrs["rain"], temp=X.attrs["temp"])


def score(pick, actual_top3):
    """Taškai pagal mūsų taisykles."""
    return sum(2 if pos < len(actual_top3) and actual_top3[pos] == d else int(d in actual_top3)
               for pos, d in enumerate(pick))


# ------------------------------------------------------------------ įrašymas

def save_weights(db, fitted):
    now = datetime.now(timezone.utc).isoformat()
    db.write("model_params", [dict(kind=kind, name=k, value=float(v), n_samples=n, fitted_at=now)
                              for kind, (w, n) in fitted.items() for k, v in w.items()])


def save_prediction(db, season, rnd, session, out):
    now = datetime.now(timezone.utc).isoformat()
    db.write("predictions", [dict(created_at=now, season=season, round=rnd, session=session, driver=d,
                                  p1=float(r.P1), p2=float(r.P2), p3=float(r.P3), p_top3=float(r.TOP3),
                                  pick_pos=(out["pick"].index(d) + 1) if d in out["pick"] else None)
                             for d, r in out["table"].iterrows()])
