"""Trasos informacija skirtukui „Trasa“: charakteristikos, savaitgalio tvarkaraštis ir orai, ankstesnių metų
podiumai ir vairuotojų rezultatai šioje trasoje. Tik skaitymas iš `Dataset` – modelio neliečia."""
import pandas as pd

from .config import DONE_STATUSES

PROFILE = ("greitis", "prispaudimas", "padangos", "lenkimo_sunkumas", "gatve")


class TrackInfo:
    def __init__(self, data, tracks_table):
        self.data = data
        self.tracks = tracks_table.set_index("trasa")

    def profile(self, circuit):
        """{charakteristika: reikšmė 1–5 (gatvė – 0/1)}; tuščias, jei trasos žinyne nėra."""
        if circuit not in self.tracks.index:
            return {}
        r = self.tracks.loc[circuit]
        return {k: float(r[k]) for k in PROFILE if k in r and pd.notna(r[k])}

    def weekend(self, season, rnd):
        """Visos savaitgalio sesijos: laikas, būsena, orai ir (įvykusioms) TOP3."""
        s = self.data.session_rows(season, rnd).sort_values("date_utc")
        top3 = [" – ".join(self.data.top3(season, rnd, c)) if st in DONE_STATUSES else ""
                for c, st in zip(s.session, s.status)]
        return s.assign(top3=top3)[["session", "date_utc", "status", "rain_prob", "track_rain_frac", "temp_c",
                                    "weather_source", "top3"]]

    def _at(self, circuit, session, before_season):
        r = self.data.res
        return r[(r.circuit == circuit) & (r.session == session) & (r.season < before_season) & r.position.notna()]

    def podiums(self, circuit, before_season):
        """Ankstesnių metų lenktynių podiumai ir pole pozicija: [metai, P1, P2, P3, pole]."""
        rows = []
        race, quali = self._at(circuit, "R", before_season), self._at(circuit, "Q", before_season)
        for season in sorted(set(race.season) | set(quali.season), reverse=True):
            top = race[race.season == season].sort_values("position").driver.head(3).tolist()
            pole = quali[quali.season == season].sort_values("position").driver.head(1).tolist()
            rows.append(dict(season=int(season), P1=(top + ["", "", ""])[0], P2=(top + ["", "", ""])[1],
                             P3=(top + ["", "", ""])[2], pole=(pole or [""])[0]))
        return pd.DataFrame(rows)

    def drivers(self, circuit, before_season, drivers):
        """Šio savaitgalio vairuotojų rezultatai šioje trasoje anksčiau (lenktynės ir kvalifikacija)."""
        race, quali = self._at(circuit, "R", before_season), self._at(circuit, "Q", before_season)
        g = race.groupby("driver").position
        out = pd.DataFrame({"starts": g.size(), "avg": g.mean().round(1), "best": g.min(),
                            "podiums": g.apply(lambda p: int((p <= 3).sum())),
                            "wins": g.apply(lambda p: int((p == 1).sum())),
                            "avg_quali": quali.groupby("driver").position.mean().round(1)})
        out = out.reindex([d for d in drivers if d in out.index])
        return out.sort_values(["avg"]).astype({"starts": "Int64", "best": "Int64", "podiums": "Int64", "wins": "Int64"})
