"""Modelio nustatymai (`Settings`) ir jų įkėlimas/išsaugojimas į parametrai.json.
`Settings` objektas perduodamas kaip priklausomybė (per `Dataset`), globalios būsenos nėra."""
import json
import logging
from dataclasses import dataclass, field, replace

log = logging.getLogger("f1")


@dataclass
class Settings:
    # mokymasis
    train_seasons: list = field(default_factory=lambda: [2024, 2025, 2026])
    current_season_sample_weight: float = 2.0  # šio sezono sesijos svarbesnės (nauji reglamentai)
    l2: float = 0.1                            # svorių reguliarizacija
    disabled: list = field(default_factory=list)  # išjungti požymiai (nemokomi ir nenaudojami)
    n_sim: int = 20000                         # Monte Carlo simuliacijų skaičius
    # forma ir istorija
    form_halflife: float = 3.0
    history_years: int = 3
    year_decay: float = 0.7
    track_shrink: float = 1.0
    similar_shrink: float = 2.0
    resid_clip: float = 8
    # oras
    wet_chaos: float = 0.35                    # pradinė reikšmė: lyjant stiprumai suspaudžiami ×(1 − chaosas·lietus)
    wet_threshold: float = 0.5
    wet_shrink: float = 2.0
    heat_ref_c: float = 22.0
    heat_scale_c: float = 7.0
    heat_shrink: float = 15.0
    # gedimai (lenktynėms ir sprintams)
    dnf_seasons: int = 2                       # kiek sezonų atgal skaičiuojamas gedimų dažnis
    dnf_shrink: float = 20.0                   # kiek „vidutinių“ lenktynių pridedama prie vairuotojo/komandos istorijos
    # treniruotės ir lažybos
    quali_pace_metrics: list = field(default_factory=lambda: ["best_lap_s"])
    source_weights: dict = field(default_factory=lambda: {"kalshi": 1.0, "polymarket": 0.5, "bookmakers": 0.0})
    market_min_drivers: int = 6
    # rankiniai požymių daugikliai (1 = kaip išmokta, 0 = išjungti)
    multipliers: dict = field(default_factory=dict)

    def multiplier(self, feature):
        return float(self.multipliers.get(feature, 1.0))

    def active(self, names):
        """Požymiai, kuriuos modelis naudoja (registro tvarka)."""
        return [f for f in names if f not in self.disabled]

    def with_values(self, **values):
        """Kopija su pakeistomis reikšmėmis (eksperimentams – originalas nekeičiamas)."""
        return replace(self, **values)


# parametrai.json raktas -> Settings laukas
EDITABLE = {
    "forma_pusejimo_sesijos": "form_halflife", "metu_svoris_trasos_istorijoje": "year_decay",
    "trasos_istorijos_metai": "history_years", "lietaus_chaosas": "wet_chaos",
    "lietinga_sesija_nuo": "wet_threshold", "sio_sezono_svarba_mokantis": "current_season_sample_weight",
    "mokymosi_sezonai": "train_seasons", "reguliarizacija": "l2", "simuliaciju_skaicius": "n_sim",
    "isjungti_pozymiai": "disabled", "gedimu_sezonai": "dnf_seasons", "gedimu_istorijos_svoris": "dnf_shrink",
    "kvalifikacijos_tempo_matai": "quali_pace_metrics", "lazybu_saltiniu_svoriai": "source_weights",
}
HELP = ("Čia galite keisti modelio parametrus. Pilnas aprašymas – PARAMETRAI.md. Daugikliai: 1 = kaip "
        "išmokta iš duomenų, 0.5 = perpus mažiau, 0 = neatsižvelgti, 2 = dvigubai daugiau. Pakeitę "
        "išsaugokite failą ir programoje paspauskite 'Atnaujinti duomenis' (arba perkraukite programą).")


def field_name(key):
    """parametrai.json raktas arba Settings lauko pavadinimas -> Settings laukas (None, jei nėra)."""
    return EDITABLE.get(key) or (key if key in Settings.__dataclass_fields__ else None)


def save(settings, path, feature_names):
    data = {"_paaiskinimas": HELP,
            "pozymiu_daugikliai": {f: settings.multiplier(f) for f in feature_names},
            "nustatymai": {k: getattr(settings, a) for k, a in EDITABLE.items()}}
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load(path, feature_names):
    """parametrai.json -> Settings. Trūkstamus (naujus) laukus faile papildo, esamos reikšmės išlieka;
    nebenaudojami raktai pašalinami."""
    s = Settings()
    if not path.exists():
        save(s, path, feature_names)
        return s
    try:
        p = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as e:
        log.warning("parametrai.json klaida (%s) – naudojamos numatytosios reikšmės", e)
        return s
    s.multipliers.update({f: float(v) for f, v in p.get("pozymiu_daugikliai", {}).items() if f in feature_names})
    for k, v in p.get("nustatymai", {}).items():
        if k in EDITABLE:
            setattr(s, EDITABLE[k], v)
    if set(p.get("pozymiu_daugikliai", {})) != set(feature_names) or set(p.get("nustatymai", {})) != set(EDITABLE):
        save(s, path, feature_names)
    return s
