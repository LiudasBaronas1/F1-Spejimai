"""Duomenų šaltiniai. Kiekvienas šaltinis – `DataSource` poklasis; priklausomybės (DB, žinynai)
perduodamos konstruktoriuje, todėl šaltinį galima išbandyti su testine duomenų baze.

NAUJAS ŠALTINIS = nauja klasė + įrašas `registry()`.
"""
import logging
import time
from abc import ABC, abstractmethod

import requests

log = logging.getLogger("f1")


class DataSource(ABC):
    label = "šaltinis"

    def __init__(self, db, ref):
        self.db, self.ref = db, ref
        self.report = lambda frac, detail="": None   # update_all() pakeičia į eigos juostos atnaujinimą

    @abstractmethod
    def update(self, season: int) -> None:
        """Surenka trūkstamus/naujausius sezono duomenis į DB."""

    def progress(self, i, n, detail=""):
        """Kviečiama cikluose: atlikta i iš n (eigos juostai sąsajoje)."""
        self.report(min(1.0, i / n) if n else 1.0, detail)


def get_json(url, params=None, tries=6, **kw):
    """HTTP GET su pakartojimu, kai serveris praneša apie užklausų limitą (429) ar laikiną sutrikimą (5xx)."""
    for i in range(tries):
        r = requests.get(url, params=params, timeout=30, **kw)
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(10 * (i + 1))
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError(f"Užklausų limitas: {url}")


def registry(db, ref):
    """Visi šaltiniai, atnaujinimo tvarka (orai – po rezultatų, lažybos – pabaigoje)."""
    from .fia import GridSource, UpgradeSource
    from .news import NewsSource
    from .odds import BookmakerSource, KalshiSource, PolymarketSource
    from .official import OfficialSource
    from .track_maps import TrackMapSource
    from .weather import TrackWeatherSource, WeatherSource
    return [cls(db, ref) for cls in (OfficialSource, TrackMapSource, TrackWeatherSource, WeatherSource, UpgradeSource,
                                     GridSource, BookmakerSource, KalshiSource, PolymarketSource, NewsSource)]


def update_all(sources, season, only=None, progress=None):
    """Atnaujina šaltinius; vieno klaida nestabdo kitų. Grąžina [(šaltinis, klaida)].
    progress(dalis 0..1, šaltinis, detalė) – eigos juostai (nebūtina)."""
    errors = []
    chosen = [s for s in sources if not only or s.label in only]
    for k, src in enumerate(chosen):
        if progress:
            src.report = lambda frac, detail="", k=k, src=src: progress((k + frac) / len(chosen), src, detail)
            src.report(0.0)
        try:
            log.info("Atnaujinu: %s", src.label)
            src.update(season)
        except Exception as e:  # tinklo/API klaidos – tęsiame su kitais šaltiniais
            log.warning("%s: nepavyko (%s)", src.label, e)
            errors.append((src.label, e))
    if progress and chosen:
        progress(1.0, chosen[-1], "")
    return errors
