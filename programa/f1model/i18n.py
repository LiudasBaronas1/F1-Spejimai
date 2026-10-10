"""Sąsajos vertimai.

Tekstai laikomi DB lentelėje `vertimai` (raktas, kalba, tekstas), kalbų sąrašas – lentelėje `kalbos`.
Pradinės reikšmės – translations.py; paleidžiant įrašomi tik TRŪKSTAMI raktai, todėl programoje
(meniu „Duomenys“ -> „Žinynai“ -> „Vertimai“) pataisyti tekstai neperrašomi.

NAUJA KALBA: eilutė lentelėje `kalbos` + vertimai lentelėje `vertimai` (arba translations.py).
Neišversti raktai rodomi numatytąja kalba, o jei nėra ir jos – pačiu raktu.
"""

DEFAULT_LANGUAGE = "lt"


class TranslationRepository:
    """Vertimų saugykla DB (tik skaitymas/rašymas, jokios rodymo logikos)."""

    def __init__(self, db):
        self.db = db

    def seed(self, languages, texts):
        """languages – {kodas: pavadinimas}; texts – {raktas: {kalba: tekstas}}. Įrašo tik tai, ko DB dar nėra."""
        have_lang = set(self.languages())
        self.db.write("kalbos", [dict(kodas=k, pavadinimas=n) for k, n in languages.items() if k not in have_lang])
        have = set(map(tuple, self.db.query("SELECT raktas, kalba FROM vertimai").values))
        self.db.write("vertimai", [dict(raktas=key, kalba=lang, tekstas=text)
                                   for key, by_lang in texts.items() for lang, text in by_lang.items()
                                   if (key, lang) not in have])

    def languages(self):
        return dict(self.db.query("SELECT kodas, pavadinimas FROM kalbos ORDER BY kodas = ? DESC, pavadinimas",
                                  (DEFAULT_LANGUAGE,)).values)

    def texts(self, lang):
        return dict(self.db.query("SELECT raktas, tekstas FROM vertimai WHERE kalba = ? AND tekstas IS NOT NULL",
                                  (lang,)).values)


class Translator:
    """Grąžina tekstą pasirinkta kalba: t("raktas", kintamasis=...) arba t.get("raktas", numatytasis)."""

    def __init__(self, lang, texts, fallback=None):
        self.lang, self._texts, self._fallback = lang, texts, fallback or {}

    @classmethod
    def load(cls, repo, lang):
        fallback = repo.texts(DEFAULT_LANGUAGE) if lang != DEFAULT_LANGUAGE else None
        return cls(lang, repo.texts(lang), fallback)

    def get(self, key, default=None):
        text = self._texts.get(key) or self._fallback.get(key)
        return text if text is not None else (default if default is not None else key)

    def __call__(self, key, **values):
        text = self.get(key)
        return text.format(**values) if values else text

    def prefixed(self, prefix, keys):
        """{raktas: tekstas} visiems `prefix.raktas` (pvz. sesijų pavadinimai)."""
        return {k: self.get(f"{prefix}.{k}", str(k)) for k in keys}
