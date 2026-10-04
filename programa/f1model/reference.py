"""Žinynai: trasos, sinonimai, komandų spalvos, žaidėjai, GP pavadinimai, vairuotojų vardai.

Duomenys laikomi DB lentelėse (redaguojami programoje). Čia – tik PRADINĖS reikšmės, kurios
įrašomos, kai lentelė tuščia, ir `Reference` objektas, per kurį kiti moduliai juos naudoja.

Trasų charakteristikos (1–5): greitis, prispaudimas, gatvė (0 / 0.5 / 1), padangų apkrova,
lenkimo sunkumas (5 = beveik neįmanoma aplenkti). Panašumas = exp(-atstumas² / 2σ²).
"""
from dataclasses import dataclass

import numpy as np

#              trasa               greitis prisp. gatvė padangos lenkimas platuma  ilguma
TRACKS = [("Melbourne",            4, 3, 0.5, 2, 3, -37.8497, 144.9680),
          ("Shanghai",             3, 3, 0,   3, 2, 31.3389, 121.2197),
          ("Suzuka",               4, 4, 0,   3, 4, 34.8431, 136.5407),
          ("Sakhir",               3, 3, 0,   5, 1, 26.0325, 50.5106),
          ("Jeddah",               5, 2, 1,   2, 2, 21.6319, 39.1044),
          ("Miami Gardens",        3, 3, 0.5, 3, 3, 25.9581, -80.2389),
          ("Imola",                4, 3, 0,   2, 5, 44.3439, 11.7167),
          ("Monaco",               1, 5, 1,   1, 5, 43.7347, 7.4206),
          ("Barcelona",            3, 4, 0,   4, 4, 41.5700, 2.2611),
          ("Montréal",             4, 2, 0.5, 2, 2, 45.5000, -73.5228),
          ("Spielberg",            4, 3, 0,   3, 2, 47.2197, 14.7647),
          ("Silverstone",          5, 4, 0,   4, 3, 52.0786, -1.0169),
          ("Spa-Francorchamps",    5, 2, 0,   3, 1, 50.4372, 5.9714),
          ("Budapest",             2, 5, 0,   3, 5, 47.5789, 19.2486),
          ("Zandvoort",            3, 5, 0,   3, 5, 52.3888, 4.5409),
          ("Monza",                5, 1, 0,   2, 2, 45.6156, 9.2811),
          ("Baku",                 5, 2, 1,   2, 1, 40.3725, 49.8533),
          ("Marina Bay",           2, 5, 1,   3, 5, 1.2914, 103.8640),
          ("Austin",               3, 4, 0,   4, 2, 30.1328, -97.6411),
          ("Mexico City",          3, 4, 0,   2, 3, 19.4042, -99.0907),
          ("São Paulo",            3, 3, 0,   3, 1, -23.7036, -46.6997),
          ("Las Vegas",            5, 1, 1,   1, 1, 36.1147, -115.1728),
          ("Lusail",               4, 4, 0,   5, 3, 25.4900, 51.4542),
          ("Yas Marina",           3, 3, 0,   2, 3, 24.4672, 54.6031),
          ("Madrid",               3, 3, 1,   2, 3, 40.4650, -3.6150),
          ("Kuala Lumpur",         4, 4, 0,   5, 2, 2.7608, 101.7382)]
TRACK_ALIASES = {"Monte Carlo": "Monaco", "Yas Island": "Yas Marina", "Sepang": "Kuala Lumpur",
                 "Miami": "Miami Gardens", "Montreal": "Montréal", "Spa": "Spa-Francorchamps",
                 "Losail": "Lusail", "Sao Paulo": "São Paulo", "Singapore": "Marina Bay"}
TEAM_COLORS = [("mercedes", "#27F4D2"), ("red bull", "#3671C6"), ("ferrari", "#E8002D"), ("mclaren", "#FF8000"),
               ("aston", "#229971"), ("alpine", "#00A1E8"), ("racing bulls", "#6692FF"), ("rb f1", "#6692FF"),
               ("williams", "#64C4FF"), ("haas", "#B6BABD"), ("audi", "#F50537"), ("sauber", "#52E252"),
               ("cadillac", "#C9A961")]
PLAYERS = []   # totalizatoriaus žaidėjai (Excel lapų pavadinimai) – įrašomi programoje, jei turite savo lentelę
GP_NAMES = {"Australia": "Australian", "China": "Chinese", "Japan": "Japanese", "Bahrain": "Bahrain",
            "Saudi Arabia": "Saudi", "Miami": "Miami", "Canada": "Canadian", "Monaco": "Monaco",
            "Barcelona": "Barcelona", "Austria": "Austrian", "Britain": "British", "Belgium": "Belgian",
            "Hungary": "Hungarian", "Netherlands": "Dutch", "Monza": "Italian", "Madrid": "Spanish",
            "Azerbaijan": "Azerbaijan", "Singapore": "Singapore", "Austin": "United States",
            "Mexico": "Mexico City", "Brazil": "São Paulo", "Las Vegas": "Las Vegas", "Qatar": "Qatar",
            "Abu Dhabi": "Abu Dhabi"}
DRIVER_NAMES = {"ZHOU": "ZHO", "GUANYU": "ZHO", "KIMI ANTONELLI": "ANT"}

TRACK_COLS = ["trasa", "greitis", "prispaudimas", "gatve", "padangos", "lenkimo_sunkumas", "platuma", "ilguma"]
DEFAULTS = {  # lentelė -> pradinės eilutės
    "trasos": [dict(zip(TRACK_COLS, t)) for t in TRACKS],
    "trasu_sinonimai": [dict(vieta=k, trasa=v) for k, v in TRACK_ALIASES.items()],
    "komandos": [dict(raktazodis=k, spalva=v) for k, v in TEAM_COLORS],
    "zaidejai": [dict(vardas=p, aktyvus=1) for p in PLAYERS],
    "gp_pavadinimai": [dict(excel_pavadinimas=k, fastf1_dalis=v) for k, v in GP_NAMES.items()],
    "vairuotoju_vardai": [dict(vardas=k, kodas=v) for k, v in DRIVER_NAMES.items()],
}
SIGMA = 1.5


def seed(db):
    """Užpildo tuščias žinynų lenteles pradinėmis reikšmėmis (esamų duomenų neliečia)."""
    for table, rows in DEFAULTS.items():
        if db.query(f"SELECT COUNT(*) n FROM {table}").n.iloc[0] == 0:
            db.write(table, rows)


class TrackCatalog:
    def __init__(self, tracks, aliases):
        t = tracks.set_index("trasa")
        self.profiles = {c: np.array(r[["greitis", "prispaudimas", "gatve", "padangos"]], dtype=float)
                         for c, r in t.iterrows()}
        self._overtaking = t.lenkimo_sunkumas.to_dict()
        self._coords = {c: (r.platuma, r.ilguma) for c, r in t.iterrows() if r.platuma == r.platuma}
        self.aliases = aliases

    def circuit(self, location):
        return self.aliases.get(location, location)

    def similarity(self, a, b):
        pa, pb = self.profiles.get(self.circuit(a)), self.profiles.get(self.circuit(b))
        if pa is None or pb is None:
            return 0.0
        return float(np.exp(-float(np.sum((pa - pb) ** 2)) / (2 * SIGMA ** 2)))

    def most_similar(self, location, n=5):
        c = self.circuit(location)
        return sorted(((o, self.similarity(c, o)) for o in self.profiles if o != c), key=lambda x: -x[1])[:n]

    def overtaking(self, location):
        return self._overtaking.get(self.circuit(location), 3)

    def tyre_severity(self, location):
        p = self.profiles.get(self.circuit(location))
        return p[3] if p is not None else 3

    def coords(self, location):
        return self._coords.get(self.circuit(location))


@dataclass
class Reference:
    tracks: TrackCatalog
    team_colors: list
    players: list
    gp_names: dict
    driver_names: dict

    @classmethod
    def load(cls, db):
        q = db.query
        return cls(tracks=TrackCatalog(q("SELECT * FROM trasos"),
                                       dict(q("SELECT vieta, trasa FROM trasu_sinonimai").values)),
                   team_colors=[tuple(r) for r in q("SELECT raktazodis, spalva FROM komandos").values],
                   players=q("SELECT vardas FROM zaidejai WHERE aktyvus=1").vardas.tolist(),
                   gp_names=dict(q("SELECT excel_pavadinimas, fastf1_dalis FROM gp_pavadinimai").values),
                   driver_names=dict(q("SELECT vardas, kodas FROM vairuotoju_vardai").values))

    def team_color(self, team):
        t = (team or "").lower()
        return next((c for key, c in self.team_colors if key.lower() in t), "#888888")
