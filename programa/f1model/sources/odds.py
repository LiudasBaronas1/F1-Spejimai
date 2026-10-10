"""Lažybų rinkų kainos: Kalshi, Polymarket (su istorija) ir lažybininkai (DeltaF1, tik dabartinis etapas).

Kaina (0..1) = rinkos priskiriama tikimybė. Imama paskutinė kaina PRIEŠ sesijos pradžią (mokantis
nežiūrima į ateitį). Mažos apyvartos rinkos atmetamos. Tikimybės normalizuojamos: nugalėtojo/pole
suma = 1, podiumo = 3, TOP5 = 5.

NAUJAS ŠALTINIS = `OddsSource` poklasis su events(), driver(), volume(), price_before().
"""
import json
import re
import time
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone

import pandas as pd
import requests

from . import DataSource, get_json, log

MIN_VOLUME_USD = 50
HISTORY_HOURS = 48           # kiek valandų prieš sesiją ieškoti paskutinės kainos
PAUSE_S = 0.15
MARKET_TOTAL = {"podium": 3.0, "top5": 5.0}


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _ts(unix):
    return datetime.fromtimestamp(unix, timezone.utc).isoformat()


def driver_code(name, known, overrides):
    """Vardas -> trumpinys (pavardės pirmos 3 raidės), tikrinant, ar toks vairuotojas važiuoja.
    overrides – žinynas „vairuotoju_vardai“ (išimtys, pvz. ZHOU -> ZHO)."""
    n = "".join(c for c in unicodedata.normalize("NFKD", name or "") if not unicodedata.combining(c)).upper().strip()
    for key in [n] + n.split():
        if key in overrides:
            return overrides[key]
    if not n or n in ("OTHER", "FIELD"):
        return None
    code = n.split()[-1][:3]
    return code if (not known or code in known) else None


@dataclass
class MarketEvent:
    session: str                # SQ / S / Q / R
    market: str                 # win / pole / podium / top5
    date: pd.Timestamp          # sesijos data (susiejimui)
    ident: str                  # įvykio identifikatorius šaltinyje
    items: list                 # vairuotojų rinkos
    extra: dict = field(default_factory=dict)


class OddsSource(DataSource):
    source = ""                 # reikšmė DB stulpelyje `source`

    # --- šaltinio specifika
    def events(self, season, skip):
        raise NotImplementedError

    def driver(self, item, known):
        raise NotImplementedError

    def volume(self, item):
        raise NotImplementedError

    def price_before(self, ev, item, t0):
        raise NotImplementedError

    # --- bendra eiga
    def update(self, season):
        sess = self.db.query("SELECT season, round, session, date_utc, status FROM sessions WHERE season=?", (season,))
        sess["d"] = pd.to_datetime(sess.date_utc, utc=True, format="ISO8601")
        known = set(self.db.query("SELECT driver FROM results WHERE season=? UNION SELECT driver FROM practice "
                             "WHERE season=?", (season, season)).driver)
        stored = self.db.query("SELECT o.round, o.session, o.market, o.event_slug FROM odds o JOIN sessions s "
                               "USING(season, round, session) WHERE o.season=? AND o.source=? "
                               "GROUP BY 1, 2, 3, 4 HAVING MAX(o.fetched_at) >= MAX(s.date_utc)",
                               (season, self.source))
        # surinkta po sesijos pradžios = galutinė kaina; surinktos anksčiau (pvz. sprinto – prieš SQ) perrenkamos
        have = set(zip(stored["round"], stored.session, stored.market))
        now = datetime.now(timezone.utc)
        events = list(self.events(season, skip=set(stored.event_slug)))
        for i, ev in enumerate(events):
            self.progress(i, len(events), f"{ev.session} {ev.market} {ev.date:%m-%d}")
            cand = sess[(sess.session == ev.session) & ((sess.d.dt.normalize() - ev.date.normalize()).abs()
                                                        <= pd.Timedelta(days=1))]
            if cand.empty:
                continue
            s = cand.iloc[0]
            if (s["round"], ev.session, ev.market) in have and (s.status == "ok" or s.d < now):
                continue  # įvykusios sesijos kainos jau surinktos
            rows = []
            for item in ev.items:
                code, vol = self.driver(item, known), self.volume(item)
                if not code or vol < MIN_VOLUME_USD:
                    continue
                try:
                    price, ts = self.price_before(ev, item, min(s.d.to_pydatetime(), now))
                except Exception:
                    continue
                time.sleep(PAUSE_S)
                if price:
                    rows.append(dict(driver=code, price=float(price), volume=vol, price_ts=ts))
            n = self.store(rows, season, int(s["round"]), ev.session, ev.market, ev.ident)
            if n:
                log.info("%s %s R%02d %s %s: %s vairuotojų", self.label, season, s["round"], ev.session, ev.market, n)

    def store(self, rows, season, rnd, session, market, ident, total=None):
        """Normalizuoja tikimybes ir įrašo vienos rinkos kainas."""
        if not rows:
            return 0
        df = pd.DataFrame(rows).drop_duplicates("driver")
        if df.price.sum() <= 0:
            return 0
        target = total or MARKET_TOTAL.get(market, 1.0)
        if market in MARKET_TOTAL:  # kainos ne visiems vairuotojams – tik mažinama, kad 0.80 netaptų 0.99
            df["prob"] = (df.price * min(1.0, target / df.price.sum())).clip(upper=0.99)
        else:
            df["prob"] = df.price / df.price.sum() * target
        df = df.assign(season=season, round=rnd, session=session, market=market, source=self.source,
                       event_slug=ident, fetched_at=datetime.now(timezone.utc).isoformat())
        self.db.write("odds", df.to_dict("records"), replace_where=(
            "season=? AND round=? AND session=? AND market=? AND source=?", (season, rnd, session, market, self.source)))
        return len(df)


# ------------------------------------------------------------------ Kalshi

class KalshiSource(OddsSource):
    """Reguliuojama JAV birža, didelės apyvartos. Senesni įvykiai – /historical archyve."""
    label, source = "Kalshi", "kalshi"
    API = "https://api.elections.kalshi.com/trade-api/v2"
    SERIES = {"KXF1RACE": ("R", "win"), "KXF1POLE": ("Q", "pole"), "KXF1POLEPOSITION": ("Q", "pole"),
              "KXF1RACEPODIUM": ("R", "podium"), "KXF1TOP5": ("R", "top5"), "KXF1RACESPRINT": ("S", "win"),
              "KXF1SPRINTPOLE": ("SQ", "pole"), "KXF1SPRINTTOP5": ("S", "top5")}
    MAX_SPREAD = 0.20           # didesnis pirkimo/pardavimo skirtumas -> imama paskutinio sandorio kaina

    def events(self, season, skip):
        for series, (session, market) in self.SERIES.items():
            cursor = None
            while True:
                r = get_json(f"{self.API}/events", dict(series_ticker=series, limit=200, with_nested_markets="true",
                                                       **({"cursor": cursor} if cursor else {})))
                for ev in r.get("events", []):
                    yr = re.search(r"(\d{2})[A-Z]*$", ev["event_ticker"].split("-", 1)[-1])
                    if yr and 2000 + int(yr.group(1)) != season:
                        continue
                    markets, historical = ev.get("markets") or [], False
                    if not markets:  # archyvuotas (pasibaigęs) įvykis – jei jau surinktas, praleidžiame
                        if ev["event_ticker"] in skip:
                            continue
                        markets = get_json(f"{self.API}/historical/markets",
                                           dict(event_ticker=ev["event_ticker"], limit=100)).get("markets", [])
                        historical = True
                    if markets:
                        d = pd.Timestamp(markets[0].get("expected_expiration_time") or markets[0].get("close_time"))
                        yield MarketEvent(session, market, d, ev["event_ticker"], markets,
                                          dict(series=series, historical=historical))
                cursor = r.get("cursor")
                if not cursor:
                    break

    def driver(self, m, known):
        code = m["ticker"].rsplit("-", 1)[-1].upper()
        return code if not known or code in known else driver_code(m.get("yes_sub_title", ""), known, self.ref.driver_names)

    def volume(self, m):
        return _f(m.get("volume_fp", m.get("volume"))) or 0

    def price_before(self, ev, m, t0):
        end = int(t0.timestamp())
        params = dict(start_ts=end - HISTORY_HOURS * 3600, end_ts=end, period_interval=60)
        hist_url = f"{self.API}/historical/markets/{m['ticker']}/candlesticks"
        try:
            r = get_json(hist_url if ev.extra["historical"] else
                         f"{self.API}/series/{ev.extra['series']}/markets/{m['ticker']}/candlesticks", params)
        except requests.HTTPError:
            r = get_json(hist_url, params)  # rinka jau archyvuota

        def close(d):
            d = d or {}
            return _f(d.get("close_dollars", d.get("close")))
        for c in reversed(r.get("candlesticks", [])):
            bid, ask, last = close(c.get("yes_bid")), close(c.get("yes_ask")), close(c.get("price"))
            if bid is not None and ask is not None and 0 < ask - bid <= self.MAX_SPREAD:
                return (bid + ask) / 2, _ts(c["end_period_ts"])
            if last is not None:
                return last, _ts(c["end_period_ts"])
        return None, None


# ------------------------------------------------------------------ Polymarket

class PolymarketSource(OddsSource):
    label, source = "Polymarket", "polymarket"
    GAMMA = "https://gamma-api.polymarket.com/events"
    HISTORY = "https://clob.polymarket.com/prices-history"
    TYPES = [("sprint-qualifying-pole", "SQ", "pole"), ("sprint-race-winner", "S", "win"),
             ("sprint-winner", "S", "win"), ("driver-pole-position", "Q", "pole"),
             ("driver-podium", "R", "podium"), ("grand-prix-driver-winner", "R", "win"),
             ("grand-prix-winner", "R", "win")]

    def events(self, season, skip):
        for closed in ("true", "false"):
            offset = 0
            while page := get_json(self.GAMMA, dict(tag_slug="f1", closed=closed, limit=100, offset=offset)):
                for ev in page:
                    kind = next(((s, m) for frag, s, m in self.TYPES if frag in ev["slug"]), None)
                    if kind and "constructor" not in ev["slug"] and not (closed == "true" and ev["slug"] in skip):
                        m = re.search(r"(\d{4}-\d{2}-\d{2})$", ev["slug"])
                        d = pd.Timestamp(m.group(1), tz="UTC") if m else \
                            pd.Timestamp(ev.get("endDate") or ev.get("startDate")).normalize()
                        if d.year == season:
                            yield MarketEvent(*kind, d, ev["slug"], ev.get("markets", []))
                offset += 100
                time.sleep(PAUSE_S)

    def driver(self, m, known):
        return driver_code(m.get("groupItemTitle") or m.get("question", ""), known, self.ref.driver_names)

    def volume(self, m):
        return _f(m.get("volume")) or 0

    def price_before(self, ev, m, t0):
        end = int(t0.timestamp())
        h = get_json(self.HISTORY, dict(market=json.loads(m["clobTokenIds"])[0],
                                        startTs=end - HISTORY_HOURS * 3600, endTs=end, fidelity=30))
        pts = [p for p in h.get("history", []) if p["t"] <= end]
        return (pts[-1]["p"], _ts(pts[-1]["t"])) if pts else (None, None)


# ------------------------------------------------------------------ lažybininkai (DeltaF1)

class BookmakerSource(OddsSource):
    """bet365 / DraftKings / FanDuel lenktynių nugalėtojo koeficientai artimiausiam etapui.
    DeltaF1 juos atnaujina tik kas savaitę, todėl modelyje jie – tik atsarginis šaltinis."""
    label, source = "lažybininkai", "bookmakers"
    URL = "https://www.deltaf1.com/odds"
    COVERAGE = 0.97             # rodomi tik favoritai – jie kartu turi ~97 % tikimybės

    def update(self, season):
        now = datetime.now(timezone.utc).isoformat()
        nxt = self.db.query("SELECT round FROM sessions WHERE season=? AND session='R' AND date_utc > ? "
                       "ORDER BY date_utc LIMIT 1", (season, now))
        if nxt.empty:
            return
        html = requests.get(self.URL, timeout=30, headers={"User-Agent": "Mozilla/5.0"}).text
        known = set(self.db.query("SELECT driver FROM practice WHERE season=? UNION SELECT driver FROM results "
                             "WHERE season=?", (season, season)).driver)
        rows = []
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", html.split("</table>")[0], flags=re.S):
            cells = [re.sub(r"<[^>]+>", " ", c).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, flags=re.S)]
            odds = [o for o in map(_f, cells[2:]) if o and o > 1.0]
            code = driver_code(cells[0].replace("FAV", ""), known, self.ref.driver_names) if cells else None
            if code and odds:
                rows.append(dict(driver=code, price=sum(1 / o for o in odds) / len(odds), volume=None, price_ts=now))
        if len(rows) >= 3:
            self.store(rows, season, int(nxt["round"].iloc[0]), "R", "win", "deltaf1:bet365/draftkings/fanduel",
                       total=self.COVERAGE)
