# F1 spėjimų modelis – programuotojui

## Naudojimas

Paleidimas: `F1 Spėjimai.vbs` pagrindiniame aplanke (pirmą kartą paleidžia `idiegti.bat`) arba darbalaukio
nuoroda „F1 Spejimai“. Išjungti: šoninėje juostoje **„Išjungti programą“**. Prieš spėdami paspauskite
**„Atnaujinti duomenis“**.

- **Automatinis spėjimas prieš kiekvieną sesiją:** `automatinis_ijungti.bat` / `automatinis_isjungti.bat`.
- **Testai:** `testai.bat` (naudoja laikiną testinę duomenų bazę – tikri duomenys nepaliečiami).
- **Komandinė eilutė:** `.venv\Scripts\python cli.py spejimas | testas | atnaujinti [metai] | automatinis`.

## Duomenys

- `../duomenys/` – vartotojo duomenys (DB `f1.db`, F1 talpykla, orų kalibracija). Į GitHub nekeliama.
- `pradiniai_duomenys/` – pradinė DB ir orų kalibracija; nukopijuojamos į `duomenys/`, jei jų dar nėra
  (`app.install_starter_data`). Atnaujinti: nukopijuoti savo `f1.db` ir išvalyti asmenines lenteles
  (`zaideju_spejimai`, `predictions`, `nustatymai`, `model_params`, `zaidejai`, `vertimai`, `kalbos`).
- **Excel lentelė** (`duomenys/Rezultatai_ Bendri.xlsx`) – neprivaloma, asmeninė. Jei jos nėra, sąsajoje
  nerodomi žaidėjų žinynai, palyginimas su žaidėjais ir susijusios SQL lentelės (`ui.EXCEL_ONLY`).

## Architektūra

```
programa/
├── ui.py, ui_style.py     sąsaja ir jos išvaizda (ui_style be tekstų – juos perduoda ui.py)
├── cli.py                 komandinė eilutė / automatinis režimas
├── tests/                 automatiniai testai (unittest)
└── f1model/
    ├── app.py             KOMPOZICIJOS ŠAKNIS – vienintelė vieta, kur kuriamos priklausomybės
    ├── db.py              Database klasė (schema, migracijos, rodiniai, duomenų versija, tik skaitymo SQL)
    ├── reference.py       žinynai (trasos, komandos, žaidėjai...) – DB lentelės + pradinės reikšmės
    ├── i18n.py            vertimai: TranslationRepository (DB) + Translator
    ├── translations.py    pradiniai sąsajos tekstai (lt, en)
    ├── preferences.py     programos pasirinkimai (pvz. kalba)
    ├── settings.py        Settings + parametrai.json
    ├── dataset.py         duomenys modeliui (+ nustatymai ir žinynai)
    ├── features.py        POŽYMIŲ REGISTRAS (@feature)
    ├── model.py           Plackett-Luce modelis
    ├── sources/           DUOMENŲ ŠALTINIAI (DataSource): official, weather, odds, track_maps
    ├── automation.py, backtest.py, report.py, excel.py, config.py
```

**Priklausomybių injekcija.** Moduliai neturi globalios būsenos: `Database`, `Settings` ir žinynai
perduodami per `App` → `Dataset` / šaltinių konstruktorius / funkcijų parametrus. Todėl visą modelį galima
paleisti su kita (testine) duomenų baze: `App.create(db_path=..., params_path=..., starter_dir=None)`.

**Žinynai duomenų bazėje** (redaguojami programos skirtuke „Duomenys“): `trasos`, `trasu_sinonimai`,
`komandos`, `zaidejai`, `gp_pavadinimai`, `vairuotoju_vardai`, `vertimai`, `kalbos`.

## Kaip plėsti

- **Naujas požymis** – funkcija `features.py` su `@feature(...)`; ji gauna `ctx` (sesijos kontekstą su
  `ctx.S` nustatymais ir `ctx.tracks` trasų žinynu) ir grąžina reikšmę kiekvienam vairuotojui.
  Anglišką pavadinimą ir aprašymą įrašykite į `translations.FEATURES_EN`.
- **Naujas duomenų šaltinis** – `DataSource` poklasis (`sources/`), gaunantis `db` ir `ref` konstruktoriuje,
  ir įrašas `sources.registry()`. Lažybų šaltiniui – `OddsSource` poklasis.
- **Naujas žinynas** – lentelė `db.SCHEMA` + pradinės reikšmės `reference.DEFAULTS` + laukas `Reference`.
- **Naujas sąsajos tekstas** – raktas `translations.UI` ir `t("raktas")` sąsajoje.
  **Nauja kalba** – eilutė žinyne „Kalbos“ ir vertimai žinyne „Vertimai“.
- Po pakeitimų paleiskite `testai.bat`.
