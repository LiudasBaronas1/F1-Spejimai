"""Informacija sąsajai iš FIA dokumentų ir naujienų: komandų bolidų atnaujinimai, naujienų paieška,
svarbiausi faktai konkrečiam etapui (starto baudos, atnaujinimai, susijusios naujienos).
Tik skaitymas iš DB – jokios rodymo logikos (ją daro ui.py / ui_style.py)."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher

import pandas as pd

REASON_ORDER = ["performance", "circuit", "reliability"]
IMPORTANT_TAGS = {"penalties", "power_unit", "drivers", "weather", "upgrades"}


def _has_any(column, values):
    """Ar kableliais atskirtų žymių stulpelyje yra bent viena iš values (visada bool – ir tuščiam stulpeliui)."""
    values = set(values)
    return column.fillna("").map(lambda s: bool(set(s.split(",")) & values)).astype(bool)


@dataclass
class TeamUpgrades:
    key: str
    name: str
    color: str
    counts: dict          # priežastis -> detalių skaičius
    items: list           # [(detalė, priežastis, aprašymas)]
    source_url: str = None    # FIA dokumentas, atidaromas ties komandos puslapiu
    page: int = None
    articles: list = None     # [(pavadinimas, nuoroda, šaltinis)] – straipsniai apie komandos atnaujinimus


class Briefing:
    def __init__(self, db, ref):
        self.db, self.ref = db, ref

    # --- komandos
    def teams(self, season):
        """{komandos raktas: (pavadinimas, taškai)} pagal sezono rezultatus (naujausias pavadinimas)."""
        r = self.db.query("SELECT r.team, SUM(COALESCE(r.points, 0)) AS pts, MAX(s.date_utc) AS last "
                          "FROM results r JOIN sessions s USING(season, round, session) WHERE r.season=? "
                          "GROUP BY r.team", (int(season),))
        out = {}
        for team, pts, last in r.sort_values("last").values:
            key = self.ref.team_key(team)
            if key:
                out[key] = (team, out.get(key, (None, 0))[1] + pts)
        return out

    def _team(self, key, fallback, season_teams):
        name = season_teams.get(key, (fallback, 0))[0]
        return name, self.ref.team_color(name or fallback)

    # --- bolidų atnaujinimai
    def upgrade_rounds(self, season):
        """[(etapas, GP pavadinimas)] su FIA atnaujinimų dokumentu."""
        return [tuple(r) for r in self.db.query(
            "SELECT DISTINCT a.round, e.name FROM atnaujinimai a JOIN events e USING(season, round) "
            "WHERE a.season=? ORDER BY a.round", (int(season),)).values]

    def upgrade_document(self, season, rnd):
        """FIA „Car Presentation“ dokumento nuoroda (arba None)."""
        r = self.db.query("SELECT url FROM fia_dokumentai WHERE tipas='car_presentation' AND season=? AND round=?",
                          (int(season), int(rnd)))
        return r.url.iloc[0] if not r.empty else None

    def upgrades(self, season, rnd):
        """[TeamUpgrades], komandos – pagal sezono taškus (stipriausios pirmos)."""
        df = self.db.query("SELECT komanda, nr, detale, priezastis, aprasymas, puslapis FROM atnaujinimai "
                           "WHERE season=? AND round=? ORDER BY komanda, nr", (int(season), int(rnd)))
        season_teams, doc = self.teams(season), self.upgrade_document(season, rnd)
        articles = self._upgrade_articles(season, rnd)
        out = {}
        for team, g in df.groupby("komanda", sort=False):
            key = self.ref.team_key(team) or team
            name, color = self._team(key, team, season_teams)
            items = [(d, p, a) for n, d, p, a in g[["nr", "detale", "priezastis", "aprasymas"]].values if n > 0]
            page = int(g.puslapis.min()) if g.puslapis.notna().any() else None
            prev = out.get(key)
            if prev:  # ta pati komanda dokumente du kartus – sujungiame
                items, page = prev.items + items, prev.page or page
            counts = {r: sum(1 for _, p, _ in items if p == r) for r in REASON_ORDER}
            url = f"{doc}#page={page}" if doc and page else doc
            out[key] = TeamUpgrades(key, name, color, counts, items, url, page, articles.get(key, []))
        return sorted(out.values(), key=lambda t: -season_teams.get(t.key, (None, -1))[1])

    def _upgrade_articles(self, season, rnd, days_before=6, days_after=2, per_team=3):
        """{komandos raktas: [(pavadinimas, nuoroda, šaltinis)]} – naujienos su žyme „upgrades“ apie komandą
        per kelias dienas iki etapo ir po jo."""
        ev = self.db.query("SELECT date FROM events WHERE season=? AND round=?", (int(season), int(rnd)))
        if ev.empty or not ev.date.iloc[0]:
            return {}
        day = pd.Timestamp(ev.date.iloc[0], tz="UTC")
        df = self.db.query("SELECT pavadinimas, url, saltinis, komandos, zymes FROM naujienos "
                           "WHERE paskelbta BETWEEN ? AND ? ORDER BY paskelbta DESC",
                           ((day - pd.Timedelta(days=days_before)).isoformat(),
                            (day + pd.Timedelta(days=days_after + 1)).isoformat()))
        df = df[_has_any(df.zymes, ["upgrades"])].drop_duplicates("pavadinimas")
        names = {}   # komandos raktas -> visi jos raktažodžiai (pvz. racing bulls: rb f1, visa cash app)
        for kw, _ in self.ref.team_colors:
            names.setdefault(self.ref.team_key(kw), []).append(kw.lower())
        out = {}
        for title, url, src, teams in df[["pavadinimas", "url", "saltinis", "komandos"]].values:
            for key in filter(None, (teams or "").split(",")):
                picked = out.setdefault(key, [])
                about_team = any(kw in title.lower() for kw in names.get(key, [key]))   # komanda – pavadinime
                duplicate = any(SequenceMatcher(None, title.lower(), t.lower()).ratio() > 0.75 for t, _, _ in picked)
                if about_team and not duplicate and len(picked) < per_team:
                    picked.append((title, url, src))
        return {k: v for k, v in out.items() if v}

    def upgrade_matrix(self, season, reason="performance"):
        """DataFrame: komanda x etapas -> detalių skaičius (pagal priežastį; None – visos)."""
        df = self.db.query("SELECT a.round, e.name, a.komanda, a.nr, a.priezastis FROM atnaujinimai a "
                           "JOIN events e USING(season, round) WHERE a.season=?", (int(season),))
        if df.empty:
            return pd.DataFrame()
        season_teams = self.teams(season)
        df["team"] = [self._team(self.ref.team_key(t) or t, t, season_teams)[0] for t in df.komanda]
        df["gp"] = df["round"].astype(str) + ". " + df.name.str.replace(" Grand Prix", "", regex=False)
        hit = (df.nr > 0) & ((df.priezastis == reason) if reason else True)
        m = df.assign(n=hit.astype(int)).pivot_table(index="team", columns=["round", "gp"], values="n", aggfunc="sum",
                                                     fill_value=0)
        m.columns = [gp for _, gp in m.columns]
        order = sorted(m.index, key=lambda t: -season_teams.get(self.ref.team_key(t), (None, -1))[1])
        return m.loc[order]

    # --- naujienos
    def news(self, days=30, teams=(), tags=(), sources=(), text="", limit=60):
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="seconds")
        df = self.db.query("SELECT * FROM naujienos WHERE paskelbta >= ? ORDER BY paskelbta DESC", (since,))
        if teams:
            df = df[_has_any(df.komandos, teams)]
        if tags:
            df = df[_has_any(df.zymes, tags)]
        if sources:
            df = df[df.saltinis.isin(sources)]
        if text:
            low = text.lower()
            df = df[(df.pavadinimas + " " + df.santrauka.fillna("")).str.lower().str.contains(low, regex=False).astype(bool)]
        return df.drop_duplicates("pavadinimas").head(limit)   # ta pati naujiena keliuose šaltiniuose

    def news_sources(self):
        return self.db.query("SELECT DISTINCT saltinis FROM naujienos ORDER BY saltinis").saltinis.tolist()

    def news_tags(self):
        return self.db.query("SELECT DISTINCT zyme FROM naujienu_zymes ORDER BY zyme").zyme.tolist()

    # --- svarbu šiam etapui
    def grid_changes(self, data, season, rnd, session):
        """[(vairuotojas, kvalifikacijos vieta, FIA starto vieta)] nubaustiems (startuoja toliau nei kvalifikavosi);
        pakilę dėl kitų baudų neįtraukiami."""
        fia = data.fia_grid(season, rnd, session)
        if not fia or session not in ("R", "S"):
            return []
        q = data.results_of(season, rnd, "Q" if session == "R" else "SQ")
        quali = dict(zip(q.driver, q.position))
        return sorted(((d, int(quali[d]), int(g)) for d, g in fia.items()
                       if d in quali and pd.notna(quali[d]) and int(g) > int(quali[d])), key=lambda x: x[2])

    def weekend_news(self, event_date, team_keys, days_before=6, limit=5):
        """Svarbios naujienos (baudos, variklis, vairuotojai, orai, atnaujinimai) apie nurodytas komandas
        per kelias dienas iki etapo ir jo metu."""
        start = (pd.Timestamp(event_date, tz="UTC") - pd.Timedelta(days=days_before)).isoformat()
        end = (pd.Timestamp(event_date, tz="UTC") + pd.Timedelta(days=3)).isoformat()
        df = self.db.query("SELECT * FROM naujienos WHERE paskelbta BETWEEN ? AND ? ORDER BY paskelbta DESC",
                           (start, end))
        keep = _has_any(df.zymes, IMPORTANT_TAGS) & _has_any(df.komandos, team_keys)
        return df[keep].drop_duplicates("pavadinimas").head(limit)
