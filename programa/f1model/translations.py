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
    # --- šoninė juosta
    "sidebar.language": ("Kalba", "Language"),
    "sidebar.update": ("Atnaujinti duomenis", "Update data"),
    "sidebar.update_info": ("Parsiunčia rezultatus, treniruotes, orus, lažybų rinkas, FIA dokumentus ir naujienas. "
                            "Geriausia – likus 30–60 min. iki sesijos.",
                            "Downloads results, practice, weather, betting markets, FIA documents and news. "
                            "Best done 30–60 min before a session."),
    "sidebar.last_update": ("Paskutinis atnaujinimas", "Last update"),
    "sidebar.never": ("dar nebuvo šioje programoje", "not yet in this app"),
    # --- meniu
    "nav.next": ("Artimiausia sesija", "Next session"),
    "nav.weekend": ("Etapas", "Weekend"),
    "nav.season": ("Sezonas", "Season"),
    "nav.news": ("Naujienos", "News"),
    "nav.model": ("Modelis", "Model"),
    "nav.data": ("Duomenys", "Data"),
    # --- artimiausia sesija
    "next.kicker": ("Artimiausia sesija", "Next session"),
    "next.starts_in": ("Prasidės po", "Starts in"),
    "next.update_hint": ("Atnaujinkite likus 30–60 min. iki sesijos.", "Update 30–60 min before the session."),
    "next.data_title": ("Duomenys šiam spėjimui", "Data for this prediction"),
    "check.results": ("Rezultatai", "Results"),
    "check.practice": ("Treniruotės", "Practice"),
    "check.grid": ("Starto rikiuotė", "Starting grid"),
    "check.weather": ("Orai", "Weather"),
    "check.odds": ("Lažybų rinkos", "Betting markets"),
    "check.news": ("Naujienos", "News"),
    "check.results.na": ("Ankstesnių sesijų šį savaitgalį dar nebuvo.", "No earlier sessions this weekend yet."),
    "check.results.missing": ("Dar nepaskelbta: {sessions}. Atnaujinkite vėliau.",
                              "Not published yet: {sessions}. Update again later."),
    "check.results.prelim": ("{sessions}: preliminarus FIA rezultatas (oficialūs F1 duomenys dar vėluoja).",
                             "{sessions}: preliminary FIA result (official F1 data still delayed)."),
    "check.results.ok": ("Surinkta: {sessions}.", "Collected: {sessions}."),
    "check.practice.na": ("Treniruočių prieš šią sesiją nebuvo.", "No practice before this session."),
    "check.practice.missing": ("Trūksta ratų duomenų: {sessions}.", "Lap data missing: {sessions}."),
    "check.practice.ok": ("Ratų duomenys: {sessions}.", "Lap data: {sessions}."),
    "check.grid.official": ("Oficiali starto rikiuotė.", "Official starting grid."),
    "check.grid.fia": ("FIA starto rikiuotė su baudomis.", "FIA starting grid with penalties."),
    "check.grid.quali": ("FIA rikiuotės dar nėra – imama kvalifikacijos vieta (be baudų).",
                         "No FIA grid yet, using the qualifying order (without penalties)."),
    "check.grid.none": ("Kvalifikacijos rezultato dar nėra.", "No qualifying result yet."),
    "check.weather.sensors": ("Faktas iš trasos jutiklių.", "Actual data from track sensors."),
    "check.weather.forecast": ("Prognozė, gauta prieš {age}.", "Forecast fetched {age} ago."),
    "check.weather.none": ("Prognozės dar nėra (daugiau nei 15 d. iki sesijos).",
                           "No forecast yet (more than 15 days away)."),
    "check.odds.none": ("Rinkų kainų šiai sesijai nėra.", "No market prices for this session."),
    "check.odds.stale": ("Kainos senos ({age}) – atnaujinkite prieš spėdami.",
                         "Prices are old ({age}). Update before you pick."),
    "check.odds.ok": ("{sources}: {markets} rinkos, prieš {age}.", "{sources}: {markets} markets, {age} ago."),
    "check.news.none": ("Naujienų dar nėra.", "No news yet."),
    "check.news.ok": ("Atnaujinta prieš {age}.", "Updated {age} ago."),
    "state.ok": ("gerai", "ok"),
    "state.warn": ("dėmesio", "check"),
    "state.missing": ("trūksta", "missing"),
    "state.na": ("nereikia", "n/a"),
    "state.prelim": ("preliminarus (FIA)", "preliminary (FIA)"),
    "state.official": ("oficialūs duomenys", "official data"),
    "state.missing_data": ("įvyko, bet duomenų nėra", "happened, no data yet"),
    "predict.prelim_title": ("Preliminarus", "Preliminary"),
    "predict.prelim_text": ("Rezultatas paimtas iš FIA klasifikacijos, nes oficialūs F1 duomenys dar nepaskelbti. "
                            "Kai jie atsiras, atnaujinimas jį pakeis.",
                            "The result comes from the FIA classification because official F1 data is not published "
                            "yet. An update will replace it once it is."),
    "pick.why": ("Kodėl", "Why"),
    "section.why_full": ("Išsamus spėjimo paaiškinimas", "Detailed prediction breakdown"),
    # --- etapas
    "weekend.tab_pick": ("Spėjimas", "Prediction"),
    "weekend.tab_track": ("Trasa ir orai", "Track & weather"),
    "weekend.tab_news": ("Atnaujinimai ir naujienos", "Upgrades & news"),
    "upgrades.round_sub": ("Naujos detalės šiam etapui iš FIA dokumentų", "New parts for this round from FIA documents"),
    "news.weekend_title": ("Naujienos apie šį etapą", "News around this weekend"),
    "news.weekend_sub": ("Svarbiausios naujienos savaitgalio laikotarpiu", "Key news around the weekend"),
    # --- sezonas
    "season.tab_calendar": ("Kalendorius", "Calendar"),
    "season.tab_backtest": ("Modelis prieš žaidėjus", "Model vs players"),
    "season.tab_upgrades": ("Atnaujinimų apžvalga", "Upgrades overview"),
    "season.calendar": ("Sezono kalendorius", "Season calendar"),
    "season.calendar_sub": ("Visi etapai, pole pozicija ir lenktynių podiumas", "All rounds, pole position and race podium"),
    "season.done": ("įvyko", "done"),
    "season.next": ("artimiausias", "next"),
    "season.live": ("vyksta", "in progress"),
    "season.std": ("įprastas", "standard"),
    "season.col.round": ("Etapas", "Round"),
    "season.col.date": ("Data", "Date"),
    "season.col.podium": ("Lenktynių podiumas", "Race podium"),
    "track.col.circuit": ("Trasa", "Circuit"),
    # --- modelis
    "model.tab_how": ("Kaip veikia", "How it works"),
    "model.tab_factors": ("Veiksniai ir svoriai", "Factors and weights"),
    "model.tab_params": ("Parametrai", "Parameters"),
    "model.how.1": ("Surenkami faktai apie kiekvieną vairuotoją: forma, starto vieta, treniruočių tempas, lažybų rinka, "
                    "orai, trasos istorija.", "Facts are collected for every driver: form, grid position, practice "
                    "pace, betting market, weather, track history."),
    "model.how.2": ("Kiekvienam faktui suteikiamas svoris, išmoktas iš 2024–2026 m. sesijų: kas praeityje geriausiai "
                    "nuspėjo TOP3.", "Each fact gets a weight learned from 2024–2026 sessions: what best predicted "
                    "the TOP3 in the past."),
    "model.how.3": ("Faktų ir svorių suma – vairuotojo „stiprumas“.", "The weighted sum is the driver's \"strength\"."),
    "model.how.4": ("Sesija 20 000 kartų „perleidžiama“ su atsitiktinumu (lyjant – didesniu); gaunamos P1, P2, P3 "
                    "tikimybės.", "The session is simulated 20,000 times with randomness (more in the rain), "
                    "giving P1, P2 and P3 chances."),
    "model.how.5": ("Parenkamas trejetas, kuris pagal mūsų taisykles vidutiniškai atneša daugiausiai taškų.",
                    "The trio that scores the most points on average under our rules is picked."),
    "model.importance": ("Kas lemia spėjimą", "What drives the prediction"),
    "model.importance_sub": ("Kiekvieno veiksnio dalis (išmokta iš {q} kvalifikacijų ir {r} lenktynių)",
                             "Share of each factor (learned from {q} qualifying and {r} race sessions)"),
    "model.share": ("Dalis sprendime", "Share of the decision"),
    "model.accuracy": ("2025–2026 m. modelis vidutiniškai surenka apie 3 taškus iš 6 per sesiją; reali viršutinė riba – "
                       "apie 3,2–3,4.", "In 2025–2026 the model averages about 3 of 6 points per session; the "
                       "realistic ceiling is about 3.2–3.4."),
    # --- duomenys
    "data.tab_status": ("Duomenų būklė", "Data status"),
    "data.tab_sql": ("SQL", "SQL"),
    "data.tab_reference": ("Žinynai", "Reference tables"),
    "data.status_title": ("Šio sezono duomenys", "This season's data"),
    "data.status_sub": ("Kiekvieno etapo kiekviena sesija", "Every session of every round"),
    "data.status_help": ("Oficialūs F1 duomenys paprastai paskelbiami per 1–2 val. po sesijos, kartais vėliau. Kol jų "
                         "nėra, rezultatas imamas iš FIA klasifikacijos (preliminarus). Raudona – sesija įvyko, bet "
                         "duomenų dar nėra: atnaujinkite vėliau.",
                         "Official F1 data is usually published 1–2 h after a session, sometimes later. Until then "
                         "the result comes from the FIA classification (preliminary). Red means the session "
                         "happened but there is no data yet: update again later."),
    "progress.running_for": ("vyksta · {s}", "running · {s}"),
    "progress.expected": ("laukia · ~{s}", "waiting · ~{s}"),
    "source.ClassificationSource": ("FIA klasifikacija (atsarginė)", "FIA classification (fallback)"),
    "source.ClassificationSource.desc": ("Jei oficialūs F1 rezultatai vėluoja, rezultatas paimamas iš FIA "
                                         "klasifikacijos dokumento (preliminarus).",
                                         "If official F1 results are delayed, the result is taken from the FIA "
                                         "classification document (preliminary)."),
    # --- eigos skydelis
    "progress.update_title": ("Atnaujinami duomenys", "Updating data"),
    "progress.update_sub": ("Šaltinis {k} iš {n}", "Source {k} of {n}"),
    "progress.training_title": ("Mokomas modelis", "Training the model"),
    "progress.training_before_title": ("Mokomas modelis iki pasirinktos sesijos",
                                       "Training the model up to the selected session"),
    "progress.training_sub": ("Modelis {k} iš {n}", "Model {k} of {n}"),
    "progress.elapsed": ("praėjo {t}", "elapsed {t}"),
    "progress.left": ("liko apie {t}", "about {t} left"),
    "progress.now": ("Dabar", "Now"),
    "progress.waiting": ("laukia", "waiting"),
    "progress.done": ("atlikta · {s} s", "done · {s} s"),
    "progress.finished": ("atlikta", "done"),
    "progress.failed": ("klaida · {s} s", "error · {s} s"),
    "progress.starting": ("Jungiamasi prie šaltinio...", "Connecting to the source..."),
    "progress.item": ("{i} iš {n}", "{i} of {n}"),
    "progress.model_quali": ("Kvalifikacijos modelis (Q, SQ)", "Qualifying model (Q, SQ)"),
    "progress.model_race": ("Lenktynių modelis (R, S)", "Race model (R, S)"),
    "progress.training_desc": ("Kiekvienai praeities sesijai apskaičiuojami požymiai (forma, tempas, rinka, orai...), "
                               "tada išmokstami svoriai, kurie geriausiai nuspėja tikrą TOP3.",
                               "Features (form, pace, market, weather...) are computed for every past session, then the "
                               "weights that best predict the actual TOP3 are learned."),
    "progress.fitting": ("Svorių optimizavimas", "Optimising the weights"),
    "progress.session": ("Sesija {d}", "Session {d}"),
    # --- šaltiniai
    "source.OfficialSource": ("Oficialūs F1 rezultatai ir treniruotės", "Official F1 results and practice"),
    "source.OfficialSource.desc": ("Iš oficialaus F1 laiko sekimo (FastF1) parsiunčiami įvykusių sesijų rezultatai, "
                                   "starto vietos ir treniruočių ratai (tempas, ilgos serijos, padangų dėvėjimasis).",
                                   "Results, grid positions and practice laps (pace, long runs, tyre wear) of completed "
                                   "sessions from official F1 live timing (FastF1)."),
    "source.TrackMapSource": ("Trasų žemėlapiai", "Track maps"),
    "source.TrackMapSource.desc": ("Naujoms trasoms nubraižomas kontūras ir posūkiai pagal greičiausią kvalifikacijos ratą.",
                                   "Draws the outline and corners of new tracks from the fastest qualifying lap."),
    "source.TrackWeatherSource": ("Trasos orų jutikliai", "Track weather sensors"),
    "source.TrackWeatherSource.desc": ("Trasos jutiklių duomenys: ar sesijos metu tikrai lijo, oro ir trasos temperatūra.",
                                       "Track sensor data: whether it really rained during the session, air and track "
                                       "temperature."),
    "source.WeatherSource": ("Regiono orų prognozė", "Regional weather forecast"),
    "source.WeatherSource.desc": ("Open-Meteo valandinė prognozė trasai ir 15 km aplink, tada lietaus tikimybė "
                                  "kalibruojama pagal praeities sesijas.",
                                  "Open-Meteo hourly forecast for the track and 15 km around it, then the chance of rain "
                                  "is calibrated against past sessions."),
    "source.UpgradeSource": ("FIA bolidų atnaujinimai", "FIA car upgrades"),
    "source.UpgradeSource.desc": ("FIA „Car Presentation Submissions“ dokumentai: kokias naujas detales atvežė kiekviena "
                                  "komanda.", "FIA \"Car Presentation Submissions\" documents: which new parts each "
                                  "team brought."),
    "source.GridSource": ("FIA starto rikiuotė", "FIA starting grid"),
    "source.GridSource.desc": ("Oficiali artėjančių lenktynių ir sprinto starto rikiuotė su baudomis.",
                               "The official starting grid with penalties for upcoming races and sprints."),
    "source.BookmakerSource": ("Lažybininkų koeficientai", "Bookmaker odds"),
    "source.BookmakerSource.desc": ("bet365, DraftKings ir FanDuel nugalėtojo koeficientai (atsarginis šaltinis).",
                                    "Winner odds from bet365, DraftKings and FanDuel (fallback source)."),
    "source.KalshiSource": ("Kalshi rinka", "Kalshi market"),
    "source.KalshiSource.desc": ("Kalshi biržos kainos: pole, pergalė, podiumas, TOP5. Paskutinė kaina prieš sesiją.",
                                 "Kalshi exchange prices: pole, win, podium, TOP5. Last price before the session."),
    "source.PolymarketSource": ("Polymarket rinka", "Polymarket market"),
    "source.PolymarketSource.desc": ("Polymarket biržos kainos: pole, pergalė, podiumas.",
                                     "Polymarket exchange prices: pole, win, podium."),
    "source.NewsSource": ("Naujienos", "News"),
    "source.NewsSource.desc": ("Naujienų srautai (formula1.com, Autosport, Motorsport.com, RaceFans, BBC), "
                               "pažymimi komandomis ir temomis.",
                               "News feeds (formula1.com, Autosport, Motorsport.com, RaceFans, BBC), tagged with "
                               "teams and topics."),
    "sidebar.quit": ("Išjungti programą", "Quit the app"),
    "sidebar.quit_done": ("Programa išjungta – galite uždaryti langą.", "The app has stopped. You can close the window."),
    # --- skirtukai
    # --- spėjimas
    "predict.season": ("Metai", "Season"),
    "predict.gp": ("Grand Prix", "Grand Prix"),
    "predict.session": ("Sesija", "Session"),
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
    "track.hint": ("Trasos žemėlapis, charakteristikos, tvarkaraštis ir istorija – skyriuje „Trasa“.",
                   "Track map, characteristics, schedule and history are in the \"Track\" section."),
    "track.character": ("Trasos charakteristika", "Track character"),
    "track.character_sub": ("Iš žinyno „trasos“ (1 – mažai, 5 – daug). Naudojama panašioms trasoms ir strategijai.",
                            "From the 'trasos' reference table (1 = low, 5 = high). Used for similar tracks and strategy."),
    "track.speed": ("Greitis", "Speed"),
    "track.speed_d": ("Ilgos tiesiosios ir greiti posūkiai", "Long straights and fast corners"),
    "track.downforce": ("Prispaudimas", "Downforce"),
    "track.downforce_d": ("Kiek svarbūs lėti posūkiai ir sukibimas", "How much slow corners and grip matter"),
    "track.tyres_d": ("Daugiau = daugiau sustojimų ir padangų taupymo", "Higher = more pit stops and tyre saving"),
    "track.overtaking_d": ("Daugiau = starto vieta svarbesnė", "Higher = grid position matters more"),
    "track.street": ("Gatvių trasa", "Street circuit"),
    "track.street_d": ("Sienos arti – daugiau saugos automobilių", "Walls close by, more safety cars"),
    "track.yes": ("taip", "yes"),
    "track.no": ("ne", "no"),
    "track.strategy": ("Strategija", "Strategy"),
    "strategy.tyres_high": ("Didelė padangų apkrova: tikėtini 2 sustojimai, svarbus padangų taupymas ilgose serijose.",
                            "High tyre stress: 2 stops likely, tyre saving on long runs matters."),
    "strategy.tyres_mid": ("Vidutinė padangų apkrova: dažniausiai 1–2 sustojimai.",
                           "Medium tyre stress: usually 1–2 stops."),
    "strategy.tyres_low": ("Maža padangų apkrova: dažniausiai 1 sustojimas, strategijos mažai skiriasi.",
                           "Low tyre stress: usually 1 stop, strategies differ little."),
    "strategy.overtake_hard": ("Sunku aplenkti: kvalifikacija ir starto vieta lemia labai daug, svarbus "
                               "„undercut“ per sustojimus.",
                               "Hard to overtake: qualifying and grid position decide a lot, the undercut in the "
                               "pit stops matters."),
    "strategy.overtake_mid": ("Aplenkti įmanoma, bet starto vieta vis tiek svarbi.",
                              "Overtaking is possible, but grid position still matters."),
    "strategy.overtake_easy": ("Lengva aplenkti: greitas bolidas gali atsigauti ir iš toliau.",
                               "Easy to overtake: a fast car can recover from further back."),
    "strategy.street": ("Gatvių trasa: didelė saugos automobilio tikimybė gali sumaišyti strategijas.",
                        "Street circuit: a high safety-car chance can shake up strategies."),
    "track.schedule": ("Savaitgalio tvarkaraštis ir orai", "Weekend schedule and weather"),
    "track.schedule_sub": ("Laikas – jūsų kompiuterio laiko juostoje. Įvykusioms sesijoms lietus – iš trasos jutiklių.",
                           "Times are in your computer's time zone. For completed sessions rain comes from track sensors."),
    "track.col.session": ("Sesija", "Session"),
    "track.col.time": ("Laikas", "Time"),
    "track.col.status": ("Būsena", "Status"),
    "track.col.rain": ("Lietus", "Rain"),
    "track.col.temp": ("Temp.", "Temp."),
    "track.col.source": ("Orų šaltinis", "Weather source"),
    "track.col.top3": ("TOP3", "TOP3"),
    "wsource.trasos jutikliai": ("trasos jutikliai (faktas)", "track sensors (actual)"),
    "wsource.prognozė": ("prognozė", "forecast"),
    "track.podiums": ("Ankstesni metai šioje trasoje", "Previous years at this track"),
    "track.podiums_sub": ("Lenktynių podiumas ir pole pozicija", "Race podium and pole position"),
    "track.col.year": ("Metai", "Year"),
    "track.col.winner": ("Nugalėtojas", "Winner"),
    "track.col.pole": ("Pole", "Pole"),
    "track.drivers": ("Vairuotojai šioje trasoje", "Drivers at this track"),
    "track.drivers_sub": ("Šio savaitgalio vairuotojų lenktynių rezultatai čia nuo 2023 m.",
                          "Race results here since 2023 for this weekend's drivers"),
    "track.col.starts": ("Startai", "Starts"),
    "track.col.avg": ("Vid. vieta", "Avg finish"),
    "track.col.best": ("Geriausia", "Best"),
    "track.col.podiums": ("Podiumai", "Podiums"),
    "track.col.wins": ("Pergalės", "Wins"),
    "track.col.avg_quali": ("Vid. kvalif.", "Avg quali"),
    "track.no_history": ("Šioje trasoje ankstesnių rezultatų duomenų bazėje nėra.",
                         "There are no earlier results at this track in the database."),
    "section.probabilities": ("Tikimybės", "Probabilities"),
    "section.probabilities_sub": ("Tikimybė užimti kiekvieną vietą (modelio simuliacija)",
                                  "Chance of finishing in each position (model simulation)"),
    "section.why_sub": ("Kiek kiekvienas požymis prideda prie vairuotojo stiprumo (svoris × reikšmė)",
                        "How much each feature adds to a driver's strength (weight × value)"),
    "why.value": ("Indėlis į stiprumą", "Contribution to strength"),
    "col.driver":("Vairuotojas", "Driver"),
    "col.team": ("Komanda", "Team"),
    # --- svarbu šiam etapui (spėjimo skirtukas)
    "weekend.title": ("Svarbu šiam etapui", "Key facts for this round"),
    "weekend.sub": ("FIA dokumentai ir naujienos", "FIA documents and news"),
    "weekend.grid_title": ("Starto baudos", "Grid penalties"),
    "weekend.grid_text": ("Starto rikiuotė – oficiali FIA (su baudomis). Nubausti: {changes}.",
                          "Starting grid is the official FIA one (with penalties). Penalised: {changes}."),
    "weekend.grid_ok": ("Starto rikiuotė – oficiali FIA, baudų nėra.",
                        "Starting grid is the official FIA one; no penalties."),
    "weekend.upgrades": ("Naujos detalės (našumui)", "New parts (performance)"),
    "weekend.no_upgrades": ("FIA atnaujinimų dokumentas šiam etapui dar nepaskelbtas.",
                            "The FIA upgrades document for this round is not published yet."),
    "weekend.no_news": ("Svarbių naujienų apie pirmaujančias komandas nėra.",
                        "No important news about the leading teams."),
    # --- bolidų atnaujinimai
    "upgrades.none_yet": ("Atnaujinimų dar nėra – paspauskite „Atnaujinti duomenis“.",
                          "No upgrades yet. Press \"Update data\"."),
    "upgrades.team_title": ("Komandų atnaujinimai", "Team upgrades"),
    "upgrades.empty": ("Šiame etape naujų detalių neatvežė", "No new parts at this round"),
    "upgrades.source": ("Šaltinis", "Source"),
    "upgrades.full_doc": ("visas FIA dokumentas „Car Presentation Submissions“ (PDF)",
                          "full FIA document \"Car Presentation Submissions\" (PDF)"),
    "upgrades.doc": ("FIA dokumentas (PDF)", "FIA document (PDF)"),
    "upgrades.doc_page": ("FIA dokumentas, {page} psl. (PDF)", "FIA document, page {page} (PDF)"),
    "upgrades.articles": ("Straipsniai", "Articles"),
    "upgrades.season_title": ("Sezono apžvalga", "Season overview"),
    "upgrades.season_sub": ("Kiek našumą didinančių detalių komanda atvežė į kiekvieną etapą",
                            "How many performance parts each team brought to each round"),
    "upgrades.note": ("Atnaujinimai rodomi kaip informacija. Modelyje jie išbandyti, bet spėjimų nepagerino "
                      "(2025–2026 m. 296 tšk. vs 300), todėl modelis jų neįskaičiuoja.",
                      "Upgrades are shown for information. They were tested in the model but did not improve the "
                      "predictions (2025–2026: 296 pts vs 300), so the model does not use them."),
    "reason.performance": ("Našumas", "Performance"),
    "reason.circuit": ("Trasai", "Circuit"),
    "reason.reliability": ("Patikimumas", "Reliability"),
    # --- naujienos
    "news.intro": ("Naujienos iš patikimų šaltinių (formula1.com, Autosport, Motorsport.com, RaceFans, BBC), "
                   "automatiškai pažymėtos komandomis ir temomis. Atnaujinama kartu su duomenimis.",
                   "News from reliable sources (formula1.com, Autosport, Motorsport.com, RaceFans, BBC), automatically "
                   "tagged with teams and topics. Refreshed together with the data."),
    "news.all": ("Visos", "All"),
    "news.teams": ("Komandos", "Teams"),
    "news.tags": ("Temos", "Topics"),
    "news.sources": ("Šaltiniai", "Sources"),
    "news.search": ("Paieška", "Search"),
    "news.period": ("Laikotarpis", "Period"),
    "news.days": ("{n} d.", "{n} days"),
    "news.count": ("{n} naujienų", "{n} news items"),
    "news.none": ("Pagal pasirinktus filtrus naujienų nėra.", "No news match the selected filters."),
    "newstag.upgrades": ("Atnaujinimai", "Upgrades"),
    "newstag.penalties": ("Baudos", "Penalties"),
    "newstag.power_unit": ("Variklis", "Power unit"),
    "newstag.drivers": ("Vairuotojai", "Drivers"),
    "newstag.weather": ("Orai", "Weather"),
    "newstag.rules": ("Taisyklės", "Rules"),
    "newstag.tyres": ("Padangos", "Tyres"),
    # --- požymiai
    "features.intro": ("Kiekvienas požymis, jo **išmoktas svoris** ir **daugiklis** (1 = kaip išmokta, "
                       "0 = neatsižvelgti, 2 = dvigubai daugiau). Spėjimas persiskaičiuoja iškart.",
                       "Each feature with its **learned weight** and **multiplier** (1 = as learned, "
                       "0 = ignore, 2 = double). The prediction updates immediately."),
    "features.save": ("Išsaugoti", "Save"),
    "features.saved": ("Išsaugota – bus naudojama ir kitą kartą.", "Saved. It will be used next time too."),
    "features.reset": ("Visi į 1", "Reset all to 1"),
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
    "data.collected": ("Surinkti duomenys", "Collected data"),
    "data.collected_sub": ("Įvykusių sesijų skaičius pagal sezoną", "Completed sessions per season"),
    "reftable.trasos": ("Trasos", "Tracks"),
    "reftable.trasu_sinonimai": ("Trasų sinonimai", "Track aliases"),
    "reftable.komandos": ("Komandų spalvos", "Team colours"),
    "reftable.zaidejai": ("Žaidėjai", "Players"),
    "reftable.gp_pavadinimai": ("GP pavadinimai (Excel)", "GP names (Excel)"),
    "reftable.vairuotoju_vardai": ("Vairuotojų vardai (lažybos)", "Driver names (betting)"),
    "reftable.naujienu_saltiniai": ("Naujienų šaltiniai", "News sources"),
    "reftable.naujienu_zymes": ("Naujienų temos", "News topics"),
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
    "atnaujinimai": "FIA: new car parts declared by each team for every round (2024+)",
    "starto_rikiuote": "FIA: official starting grid with penalties (upcoming races and sprints)",
    "fia_dokumentai": "FIA documents already processed",
    "naujienos": "F1 news from reliable sources, tagged with teams and topics",
    "naujienu_saltiniai": "Reference: news sources (RSS)",
    "naujienu_zymes": "Reference: news topics and their keywords",
    "v_atnaujinimai": "View: car upgrades with GP name",
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
