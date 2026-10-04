"""Informacija sąsajai iš FIA dokumentų ir naujienų: komandų bolidų atnaujinimai, naujienų paieška,
svarbiausi faktai konkrečiam etapui (starto baudos, atnaujinimai, susijusios naujienos).
Tik skaitymas iš DB – jokios rodymo logikos (ją daro ui.py / ui_style.py)."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pandas as pd

REASON_ORDER = ["performance", "circuit", "reliability"]
IMPORTANT_TAGS = {"penalties", "power_unit", "drivers", "weather", "upgrades"}


@dataclass
class TeamUpgrades:
    key: str
    name: str
    color: str
    counts: dict          # priežastis -> detalių skaičius
    items: list           # [(detalė, priežastis, aprašymas)]


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

    def upgrades(self, season, rnd):
        """[TeamUpgrades], komandos – pagal sezono taškus (stipriausios pirmos)."""
        df = self.db.query("SELECT komanda, nr, detale, priezastis, aprasymas FROM atnaujinimai "
                           "WHERE season=? AND round=? ORDER BY komanda, nr", (int(season), int(rnd)))
        season_teams = self.teams(season)
        out = {}
        for team, g in df.groupby("komanda", sort=False):
            key = self.ref.team_key(team) or team
            name, color = self._team(key, team, season_teams)
            items = [(d, p, a) for n, d, p, a in g[["nr", "detale", "priezastis", "aprasymas"]].values if n > 0]
            prev = out.get(key)
            if prev:  # ta pati komanda dokumente du kartus – sujungiame
                items = prev.items + items
            counts = {r: sum(1 for _, p, _ in items if p == r) for r in REASON_ORDER}
            out[key] = TeamUpgrades(key, name, color, counts, items)
        return sorted(out.values(), key=lambda t: -season_teams.get(t.key, (None, -1))[1])

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
            df = df[df.komandos.fillna("").map(lambda s: bool(set(s.split(",")) & set(teams)))]
        if tags:
            df = df[df.zymes.fillna("").map(lambda s: bool(set(s.split(",")) & set(tags)))]
        if sources:
            df = df[df.saltinis.isin(sources)]
        if text:
            low = text.lower()
            df = df[(df.pavadinimas + " " + df.santrauka.fillna("")).str.lower().str.contains(low, regex=False)]
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
        keep = df.zymes.fillna("").map(lambda s: bool(set(s.split(",")) & IMPORTANT_TAGS)) & \
            df.komandos.fillna("").map(lambda s: bool(set(s.split(",")) & set(team_keys)))
        return df[keep].drop_duplicates("pavadinimas").head(limit)
