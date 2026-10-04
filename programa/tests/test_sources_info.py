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

    def test_starting_grid(self):
        page = "Title Final Starting Grid\n1 3 Max VERSTAPPEN\nRed Bull\n1:35.1\n2 44 Lewis HAMILTON\n" \
               "8 6 Isack HADJAR *\nCar 6 - 5 place grid penalty"
        self.assertEqual(fia.parse_starting_grid([page]), [(1, 3), (2, 44), (8, 6)])

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


class TeamIdentityTest(unittest.TestCase):
    def test_same_colour_is_same_team(self):
        ref = temp_app()[0].reference()
        self.assertEqual({ref.team_key(n) for n in ("RB F1 Team", "Racing Bulls", "Visa Cash App RB F1 Team")},
                         {"racing bulls"})
        self.assertEqual(ref.team_key("Oracle Red Bull Racing"), "red bull")
        self.assertIsNone(ref.team_key("Nežinoma"))


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
