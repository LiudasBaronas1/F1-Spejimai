# F1 spėjimų modelis – programuotojui

## Naudojimas

Paleidimas: `F1 Spėjimai.vbs` pagrindiniame aplanke (pirmą kartą paleidžia `idiegti.bat`) arba darbalaukio
nuoroda „F1 Spejimai“. Išjungti: šoninėje juostoje **„Išjungti programą“**. Prieš spėdami paspauskite
**„Atnaujinti duomenis“**.

- **Automatinis spėjimas prieš kiekvieną sesiją:** `automatinis_ijungti.bat` / `automatinis_isjungti.bat`.
- **Testai:** `testai.bat` (naudoja laikiną testinę duomenų bazę ir talpyklą – tikri duomenys nepaliečiami).
- **Komandinė eilutė:** `.venv\Scripts\python cli.py spejimas | testas | atnaujinti [metai] | automatinis`.

## Duomenys

- `../duomenys/` – vartotojo duomenys (DB `f1.db`, F1 talpykla, orų kalibracija). Į GitHub nekeliama.
- `pradiniai_duomenys/` – pradinė DB ir orų kalibracija; nukopijuojamos į `duomenys/`, jei jų dar nėra
  (`app.install_starter_data`). Atnaujinti: nukopijuoti savo `f1.db` ir išvalyti asmenines lenteles
  (`predictions`, `nustatymai`, `model_params`, `zaidejai`, `vertimai`, `kalbos`).
- **Excel lentelė** (`duomenys/Rezultatai_ Bendri.xlsx`) – neprivaloma, asmeninė. Jei jos nėra, nerodomi
  žaidėjų žinynai ir palyginimas su žaidėjais.

## Architektūra

```
programa/
├── ui.py                  sąsajos įėjimas: App + vertėjas + Controller (foniniai darbai) -> views
├── views/                 PUSLAPIAI (po modulį): next_session, weekend, season, news, model_info,
│   ├── __init__.py        data_status; Ctx – siaura sąsaja, per kurią puslapiai pasiekia programą
│   └── common.py          bendros dalys: spėjimo blokas, duomenų patikra, laiko formatai
├── ui_progress.py         eigos skydelis: Job (foninis srautas), UpdateTracker, TrainTracker
├── ui_style.py, ui.css    vaizdo komponentai (HTML) ir stilius (CSS) – be tekstų ir be duomenų bazės
├── cli.py                 komandinė eilutė / automatinis režimas
├── tests/                 automatiniai testai (unittest)
└── f1model/
    ├── app.py             KOMPOZICIJOS ŠAKNIS – vienintelė vieta, kur kuriamos priklausomybės
    ├── config.py          konstantos ir numatytieji keliai (be šalutinių poveikių importuojant)
    ├── db.py              Database klasė (schema, migracijos, rodiniai, duomenų versija)
    ├── reference.py       žinynai (trasos, komandos, žaidėjai...) – DB lentelės + pradinės reikšmės
    ├── i18n.py            vertimai: TranslationRepository (DB) + Translator
    ├── translations.py    pradiniai sąsajos tekstai (lt, en)
    ├── preferences.py     programos pasirinkimai (kalba, šaltinių trukmės)
    ├── settings.py        Settings + parametrai.json
    ├── dataset.py         duomenys modeliui (+ nustatymai ir žinynai)
    ├── features.py        POŽYMIŲ REGISTRAS (@feature)
    ├── model.py           Plackett-Luce modelis
    ├── sources/           DUOMENŲ ŠALTINIAI (DataSource): official, weather, odds, track_maps,
    │                      fia (atnaujinimai, starto rikiuotė, klasifikacija), news (RSS)
    ├── status.py          ar spėjimui reikalingi duomenys surinkti (kontrolinis sąrašas, sezono matrica)
    ├── briefing.py        atnaujinimai, naujienos, etapo faktai
    ├── track_info.py      tvarkaraštis su orais, podiumai, vairuotojai trasoje
    └── automation.py, backtest.py, report.py, excel.py
```

**Priklausomybių injekcija.** Globalios būsenos ir šalutinių poveikių importuojant nėra:
- `App.create(...)` sukuria `Database`, `Settings`, žinynus ir paruošia aplankus bei FastF1 talpyklą
  (`cache_dir`); orų kalibravimo failas (`calibration_path`) perduodamas `WeatherSource` ir `App.write_report`.
- `sources.registry(db, ref, cache_dir, calibration_path)` sukuria šaltinius ir perduoda jiems priklausomybes;
  trims FIA šaltiniams – viena bendra `FiaDocuments` rodyklė.
- Sąsajoje `Controller` gauna `App`, vertėją ir bendrą būseną konstruktoriuje; puslapiai gauna tik `Ctx`
  (duomenys, modelis, vertėjas ir kelios operacijos) – į duomenų bazę tiesiogiai nesikreipia.
- Testai: `App.create(db_path=..., params_path=..., starter_dir=None, cache_dir=...)` – viskas laikiname aplanke.

**Atviras plėtrai, uždaras keitimui.** Naujas požymis, šaltinis ar puslapis pridedamas nauju moduliu/funkcija
ir vienu įrašu registre – esamo kodo keisti nereikia. Šaltinis pats nurodo, kiek apytiksliai užtrunka
(`DataSource.expected_s`), o eigos skydelis vėliau naudoja tikras išmatuotas trukmes.

**Žinynai duomenų bazėje** (redaguojami meniu „Duomenys“ → „Žinynai“): `trasos`, `trasu_sinonimai`,
`komandos`, `zaidejai`, `gp_pavadinimai`, `vairuotoju_vardai`, `naujienu_saltiniai`, `naujienu_zymes`,
`vertimai`, `kalbos`. Komandos tapatybė (`Reference.team_key`): raktažodžiai su ta pačia spalva = ta pati komanda.

**Sesijos būsena:** `ok` – oficialūs F1 duomenys; `fia` – preliminarus rezultatas iš FIA klasifikacijos (kol F1
archyvas vėluoja; vėliau perrašomas); `pending` – duomenų nėra. Visur naudokite `config.DONE_STATUSES`.

## Kaip plėsti

- **Naujas požymis** – funkcija `features.py` su `@feature(...)`; ji gauna `ctx` (sesijos kontekstą su
  `ctx.S` nustatymais ir `ctx.tracks` trasų žinynu) ir grąžina reikšmę kiekvienam vairuotojui.
  Anglišką pavadinimą ir aprašymą įrašykite į `translations.FEATURES_EN`.
- **Naujas duomenų šaltinis** – `DataSource` poklasis (`sources/`) su `label`, `expected_s` ir `update(season)`;
  cikluose kviečia `self.progress(i, n, detalė)`. Įrašas `sources.registry()`, pavadinimas ir aprašymas –
  vertimai `source.<Klasė>` ir `source.<Klasė>.desc`. Lažybų šaltiniui – `OddsSource` poklasis.
- **Naujas puslapis** – modulis `views/` su `render(c)`, įrašas `views.pages()` ir vertimas `nav.<raktas>`.
- **Naujas žinynas** – lentelė `db.SCHEMA` + pradinės reikšmės `reference.DEFAULTS` + laukas `Reference`.
- **Naujas sąsajos tekstas** – NAUJAS raktas `translations.UI` ir `t("raktas")` (esami raktai DB neperrašomi).
  **Nauja kalba** – eilutė žinyne „Kalbos“ ir vertimai žinyne „Vertimai“.
- Po pakeitimų paleiskite `testai.bat` ir sezono testą (`cli.py testas`) – modelio taškai neturi blogėti.
