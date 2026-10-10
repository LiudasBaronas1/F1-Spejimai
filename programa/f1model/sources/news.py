"""F1 naujienos iš patikimų šaltinių (RSS): formula1.com, Autosport, Motorsport.com, RaceFans, BBC.

Šaltinių sąrašas ir temų raktažodžiai – žinynuose `naujienu_saltiniai` ir `naujienu_zymes` (redaguojami
programoje). Kiekviena naujiena pažymima:
- komandomis – pagal žinyno „komandos“ raktažodžius (tie patys, kurie nustato komandų spalvas);
- temomis (atnaujinimai, baudos, variklis, vairuotojai, orai, taisyklės) – pagal temų raktažodžius.
"""
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape

import requests

from . import DataSource, log

HEADERS = {"User-Agent": "Mozilla/5.0 (F1 Spejimai)"}
KEEP_DAYS = 120


def _text(s):
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def _when(s):
    """Paskelbimo laikas UTC arba None (kai šaltinis jo nenurodo – tada naudojamas pirmo pamatymo laikas)."""
    try:
        return parsedate_to_datetime(s).astimezone(timezone.utc).isoformat(timespec="seconds")
    except (TypeError, ValueError):
        try:
            return datetime.fromisoformat((s or "").replace("Z", "+00:00")).astimezone(timezone.utc).isoformat(
                timespec="seconds")
        except ValueError:
            return None


def parse_feed(xml_text):
    """[{title, url, summary, published}] iš RSS 2.0 arba Atom."""
    root = ET.fromstring(xml_text)
    items = []
    for it in root.iter("item"):
        items.append(dict(title=_text(it.findtext("title")), url=(it.findtext("link") or "").strip(),
                          summary=_text(it.findtext("description"))[:600], published=_when(it.findtext("pubDate"))))
    ns = {"a": "http://www.w3.org/2005/Atom"}
    for it in root.findall("a:entry", ns):
        link = it.find("a:link", ns)
        items.append(dict(title=_text(it.findtext("a:title", namespaces=ns)),
                          url=link.get("href") if link is not None else "",
                          summary=_text(it.findtext("a:summary", namespaces=ns))[:600],
                          published=_when(it.findtext("a:updated", namespaces=ns))))
    return [i for i in items if i["title"] and i["url"]]


def tag(text, keywords):
    """keywords – [(žymė, raktažodis)]; grąžina surūšiuotas žymes, kurių raktažodis tekste yra kaip žodis."""
    low = f" {text.lower()} "
    return sorted({t for t, kw in keywords if re.search(rf"(?<![a-z]){re.escape(kw.lower())}", low)})


class NewsSource(DataSource):
    label = "naujienos"
    expected_s = 8.0

    def update(self, season):
        feeds = self.db.query("SELECT pavadinimas, adresas FROM naujienu_saltiniai WHERE aktyvus=1")
        topics = [tuple(r) for r in self.db.query("SELECT zyme, raktazodis FROM naujienu_zymes").values]
        teams = self._team_keywords()
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        first_seen = dict(self.db.query("SELECT url, paskelbta FROM naujienos").values)
        rows = []
        for i, (name, url) in enumerate(feeds.values):
            self.progress(i, len(feeds), name)
            try:
                r = requests.get(url, headers=HEADERS, timeout=30)
                r.raise_for_status()
                items = parse_feed(r.content)
            except Exception as e:  # vienas neveikiantis šaltinis nestabdo kitų
                log.warning("Naujienos %s: %s", name, e)
                continue
            for it in items:
                text = f"{it['title']} {it['summary']}"
                rows.append(dict(url=it["url"], saltinis=name, pavadinimas=it["title"], santrauka=it["summary"],
                                 paskelbta=it["published"] or first_seen.get(it["url"], now), komandos=",".join(tag(text, teams)),
                                 zymes=",".join(tag(text, topics)), gauta=now))
        self.db.write("naujienos", rows, keys=["url"])
        cutoff = datetime.fromtimestamp(datetime.now(timezone.utc).timestamp() - KEEP_DAYS * 86400, timezone.utc)
        self.db.execute("DELETE FROM naujienos WHERE paskelbta < ?", (cutoff.isoformat(timespec="seconds"),))
        log.info("Naujienos: %s įrašų iš %s šaltinių", len(rows), len(feeds))

    def _team_keywords(self):
        """[(komandos tapatybė, raktažodis)] – žymė visada ta pati komanda, nors rašoma įvairiai."""
        return [(self.ref.team_key(kw), kw) for kw, _ in self.ref.team_colors]

    def retag(self):
        """Iš naujo pažymi visas naujienas (pakeitus komandų ar temų žinynus)."""
        topics = [tuple(r) for r in self.db.query("SELECT zyme, raktazodis FROM naujienu_zymes").values]
        teams = self._team_keywords()
        df = self.db.query("SELECT url, pavadinimas, santrauka FROM naujienos")
        self.db.write("naujienos", [dict(url=u, komandos=",".join(tag(f"{t} {s}", teams)),
                                         zymes=",".join(tag(f"{t} {s}", topics))) for u, t, s in df.values],
                      keys=["url"])
