import unittest

from f1model import features, model, translations
from f1model.i18n import TranslationRepository, Translator
from tests.helpers import temp_app


class TranslationTest(unittest.TestCase):
    def setUp(self):
        self.app, _ = temp_app()

    def test_languages_and_texts_seeded(self):
        self.assertEqual(list(self.app.translations().languages()), ["lt", "en"])   # numatytoji – pirma
        self.assertEqual(self.app.translator("en")("nav.next"), "Next session")
        self.assertEqual(self.app.translator("lt")("nav.next"), "Artimiausia sesija")

    def test_every_ui_key_has_english(self):
        missing = [k for k, by in translations.texts().items() if "en" not in by and not k.startswith("tableinfo.")]
        self.assertEqual(missing, [])

    def test_feature_labels_come_from_registry(self):
        t = self.app.translator("lt")
        for f in features.REGISTRY.values():
            self.assertEqual(t(f"feature.{f.name}.label"), f.label)

    def test_fallback_and_formatting(self):
        t = Translator("de", {"a": "A {x}"}, fallback={"b": "B"})
        self.assertEqual((t("a", x=1), t("b"), t("c"), t.get("c", "d")), ("A 1", "B", "c", "d"))

    def test_seed_keeps_user_edits_and_adds_new_keys(self):
        db = self.app.db
        db.execute("UPDATE vertimai SET tekstas='Mano' WHERE raktas='nav.next' AND kalba='en'")
        TranslationRepository(db).seed({"en": "English"}, {"nav.next": {"en": "Next session"}, "new.key": {"en": "New"}})
        t = self.app.translator("en")
        self.assertEqual((t("nav.next"), t("new.key")), ("Mano", "New"))

    def test_unknown_or_saved_language(self):
        self.assertEqual(self.app.translator("xx").lang, "lt")
        self.app.preferences().set("kalba", "en")
        self.assertEqual(self.app.translator().lang, "en")


class DataVersionTest(unittest.TestCase):
    def test_only_model_inputs_change_version(self):
        app, _ = temp_app()
        v0 = app.db.data_version()
        app.preferences().set("kalba", "en")
        app.db.write("model_params", [dict(kind="quali", name="form", value=1.0, n_samples=1, fitted_at="x")])
        self.assertEqual(app.db.data_version(), v0)
        app.db.write("komandos", [dict(raktazodis="test", spalva="#000000")])
        self.assertGreater(app.db.data_version(), v0)


if __name__ == "__main__":
    unittest.main()
