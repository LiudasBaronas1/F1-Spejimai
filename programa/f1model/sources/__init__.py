"""Duomenų šaltiniai. Kiekvienas šaltinis – `DataSource` poklasis; priklausomybės (DB, žinynai)
perduodamos konstruktoriuje, todėl šaltinį galima išbandyti su testine duomenų baze.

NAUJAS ŠALTINIS = nauja klasė + įrašas `registry()`.
"""
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass

import requests

log = logging.getLogger("f1")


class DataSource(ABC):
    label = "šaltinis"
    expected_s = 10.0           # kiek apytiksliai užtrunka (eigos juostos prognozei, kol nėra tikrų matavimų)

    def __init__(self, db, ref):
        self.db, self.ref = db, ref
        self.report = lambda i, n, detail: None   # update_all() pakeičia į eigos juostos atnaujinimą

    @abstractmethod
    def update(self, season: int) -> None:
        """Surenka trūkstamus/naujausius sezono duomenis į DB."""

    def progress(self, i, n, detail=""):
        """Kviečiama cikluose: dabar apdorojamas i-asis (nuo 0) iš n elementų (eigos juostai sąsajoje)."""
        self.report(i, n, detail)


@dataclass
class Progress:
    """Atnaujinimo eigos įvykis sąsajai."""
    index: int                  # kelintas šaltinis (nuo 0)
    total: int                  # kiek šaltinių iš viso
    source: DataSource
    status: str                 # running / done / error
    step: tuple = (0, 0)        # (i, n) – šaltinio viduje
    detail: str = ""
    error: Exception = None

    @property
    def source_frac(self):
        i, n = self.step
        return 1.0 if self.status != "running" else (min(1.0, i / n) if n else 0.0)

    @property
    def frac(self):
        return (self.index + self.source_frac) / self.total if self.total else 1.0


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


def registry(db, ref, cache_dir, calibration_path):
    """Visi šaltiniai, atnaujinimo tvarka (orai – po rezultatų, lažybos – pabaigoje).
    Priklausomybės perduodamos čia: FIA dokumentų rodyklė bendra (fia.com siunčiama vieną kartą)."""
    from .fia import ClassificationSource, FiaDocuments, GridSource, UpgradeSource
    from .news import NewsSource
    from .odds import BookmakerSource, KalshiSource, PolymarketSource
    from .official import OfficialSource
    from .track_maps import TrackMapSource
    from .weather import TrackWeatherSource, WeatherSource
    docs = FiaDocuments()
    return [OfficialSource(db, ref), ClassificationSource(db, ref, docs), TrackMapSource(db, ref, cache_dir),
            TrackWeatherSource(db, ref), WeatherSource(db, ref, calibration_path), UpgradeSource(db, ref, docs),
            GridSource(db, ref, docs), BookmakerSource(db, ref), KalshiSource(db, ref), PolymarketSource(db, ref),
            NewsSource(db, ref)]


def update_all(sources, season, only=None, progress=None):
    """Atnaujina šaltinius; vieno klaida nestabdo kitų. Grąžina [(šaltinis, klaida)].
    progress(Progress) – eigos juostai (nebūtina)."""
    errors = []
    chosen = [s for s in sources if not only or s.label in only]
    emit = progress or (lambda ev: None)
    for k, src in enumerate(chosen):
        src.report = lambda i, n, detail, k=k, src=src: emit(Progress(k, len(chosen), src, "running", (i, n), detail))
        emit(Progress(k, len(chosen), src, "running"))
        try:
            log.info("Atnaujinu: %s", src.label)
            src.update(season)
            emit(Progress(k, len(chosen), src, "done"))
        except Exception as e:  # tinklo/API klaidos – tęsiame su kitais šaltiniais
            log.warning("%s: nepavyko (%s)", src.label, e)
            errors.append((src.label, e))
            emit(Progress(k, len(chosen), src, "error", error=e))
    return errors
