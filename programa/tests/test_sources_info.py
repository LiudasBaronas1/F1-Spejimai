"""FIA dokumentų ir naujienų apdorojimas (be tinklo), komandų tapatybė, starto rikiuotė modelyje."""
import unittest

from f1model import model
from f1model.sources import fia, news
from tests.helpers import DRIVERS, synthetic_season, temp_app

COVER = "2026 TEST GRAND PRIX\nThe FIA Formula 1 Media Delegate\nTitle Car Presentation Submissions"
HEADER = ("Updated\ncomponent\nPrimary reason\nfor update\nGeometric differences compared to\nprevious version\n"
          "Brief description on how the update works\n(min 20, max 100 words)\n")


class FiaParsingTest(unittest.TestCase):
    def test_car_presentation(self):
        pages = [COVER,
                 "Car Presentation – Test Grand Prix\nMcLaren F1 Team\n" + HEADER +
                 "1 Front Wing Performance - Local Load Revised flap.\nMore load in 2 corners.\n"
                 "2 Rear Wing Circuit specific - Drag Reduction Lower downforce wing.",
                 "Rear wing text continues on page 3.",                       # tęsinys be antraštės
                 "Car Presentation – Test Grand Prix\nOracle Red Bull Racing.\n" + HEADER +
                 "1 Floor Edge Local load and flow conditioning. Reprofiled.",  # be „Performance“ žodžio
                 "Car Presentation – Test Grand Prix\nWilliams\nNo Updates"]
        rows = fia.parse_car_presentation(pages)
        mcl = [r for r in rows if r["team"] == "McLaren F1 Team"]
        self.assertEqual([(r["nr"], r["component"], r["reason"]) for r in mcl],
                         [(1, "Front Wing", "performance"), (2, "Rear Wing", "circuit")])
        self.assertIn("2 corners", mcl[0]["description"])              # skaičius aprašyme – ne nauja eilutė
        self.assertIn("continues on page 3", mcl[1]["description"])
        rbr = [r for r in rows if r["team"].startswith("Oracle")]
        self.assertEqual((rbr[0]["component"], rbr[0]["reason"]), ("Floor Edge", "performance"))
        self.assertEqual([(r["nr"], r["component"]) for r in rows if r["team"] == "Williams"], [(0, None)])
        # puslapis PDF'e (nuorodai #page=N): viršelis 1, McLaren 2 (tęsinys 3), Red Bull 4, Williams 5
        self.assertEqual({r["team"][:6]: r["page"] for r in rows}, {"McLare": 2, "Oracle": 4, "Willia": 5})

    def test_starting_grid(self):
        page = "Title Final Starting Grid\n1 3 Max VERSTAPPEN\nRed Bull\n1:35.1\n2 44 Lewis HAMILTON\n" \
               "8 6 Isack HADJAR *\nCar 6 - 5 place grid penalty"
        self.assertEqual(fia.parse_starting_grid([page]), [(1, 3), (2, 44), (8, 6)])

    def test_starting_grid_2026_layout_and_pit_lane(self):
        """2026 m. dokumentuose vieta, numeris ir vardas – atskirose eilutėsė; startuojantys iš boksų – gale."""
        page = ("1\n3\nMax VERSTAPPEN\nOracle Red Bull Racing\n1:31.156\n3\n16\nCharles LECLERC\nFerrari\n"
                "2\n63\nGeorge RUSSELL\nMercedes\n1:31.276\nDRIVERS REQUIRED TO START FROM THE PIT LANE\n55\n"
                "Carlos SAINZ *\nWilliams\n* PENALTIES\nCar 55 - pit lane\nThe F\n1\n FORMULA \n90\nFoo")
        self.assertEqual(fia.parse_starting_grid([page]), [(1, 3), (2, 63), (3, 16), (4, 55)])

    def test_doc_key(self):
        self.assertEqual(fia.doc_key("https://x/2024 Italian GP - Car Presentation Submissions.pdf"),
                         "2024_italian_gp_-_car_presentation_submissions.pdf")


class NewsTest(unittest.TestCase):
    def test_parse_rss_and_tags(self):
        xml = ("<rss><channel><item><title>Ferrari bring new floor &amp; upgrade</title>"
               "<link>https://a/1</link><description>&lt;p&gt;Grid penalty for Hamilton&lt;/p&gt;</description>"
               "<pubDate>Sat, 03 Oct 2026 15:45:03 +0000</pubDate></item></channel></rss>")
        item = news.parse_feed(xml)[0]
        self.assertEqual((item["title"], item["summary"], item["published"]),
                         ("Ferrari bring new floor & upgrade", "Grid penalty for Hamilton", "2026-10-03T15:45:03+00:00"))
        topics = [("upgrades", "upgrade"), ("penalties", "penalty"), ("weather", "rain")]
        self.assertEqual(news.tag(item["title"] + " " + item["summary"], topics), ["penalties", "upgrades"])
        self.assertEqual(news.tag("Ukraine", topics), [])                # „rain“ ne žodžio pradžioje


class BriefingTest(unittest.TestCase):
    def test_upgrades_links_and_articles(self):
        app, _ = temp_app()
        synthetic_season(app.db, rounds=2)
        db, brief = app.db, app.briefing()
        db.write("atnaujinimai", [dict(season=2026, round=1, komanda="McLaren F1 Team", nr=1, detale="Floor",
                                       priezastis="performance", aprasymas="x", puslapis=3)])
        db.write("fia_dokumentai", [dict(tipas="car_presentation", season=2026, round=1, url="https://fia/doc.pdf",
                                         gauta="x")])
        team = brief.upgrades(2026, 1)[0]                                   # naujienų nėra – be klaidų
        self.assertEqual((team.source_url, team.articles), ("https://fia/doc.pdf#page=3", []))
        self.assertTrue(brief.news(days=10000).empty and brief.news(days=10000, tags=["upgrades"]).empty)
        day = db.query("SELECT date FROM events WHERE round=1").date.iloc[0]
        db.write("naujienos", [dict(url=f"https://n/{i}", saltinis="S", pavadinimas=title, santrauka="",
                                    paskelbta=f"{day}T10:00:00+00:00", komandos="mclaren", zymes="upgrades")
                               for i, title in enumerate(["McLaren brings new floor", "McLaren brings a new floor",
                                                          "Ferrari brings new wing"])])   # McLaren – tik tekste
        self.assertEqual([a[0] for a in brief.upgrades(2026, 1)[0].articles], ["McLaren brings new floor"])


class TeamIdentityTest(unittest.TestCase):
    def test_same_colour_is_same_team(self):
        ref = temp_app()[0].reference()
        self.assertEqual({ref.team_key(n) for n in ("RB F1 Team", "Racing Bulls", "Visa Cash App RB F1 Team")},
                         {"racing bulls"})
        self.assertEqual(ref.team_key("Oracle Red Bull Racing"), "red bull")
        self.assertIsNone(ref.team_key("Nežinoma"))


class WeekendChecksTest(unittest.TestCase):
    def test_checklist_reports_missing_results_and_odds(self):
        from f1model import status
        app, _ = temp_app()
        synthetic_season(app.db, rounds=6)          # 7 etapo kvalifikacija praėjo, bet duomenų nėra
        checks = {c.key: c for c in status.weekend_checks(app.dataset(), app.db, 2026, 7, "R")}
        self.assertLessEqual({"results", "grid", "weather", "odds", "news"}, set(checks))
        self.assertEqual((checks["results"].state, checks["results"].params["sessions"]), ("missing", ["Q"]))
        self.assertEqual((checks["grid"].state, checks["odds"].state), ("missing", "missing"))
        app.db.execute("UPDATE sessions SET status='fia' WHERE round=7 AND session='Q'")   # preliminarus FIA rezultatas
        checks = {c.key: c for c in status.weekend_checks(app.dataset(), app.db, 2026, 7, "R")}
        self.assertEqual(checks["results"].state, "warn")


class FiaGridInModelTest(unittest.TestCase):
    def test_upcoming_race_uses_fia_grid(self):
        app, _ = temp_app()
        synthetic_season(app.db, rounds=6)
        nxt = 7
        app.db.write("results", [dict(season=2026, round=nxt, session="Q", driver=d, team="Team " + d[0],
                                       position=i + 1, official_position=i + 1, grid=None, status="Finished")
                                  for i, d in enumerate(DRIVERS)])
        app.db.execute("UPDATE sessions SET status='ok' WHERE round=? AND session='Q'", (nxt,))
        before = model.predict(app.dataset(), 2026, nxt, "R")
        # FIA: lyderis AAA gavo baudą ir startuoja paskutinis
        app.db.write("starto_rikiuote", [dict(season=2026, round=nxt, session="R", driver=d, grid=g, dokumentas="x")
                                         for g, d in enumerate(DRIVERS[1:] + DRIVERS[:1], 1)])
        after = model.predict(app.dataset(), 2026, nxt, "R")
        self.assertGreater(before["table"].loc["AAA", "weekend"], after["table"].loc["AAA", "weekend"])


if __name__ == "__main__":
    unittest.main()
