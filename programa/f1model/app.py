"""Kompozicijos šaknis: VIENINTELĖ vieta, kur sukuriamos ir sujungiamos priklausomybės
(duomenų bazė, nustatymai, žinynai, vertimai, šaltiniai, failų keliai). Sąsaja, komandinė eilutė ir
automatika naudoja `App`; testai gali sukurti `App` su testine duomenų baze ir kitais keliais.
Importuojant moduliai nieko nekeičia – aplankai ir FastF1 talpykla paruošiami čia, `App.create`."""
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import config, features, model, reference, report, settings, sources, translations
from .briefing import Briefing
from .dataset import Dataset, kind_of
from .db import Database
from .excel import ExcelPicks
from .i18n import DEFAULT_LANGUAGE, TranslationRepository, Translator
from .preferences import Preferences
from .reference import Reference
from .scheduler import AutoUpdatePolicy
from .sources.weather import calibration_summary
from .track_info import TrackInfo

LAST_UPDATE_KEY = "atnaujinta"          # nustatymai: kada paskutinį kartą atnaujinti duomenys (UTC ISO)


def install_starter_data(starter_dir, db_path, calibration_path):
    """Naujas vartotojas: nukopijuoja pradinę duomenų bazę ir orų kalibraciją (jei jų dar nėra),
    kad programa veiktų iškart, nelaukiant kelių sezonų duomenų parsiuntimo."""
    for name, target in (("f1.db", db_path), ("oru_kalibracija.json", calibration_path)):
        if (starter_dir / name).exists() and not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(starter_dir / name, target)


@dataclass
class App:
    db: Database
    settings: settings.Settings
    params_path: Path
    report_path: Path
    excel_path: Path
    cache_dir: Path
    calibration_path: Path

    @classmethod
    def create(cls, db_path=config.DB_PATH, params_path=config.PARAMS_JSON, report_path=config.REPORT_PATH,
               excel_path=config.EXCEL_PATH, starter_dir=config.STARTER_DIR, cache_dir=config.CACHE_DIR,
               calibration_path=None):
        """starter_dir – pradiniai duomenys, nukopijuojami, jei duomenų bazės dar nėra (None – nekopijuoti).
        calibration_path – orų kalibravimas (numatytasis – šalia duomenų bazės)."""
        db_path = Path(db_path)
        calibration_path = Path(calibration_path or db_path.parent / config.CALIBRATION_PATH.name)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        if starter_dir:
            install_starter_data(Path(starter_dir), db_path, calibration_path)
        from .sources.official import enable_cache   # FastF1 – tik kai programa tikrai paleidžiama
        enable_cache(Path(cache_dir))
        db = Database(db_path)
        reference.seed(db)
        TranslationRepository(db).seed(translations.LANGUAGES, translations.texts())
        return cls(db, settings.load(params_path, features.names()), params_path, report_path, excel_path,
                   Path(cache_dir), calibration_path)

    # --- gamyklos (sukuria objektus su reikiamomis priklausomybėmis)
    def reference(self):
        return Reference.load(self.db)

    def dataset(self):
        return Dataset.load(self.db, self.settings, self.reference())

    def sources(self):
        return sources.registry(self.db, self.reference(), self.cache_dir, self.calibration_path)

    def excel(self):
        return ExcelPicks(self.excel_path, self.reference())

    @property
    def has_excel(self):
        """Ar yra asmeninė žaidėjų spėjimų lentelė (be jos su žaidėjais susijusios dalys nerodomos)."""
        return self.excel_path.exists()

    def briefing(self):
        return Briefing(self.db, self.reference())

    @staticmethod
    def track_info(data):
        return TrackInfo(data)

    def track_outline(self, circuit):
        """(kontūro taškai, posūkiai) trasos žemėlapiui arba None (dar neparsiųsta)."""
        r = self.db.query("SELECT taskai, posukiai FROM trasu_konturai WHERE trasa=?", (circuit,))
        return (json.loads(r.taskai.iloc[0]), json.loads(r.posukiai.iloc[0])) if not r.empty else None

    def preferences(self):
        return Preferences(self.db)

    def auto_update_policy(self):
        return AutoUpdatePolicy.load(self.preferences())

    def translations(self):
        return TranslationRepository(self.db)

    def translator(self, lang=None):
        """Vertėjas pasirinkta kalba (be argumento – išsaugota sąsajos kalba)."""
        repo = self.translations()
        lang = lang or self.preferences().get("kalba", DEFAULT_LANGUAGE)
        return Translator.load(repo, lang if lang in repo.languages() else DEFAULT_LANGUAGE)

    def save_reference(self, table, rows):
        """Perrašo žinyną. Pakeitus komandas ar naujienų temas – naujienos pažymimos iš naujo."""
        self.db.write(table, rows, replace_where=("1=1", ()))
        if table in ("komandos", "naujienu_zymes"):
            from .sources.news import NewsSource
            NewsSource(self.db, self.reference()).retag()

    def default_rows(self, table):
        """Žinyno pradinės eilutės (mygtukui „Pradinės reikšmės“)."""
        return {**reference.DEFAULTS, **translations.default_rows()}[table]

    # --- dažni veiksmai
    def update(self, season=config.SEASON, only=None, progress=None):
        """Atnaujina duomenų šaltinius ir pažymi atnaujinimo laiką. Grąžina [(šaltinis, klaida)]."""
        errors = sources.update_all(self.sources(), season, only, progress)
        self.preferences().set(LAST_UPDATE_KEY, datetime.now(timezone.utc).isoformat())
        return errors

    def last_update(self):
        return self.preferences().get(LAST_UPDATE_KEY)

    def train(self, data, progress=None):
        """Išmoko abu modelius ir išsaugo jų parametrus. Grąžina {"quali"/"race": KindModel}."""
        fitted = model.fit_all(data, progress=progress)
        model.save_weights(self.db, fitted)
        return fitted

    def predict(self, data, fitted, season, rnd, session):
        return model.predict(data, season, rnd, session, fitted=fitted[kind_of(session)])

    def publish(self, data, fitted, season, rnd, session, out):
        """Išsaugo spėjimą ir atnaujina PARAMETRAI.md (su šiuo spėjimu)."""
        model.save_prediction(self.db, season, rnd, session, out)
        ev = data.event(season, rnd)
        self.write_report(data, fitted, last=(ev["name"], session, out, ev.circuit))

    def write_report(self, data, fitted, last=None):
        """PARAMETRAI.md; last = (GP, sesija, spėjimas, trasa) – paskutinis spėjimas."""
        report.write(self.report_path, data, fitted, last, calibration_summary(self.calibration_path))

    def save_settings(self):
        settings.save(self.settings, self.params_path, features.names())

    def reload_settings(self):
        self.settings = settings.load(self.params_path, features.names())
