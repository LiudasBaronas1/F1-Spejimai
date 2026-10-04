"""Pradiniai sąsajos tekstai (įrašomi į DB lenteles `kalbos` ir `vertimai`, žr. i18n.py).

Lietuviški požymių pavadinimai ir aprašymai imami iš features.py (@feature), sesijų – iš config.py,
lentelių aprašymai – iš db.TABLE_INFO, todėl čia jų nekartojame. Naujas tekstas = naujas raktas su
vertimu kiekviena kalba; jei kurios nors kalbos trūksta, rodoma lietuviškai.
"""
from . import features
from .config import SESSION_NAMES_LT
from .db import TABLE_INFO

LANGUAGES = {"lt": "Lietuvių", "en": "English"}

UI = {
    # --- bendra
    "app.title": ("F1 spėjimai", "F1 Predictions"),
    "brand.accent": ("Spėjimai", "Predictions"),
    "brand.subtitle": ("Totalizatoriaus modelis · {season} sezonas", "Prediction game model · {season} season"),
    "spinner.training": ("Mokau modelį...", "Training the model..."),
    "spinner.training_before": ("Mokau modelį tik su duomenimis iki pasirinktos sesijos...",
                                "Training the model on data up to the selected session only..."),
    # --- šoninė juosta
    "sidebar.controls": ("Valdymas", "Controls"),
    "sidebar.language": ("Kalba", "Language"),
    "sidebar.update": ("Atnaujinti duomenis", "Update data"),
    "sidebar.update_help": ("Rezultatai, treniruotės, orai, lažybų rinkos ir trasų žemėlapiai",
                            "Results, practice, weather, betting markets and track maps"),
    "sidebar.updating": ("Renku naujausius duomenis...", "Fetching the latest data..."),
    "sidebar.multipliers_hint": ("Požymių daugikliai – skirtuke „Požymiai“.",
                                 "Feature multipliers are in the Features tab."),
    "sidebar.quit": ("Išjungti programą", "Quit the app"),
    "sidebar.quit_done": ("Programa išjungta – galite uždaryti langą.", "The app has stopped. You can close the window."),
    # --- skirtukai
    "tab.predict": ("Spėjimas", "Prediction"),
    "tab.features": ("Požymiai", "Features"),
    "tab.backtest": ("Sezono testas", "Season backtest"),
    "tab.sql": ("SQL", "SQL"),
    "tab.params": ("Parametrai", "Parameters"),
    "tab.data": ("Duomenys", "Data"),
    # --- spėjimas
    "predict.season": ("Metai", "Season"),
    "predict.gp": ("Grand Prix", "Grand Prix"),
    "predict.session": ("Sesija", "Session"),
    "predict.run": ("Spėti", "Predict"),
    "predict.no_data_title": ("Nėra duomenų", "No data"),
    "predict.no_data": ("Šiam etapui sesijų dar nėra.", "There are no sessions for this round yet."),
    "predict.status_done": ("įvyko", "completed"),
    "predict.status_upcoming": ("artėja", "upcoming"),
    "predict.done_title": ("Sesija įvyko", "Session completed"),
    "predict.done_text": ("Modelis spėjo tik su duomenimis, žinotais prieš ją. Tikras rezultatas: {actual}. "
                          "Spėjimas būtų pelnęs {points} tšk.",
                          "The model used only data known before the session. Actual result: {actual}. "
                          "The prediction would have scored {points} pts."),
    "predict.pick": ("Siūlomas spėjimas", "Suggested pick"),
    "predict.save": ("Išsaugoti spėjimą", "Save prediction"),
    "predict.save_help": ("Įrašo spėjimą į duomenų bazę ir atnaujina PARAMETRAI.md",
                          "Stores the prediction in the database and updates PARAMETRAI.md"),
    "predict.saved": ("Spėjimas išsaugotas.", "Prediction saved."),
    "pick.exact": ("tiksliai", "exact"),
    "pick.top3": ("TOP3", "TOP3"),
    "tile.expected": ("Tikėtini taškai", "Expected points"),
    "tile.expected_sub": ("iš 6 galimų", "out of 6"),
    "tile.rain": ("Lietaus tikimybė", "Chance of rain"),
    "tile.temp": ("Temperatūra", "Temperature"),
    "tile.temp_sub": ("oro, sesijos metu", "air, during the session"),
    "rain.track": ("trasoje lijo {frac} laiko", "rain on track {frac} of the time"),
    "rain.forecast": ("prognozė: {mm} mm trasoje, {region} mm regione",
                      "forecast: {mm} mm at the track, {region} mm in the region"),
    "rain.none": ("nėra duomenų", "no data"),
    "rain.note_title": ("Lietus", "Rain"),
    "rain.note": ("Lyjant rezultatas mažiau nuspėjamas. Prieš pat sesiją atnaujinkite duomenis – orų prognozė "
                  "ir lažybų kainos keičiasi.",
                  "Rain makes the result less predictable. Update the data right before the session, because "
                  "the forecast and betting prices change."),
    "track.tyres": ("Padangų apkrova", "Tyre stress"),
    "track.overtaking": ("Lenkimo sunkumas", "Overtaking difficulty"),
    "track.similar": ("Panašiausios trasos", "Most similar tracks"),
    "track.format": ("Formatas", "Format"),
    "track.sprint": ("sprinto savaitgalis", "sprint weekend"),
    "track.conventional": ("įprastas", "standard"),
    "track.no_map": ("Žemėlapis dar neparsiųstas", "Map not downloaded yet"),
    "section.probabilities": ("Tikimybės", "Probabilities"),
    "section.probabilities_sub": ("Tikimybė užimti kiekvieną vietą (modelio simuliacija)",
                                  "Chance of finishing in each position (model simulation)"),
    "section.why": ("Kodėl?", "Why?"),
    "section.why_sub": ("Kiek kiekvienas požymis prideda prie vairuotojo stiprumo (svoris × reikšmė)",
                        "How much each feature adds to a driver's strength (weight × value)"),
    "why.value": ("Indėlis į stiprumą", "Contribution to strength"),
    "col.driver":("Vairuotojas", "Driver"),
    "col.team": ("Komanda", "Team"),
    # --- požymiai
    "features.intro": ("Kiekvienas požymis, jo **išmoktas svoris** ir **daugiklis** (1 = kaip išmokta, "
                       "0 = neatsižvelgti, 2 = dvigubai daugiau). Spėjimas persiskaičiuoja iškart.",
                       "Each feature with its **learned weight** and **multiplier** (1 = as learned, "
                       "0 = ignore, 2 = double). The prediction updates immediately."),
    "features.save": ("Išsaugoti", "Save"),
    "features.save_help": ("Įrašyti daugiklius į parametrai.json", "Write the multipliers to parametrai.json"),
    "features.saved": ("Išsaugota – bus naudojama ir kitą kartą.", "Saved. It will be used next time too."),
    "features.reset": ("Visi į 1", "Reset all to 1"),
    "features.reset_help": ("Grąžinti visus daugiklius į 1", "Set every multiplier back to 1"),
    "features.col.feature": ("Požymis", "Feature"),
    "features.col.meaning": ("Ką reiškia", "What it means"),
    "features.col.quali": ("Kvalifikacija", "Qualifying"),
    "features.col.race": ("Lenktynės", "Race"),
    "features.col.multiplier": ("Daugiklis", "Multiplier"),
    "features.share": ("svarba {share}", "share {share}"),
    "features.values": ("Reikšmės: {event} – {session}", "Values: {event} – {session}"),
    "features.values_sub": ("0 = vidutinis vairuotojas, teigiama = geriau", "0 = average driver, positive = better"),
    # --- sezono testas
    "backtest.intro": ("Atkuria šį sezoną: kiekvienai įvykusiai sesijai modelis spėja tik su iki jos žinomais "
                       "duomenimis, o spėjimas įvertinamas pagal tikrą rezultatą.",
                       "Replays this season: for every completed session the model predicts using only data known "
                       "before it, and the prediction is scored against the actual result."),
    "backtest.intro_players": ("Taip pat palyginama su žaidėjų spėjimais iš Excel.",
                               "It is also compared with the players' picks from Excel."),
    "backtest.run": ("Paleisti testą", "Run backtest"),
    "backtest.run_help": ("Užtrunka 1–2 min.", "Takes 1–2 min."),
    "backtest.total": ("Taškai iš viso", "Total points"),
    "backtest.sessions": ("Kiekviena sesija", "Every session"),
    "backtest.by_type": ("Pagal sesijos tipą", "By session type"),
    # --- SQL
    "sql.tables": ("Lentelės ir rodiniai", "Tables and views"),
    "sql.tables_sub": ("Rodiniai (v_...) – patogios lentelės su lietuviškais stulpeliais.",
                       "Views (v_...) are convenient tables with Lithuanian column names."),
    "sql.examples": ("Pavyzdinės užklausos", "Example queries"),
    "sql.pick_example": ("— pasirinkite pavyzdį —", "— choose an example —"),
    "sql.query": ("SQL užklausa", "SQL query"),
    "sql.readonly": ("Užklausos vykdomos tik skaitymo režimu – duomenų pakeisti ar ištrinti neįmanoma.",
                     "Queries run in read-only mode, so data cannot be changed or deleted."),
    "sql.run": ("Vykdyti", "Run"),
    "sql.error": ("Klaida: {error}", "Error: {error}"),
    "sql.rows": ("{n} eilučių", "{n} rows"),
    "sql.truncated": (" (rodomos tik pirmos 10 000)", " (only the first 10,000 are shown)"),
    "sql.download": ("Atsisiųsti CSV", "Download CSV"),
    "sql.example.round_results": ("Etapo rezultatai (pvz. 2026 m. 15 etapo lenktynės)",
                                  "Round results (e.g. 2026 round 15 race)"),
    "sql.example.driver_summary": ("Vairuotojų sezono suvestinė", "Driver season summary"),
    "sql.example.driver_results": ("Vieno vairuotojo visi rezultatai (pvz. NOR)", "All results of one driver (e.g. NOR)"),
    "sql.example.wet_winners": ("Sesijos, kai trasoje lijo, ir jų nugalėtojai", "Wet sessions and their winners"),
    "sql.example.weather": ("Orai: prognozė ir faktas šiam sezonui", "Weather: forecast vs actual this season"),
    "sql.example.best_at_track": ("Kas geriausias konkrečioje trasoje (pvz. Marina Bay)",
                                  "Who is best at a given track (e.g. Marina Bay)"),
    "sql.example.odds": ("Lažybų koeficientai paskutiniam etapui", "Betting odds for the latest round"),
    "sql.example.tracks": ("Trasų žinynas", "Track reference"),
    "sql.example.players": ("Draugų spėjimai vs rezultatas", "Friends' picks vs result"),
    "sql.example.model": ("Modelio spėjimai vs tikrovė", "Model predictions vs reality"),
    # --- parametrai
    "params.refresh": ("Atnaujinti PARAMETRAI.md", "Regenerate PARAMETRAI.md"),
    "params.language_note": ("", "This report is generated in Lithuanian."),
    # --- duomenys
    "data.reference": ("Žinynai", "Reference data"),
    "data.reference_sub": ("Trasų charakteristikos, komandų spalvos, vertimai ir kt. Pakeitimai įrašomi "
                           "į duomenų bazę, modelis persimoko automatiškai.",
                           "Track characteristics, team colours, translations and more. Changes are saved "
                           "to the database and the model retrains automatically."),
    "data.table": ("Žinynas", "Table"),
    "data.save": ("Išsaugoti žinyną", "Save table"),
    "data.defaults": ("Pradinės reikšmės", "Restore defaults"),
    "data.defaults_help": ("Grąžinti šio žinyno pradines reikšmes", "Restore this table's default values"),
    "data.collected": ("Surinkti duomenys", "Collected data"),
    "data.collected_sub": ("Įvykusių sesijų skaičius pagal sezoną", "Completed sessions per season"),
    "reftable.trasos": ("Trasos", "Tracks"),
    "reftable.trasu_sinonimai": ("Trasų sinonimai", "Track aliases"),
    "reftable.komandos": ("Komandų spalvos", "Team colours"),
    "reftable.zaidejai": ("Žaidėjai", "Players"),
    "reftable.gp_pavadinimai": ("GP pavadinimai (Excel)", "GP names (Excel)"),
    "reftable.vairuotoju_vardai": ("Vairuotojų vardai (lažybos)", "Driver names (betting)"),
    "reftable.vertimai": ("Vertimai", "Translations"),
    "reftable.kalbos": ("Kalbos", "Languages"),
}
UI.update({f"weekday.{i}": pair for i, pair in enumerate(zip(
    ["pirmadienis", "antradienis", "trečiadienis", "ketvirtadienis", "penktadienis", "šeštadienis", "sekmadienis"],
    ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]))})

SESSIONS_EN = {"FP1": "Practice 1", "FP2": "Practice 2", "FP3": "Practice 3", "SQ": "Sprint Qualifying",
               "S": "Sprint", "Q": "Qualifying", "R": "Race"}

FEATURES_EN = {
    "form": ("Season form", "Average position in this season's sessions of the same type (qualifying or race); "
             "recent sessions count more (half-life: forma_pusejimo_sesijos)."),
    "prev_season": ("Previous season", "The driver's average position last season in sessions of the same type."),
    "track": ("History at this track", "How much better or worse than usual the driver did at this track in "
              "previous years (position compared with that season's average; older years count less)."),
    "similar": ("Similar tracks", "The same, but at similar tracks (by the characteristics in the 'trasos' "
                "table), including this season."),
    "pace": ("Practice pace", "This weekend's practice: one-lap speed for qualifying (kvalifikacijos_tempo_matai), "
             "long-run pace for the race (gap % to the fastest). Sessions whose conditions (dry/wet) do not "
             "match the expected ones count less."),
    "weekend": ("Weekend results", "Race/sprint: grid position; qualifying: results of earlier sessions this "
                "weekend (e.g. sprint qualifying)."),
    "wet": ("Rain × wet skill", "How much better or worse than usual the driver did in past sessions when it "
            "rained on track (track sensors, 2023+), multiplied by the chance of rain for this session "
            "(calibrated forecast). Zero when dry."),
    "heat": ("Temperature × driver sensitivity", "Whether the driver historically does better in heat or in cool "
             "conditions, multiplied by how much hotter or cooler than usual the forecast is."),
    "tyre_deg": ("Strategy: tyre wear", "Race/sprint only. How much the lap time gets worse per lap in this "
                 "weekend's practice long runs (less = better), multiplied by the track's tyre stress."),
    "overtake": ("Strategy: overtaking difficulty", "Race/sprint only. Grid position × how hard it is to overtake: "
                 "where passing is hard (Monaco, Singapore) the grid matters more; where it is easy (Spa, Baku) "
                 "it matters less."),
    "market": ("Betting market: winner", "Market chance of winning the session (pole for qualifying, win for the "
               "race): weighted average of Kalshi and Polymarket (bookmakers as a fallback), last price before "
               "the session, log scale."),
    "market_top3": ("Betting market: podium", "Market chance of a TOP3 finish (races), logit scale. Important for "
                    "our scoring system."),
    "market_top5": ("Betting market: TOP5", "Kalshi market chance of a TOP5 finish (races and sprints), logit "
                    "scale. Helps tell who is really fighting for P3."),
}

TABLE_INFO_EN = {
    "events": "Rounds (Grand Prix): season, round, name, country, track, date, format",
    "sessions": "Sessions: FP1–3, SQ, S, Q, R; start time in UTC, whether data was collected",
    "results": "Results: position (on-track finish), official position, grid, status, points",
    "practice": "Practice: best lap, long-run pace, tyre wear",
    "weather": "Weather: sensor facts, forecast features, final chance of rain",
    "odds": "Betting prices before the session: win / pole / podium / top5; polymarket / kalshi / bookmakers",
    "predictions": "All saved model predictions with probabilities",
    "model_params": "Most recently learned model weights",
    "zaideju_spejimai": "Your and your friends' picks from the Excel sheet",
    "trasos": "Reference: track characteristics (1–5), overtaking difficulty, coordinates",
    "trasu_sinonimai": "Reference: FastF1 location name -> track",
    "komandos": "Reference: team colours (by keyword in the team name)",
    "zaidejai": "Reference: prediction game players (Excel sheet names)",
    "gp_pavadinimai": "Reference: Excel GP name -> part of the FastF1 name",
    "vairuotoju_vardai": "Reference: names in betting markets -> driver code",
    "trasu_konturai": "Track maps: outline and corners (from the fastest qualifying lap)",
    "kalbos": "Interface languages (code -> name)",
    "vertimai": "Interface texts in every language (key, language, text)",
    "nustatymai": "App preferences, e.g. interface language",
    "v_rezultatai": "View: results with GP name, date and weather",
    "v_orai": "View: weather forecast and sensor facts",
    "v_treniruotes": "View: practice pace with GP name",
    "v_vairuotojai": "View: driver season summary",
    "v_koeficientai": "View: betting probabilities and odds next to the result",
    "v_modelio_spejimai": "View: model predictions compared with the actual result",
}


def texts():
    """{raktas: {kalba: tekstas}} – viskas, kas įrašoma į lentelę `vertimai`."""
    out = {k: {lang: t for lang, t in (("lt", lt), ("en", en)) if t} for k, (lt, en) in UI.items()}
    out.update({f"session.{c}": {"lt": lt, "en": SESSIONS_EN[c]} for c, lt in SESSION_NAMES_LT.items()})
    for f in features.REGISTRY.values():
        en_label, en_desc = FEATURES_EN.get(f.name, (None, None))
        out[f"feature.{f.name}.label"] = {"lt": f.label, **({"en": en_label} if en_label else {})}
        out[f"feature.{f.name}.desc"] = {"lt": f.description, **({"en": en_desc} if en_desc else {})}
    for name, lt in TABLE_INFO.items():
        out[f"tableinfo.{name}"] = {"lt": lt, **({"en": TABLE_INFO_EN[name]} if name in TABLE_INFO_EN else {})}
    return out


def default_rows():
    """Pradinės lentelių `kalbos` ir `vertimai` eilutės (mygtukui „Pradinės reikšmės“)."""
    return {"kalbos": [dict(kodas=k, pavadinimas=n) for k, n in LANGUAGES.items()],
            "vertimai": [dict(raktas=k, kalba=lang, tekstas=t) for k, by in texts().items() for lang, t in by.items()]}
