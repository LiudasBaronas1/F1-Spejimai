"""Sugeneruoja PARAMETRAI.md – visi požymiai, jų svoriai, nustatymai ir žinynai (iš registrų ir DB)."""
import json
from datetime import datetime

from . import features, model
from .config import SESSION_NAMES_LT
from .settings import EDITABLE
from .sources import odds, weather


def _calibration_text():
    if not weather.CALIBRATION_FILE.exists():
        return ""
    c = json.loads(weather.CALIBRATION_FILE.read_text(encoding="utf-8"))
    return (f" Kalibruota pagal {c['sessions']} sesijų ({c['wet_sessions']} lietingų); paklaida (Brier) "
            f"{c['brier_new']:.3f}, ankstesnio metodo {c['brier_old']:.3f}, vien vidurkio {c['brier_base']:.3f}.")


def _table(header, rows):
    return ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)] + \
           ["| " + " | ".join(map(str, r)) + " |" for r in rows]


def write(path, data, fitted, last=None):
    """path – PARAMETRAI.md; fitted = model.fit_all(data); last = (GP, sesija, spėjimas, trasa)."""
    S, tracks = data.settings, data.ref.tracks
    (wq, nq), (wr, nr) = fitted["quali"], fitted["race"]
    eq, er = model.effective_weights(wq, S), model.effective_weights(wr, S)
    sq, sr = model.importance(eq), model.importance(er)
    L = ["# Modelio parametrai", "",
         f"*Atnaujinta automatiškai {datetime.now():%Y-%m-%d %H:%M}. Šio failo keisti nereikia – keičiami "
         "parametrai yra `parametrai.json`, o žinynai (trasos, komandos, žaidėjai) – programos meniu „Duomenys“ → „Žinynai“.*", "",
         "## 1. Požymiai ir jų svoriai", "",
         "Požymiai standartizuoti (vidutinis vairuotojas = 0, geresnis = teigiamas), todėl svorius galima "
         "lyginti tarpusavyje. **Svarba** – kokią dalį sprendimo lemia požymis. **Daugiklis** – rankinis "
         "pataisymas (1 = kaip išmokta, 0 = išjungti).", ""]
    L += _table(["Požymis", "Ką reiškia", "Kvalif. svoris", "Kvalif. svarba", "Lenkt. svoris", "Lenkt. svarba",
                 "Daugiklis"],
                [(f"**{f.label}** (`{f.name}`)", f.description, f"{eq[f.name]:+.2f}", f"{sq[f.name]:.0%}",
                  f"{er[f.name]:+.2f}", f"{sr[f.name]:.0%}", f"{S.multiplier(f.name):g}")
                 for f in features.REGISTRY.values()])
    L += ["", f"Svoriai išmokti iš {nq} kvalifikacijų ir {nr} lenktynių/sprintų ({S.train_seasons}).", "",
          "## 2. Nustatymai (`parametrai.json`)", ""]
    L += _table(["Raktas", "Reikšmė"], [(f"`{k}`", getattr(S, a)) for k, a in EDITABLE.items()])
    L += ["", "## 3. Duomenys ir taisyklės", "",
          "- **Rezultatai**: lenktynės/sprintai vertinami pagal finišą trasoje (baudos po finišo neįskaičiuojamos).",
          "- **Orai**: įvykusioms sesijoms – FastF1 trasos jutikliai; artėjančioms – Open-Meteo prognozė "
          f"(trasa + 4 taškai po {weather.REGION_KM} km, ±{weather.WINDOW_PAD_H} val.), kalibruota pagal tai, "
          "ar trasoje iš tikrųjų lijo." + _calibration_text(),
          f"- **Lažybų rinkos**: Kalshi, Polymarket (svoriai `lazybu_saltiniu_svoriai`), lažybininkai – atsarginis; "
          f"paskutinė kaina prieš sesiją, min. apyvarta {odds.MIN_VOLUME_USD} $.",
          "- **Taškų optimizavimas**: tikėtini taškai = P(TOP3) + P(tiksli vieta); perrenkami visi trejetai.", "",
          "## 4. Trasų charakteristikos (žinynas „trasos“)", ""]
    L += _table(["Trasa", "Greitis", "Prispaudimas", "Gatvė", "Padangos", "Lenkimo sunkumas"],
                [(c, *(f"{v:g}" for v in p), f"{tracks.overtaking(c):g}") for c, p in sorted(tracks.profiles.items())])
    if last:
        name, session, out, circ = last
        L += ["", f"## 5. Paskutinis spėjimas: {name} – {SESSION_NAMES_LT[session]}", "",
              f"Lietus **{out['rain']:.0%}**, trasa **{circ}**, panašiausios: "
              + ", ".join(f"{c} ({s:.0%})" for c, s in tracks.most_similar(circ, 5)) + ".", ""]
        L += _table(["Vairuotojas", "P1", "P2", "P3", "TOP3"] + [f.label for f in features.REGISTRY.values()],
                    [(d, *(f"{r[c]:.0%}" for c in ("P1", "P2", "P3", "TOP3")),
                      *(f"{r[f]:+.1f}" for f in features.names())) for d, r in out["table"].head(12).iterrows()])
        L += ["", f"Siūlomas spėjimas: **{' – '.join(out['pick'])}**, tikėtini taškai {out['expected']:.2f}."]
    path.write_text("\n".join(L) + "\n", encoding="utf-8")
