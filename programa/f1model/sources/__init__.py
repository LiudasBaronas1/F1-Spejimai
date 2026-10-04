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

    @abstractmethod
    def update(self, season: int) -> None:
        """Surenka trūkstamus/naujausius sezono duomenis į DB."""


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
    from .odds import BookmakerSource, KalshiSource, PolymarketSource
    from .official import OfficialSource
    from .track_maps import TrackMapSource
    from .weather import TrackWeatherSource, WeatherSource
    return [cls(db, ref) for cls in (OfficialSource, TrackMapSource, TrackWeatherSource, WeatherSource, BookmakerSource,
                                     KalshiSource, PolymarketSource)]


def update_all(sources, season, only=None):
    """Atnaujina šaltinius; vieno klaida nestabdo kitų. Grąžina [(šaltinis, klaida)]."""
    errors = []
    for src in sources:
        if only and src.label not in only:
            continue
        try:
            log.info("Atnaujinu: %s", src.label)
            src.update(season)
        except Exception as e:  # tinklo/API klaidos – tęsiame su kitais šaltiniais
            log.warning("%s: nepavyko (%s)", src.label, e)
            errors.append((src.label, e))
    return errors
