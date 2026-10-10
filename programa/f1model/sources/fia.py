"""Oficialūs FIA dokumentai (fia.com): bolidų atnaujinimai ir starto rikiuotė.

- „Car Presentation Submissions“ – kiekvieną savaitgalį (ketvirtadienį/penktadienį) komandos privalo
  nurodyti visas naujas bolido detales ir priežastį (našumas / trasai specifinė / patikimumas).
  -> lentelė `atnaujinimai` (2024+).
- „Final/Provisional Starting Grid“ ir sprinto atitikmenys – starto rikiuotė SU baudomis (variklio
  elementai, susidūrimai). -> lentelė `starto_rikiuote`; modelis ją naudoja artėjančioms lenktynėms,
  kol oficialių rezultatų dar nėra (kitaip – kvalifikacijos vieta, be baudų).

Apdoroti dokumentai pažymimi lentelėje `fia_dokumentai`, kad nebūtų siunčiami pakartotinai.
"""
import io
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, unquote

import requests

from ..config import ready_at
from . import DataSource, log

BASE = "https://www.fia.com"
DOCS = BASE + "/documents/championships/fia-formula-one-world-championship-14"
HEADERS = {"User-Agent": "Mozilla/5.0 (F1 Spejimai)"}
FIRST_SEASON = 2024          # nuo tada skelbiami „Car Presentation“ dokumentai

# Priežastis: pagrindinė kategorija arba (kai komanda jos neparašo) jos potipis
REASONS = {"performance": "performance", "local load": "performance", "flow conditioning": "performance",
           "drag reduction": "performance", "circuit": "circuit", "balance range": "circuit",
           "cooling range": "circuit", "reliability": "reliability"}
REASON_RE = re.compile(r"\b(Performance|Circuit[\s-]*specific|Reliability|Local\s+load|Flow\s+conditioning|"
                       r"Drag\s+reduction|Balance\s+range|Cooling\s+range)\b", re.I)
HEADER_END_RE = re.compile(r"max\.?\s*\d+\s*words\s*\)?", re.I)
GRID_ROW_RE = re.compile(r"^(\d{1,2})\s+(\d{1,2})\s+[A-Za-zÀ-ž]")


def _get(url):
    r = requests.get(url, headers=HEADERS, timeout=60)
    r.raise_for_status()
    return r


def _pdf_text_pages(content):
    import pypdf
    return [(p.extract_text() or "").replace("\xa0", " ") for p in pypdf.PdfReader(io.BytesIO(content)).pages]


def doc_key(url):
    """Dokumento pavadinimas palyginimui: „2024 Italian GP - Car Presentation.pdf“ -> „..._car_presentation.pdf“."""
    return unquote(url.rsplit("/", 1)[-1]).lower().replace(" ", "_")


def _clean(s):
    return re.sub(r"\s+", " ", s).strip(" -–")


# ------------------------------------------------------------------ dokumentų apdorojimas (be tinklo – testuojama)

def parse_car_presentation(pages):
    """pages – PDF puslapių tekstai. Grąžina [{team, page, nr, component, reason, description}]
    (page – komandos puslapio numeris PDF'e, nuorodai „#page=N“);
    komanda be atnaujinimų – viena eilutė su nr=0 ir component=None."""
    blocks, cur = [], None
    for page_no, text in enumerate(pages[1:], 2):     # 1 puslapis – FIA viršelis
        lines = [ln.strip() for ln in text.splitlines()]
        head = next((i for i, ln in enumerate(lines) if ln.lower().startswith("car presentation")), None)
        if head is not None:
            rest = [ln for ln in lines[head + 1:]]
            team_i = next((i for i, ln in enumerate(rest) if ln), None)
            if team_i is None:
                continue
            cur = {"team": rest[team_i].strip("* "), "page": page_no, "lines": rest[team_i + 1:]}
            blocks.append(cur)
        elif cur:
            cur["lines"] += lines
    rows = []
    for b in blocks:
        body = "\n".join(b["lines"])
        m = HEADER_END_RE.search(body)
        items = _split_items(body[m.end():]) if m else []
        if not items:
            rows.append(dict(team=b["team"], page=b["page"], nr=0, component=None, reason=None, description=None))
            continue
        for nr, text in items:
            text = _clean(text)
            r = REASON_RE.search(text)
            if r:
                component, reason, rest = text[:r.start()], re.sub(r"\s+", " ", r.group(1).lower()), text[r.end():]
                reason = next(v for k, v in REASONS.items() if reason.startswith(k))
            else:
                component, reason, rest = text, None, ""
            rows.append(dict(team=b["team"], page=b["page"], nr=nr, component=_clean(component)[:120] or None, reason=reason,
                             description=_clean(rest)[:1500] or None))
    return rows


def _split_items(body):
    """Lentelės eilutės prasideda numeriu 1, 2, 3...; imami tik iš eilės einantys numeriai
    (kad skaičiai aprašymuose nebūtų palaikyti nauja eilute)."""
    items, expected, start = [], 1, None
    for m in re.finditer(r"(?m)^\s*(\d{1,2})\s+(?=\S)", body):
        if int(m.group(1)) != expected:
            continue
        if start is not None:
            items.append((expected - 1, body[start:m.start()]))
        start, expected = m.end(), expected + 1
    if start is not None:
        items.append((expected - 1, body[start:]))
    return items


def _is_int(s, lo=1, hi=99):
    return s.isdigit() and lo <= int(s) <= hi


def parse_starting_grid(pages):
    """[(vieta, automobilio numeris)] iš starto rikiuotės ar klasifikacijos dokumento. Palaikomi abu FIA
    išdėstymai: „1 3 Max VERSTAPPEN ...“ vienoje eilutėje ir (2026) vieta, numeris, vardas – atskirose eilutėse.
    Startuojantys iš boksų („PIT LANE“) – rikiuotės gale."""
    grid, pit_lane = {}, []
    for text in pages:
        lines = [ln.strip() for ln in text.splitlines()]
        in_pit = False
        for i, ln in enumerate(lines):
            if "PIT LANE" in ln.upper():
                in_pit = True
                continue
            if in_pit and ("PENALT" in ln.upper() or ln.startswith("The F")):
                in_pit = False
                break
            nxt = lines[i + 1:i + 3] + ["", ""]
            if in_pit:
                if _is_int(ln) and re.match(r"[A-Za-zÀ-ž]", nxt[0]):
                    pit_lane.append(int(ln))
                continue
            m = GRID_ROW_RE.match(ln)
            if m and 1 <= int(m.group(1)) <= 30:
                grid.setdefault(int(m.group(2)), int(m.group(1)))
            elif _is_int(ln, 1, 30) and _is_int(nxt[0]) and re.match(r"[A-Za-zÀ-ž]", nxt[1]):
                grid.setdefault(int(nxt[0]), int(ln))
    last = max(grid.values(), default=0)
    for k, num in enumerate(n for n in pit_lane if n not in grid):
        grid[num] = last + k + 1
    return sorted((pos, num) for num, pos in grid.items())


# ------------------------------------------------------------------ fia.com dokumentų sąrašai

class FiaDocuments:
    """fia.com dokumentų paieška: sezono ir etapo puslapiai -> PDF nuorodos."""

    def __init__(self):
        self._index = None

    def _load_index(self):
        if self._index is None:
            html = _get(DOCS).text
            seasons = dict((int(y), slug) for slug, y in
                           re.findall(r'value="/documents/championships/[^"]+/season/(season-(\d{4})-\d+)"', html))
            events = [unquote(e) for e in re.findall(r'value="/documents/championships/[^"]+/event/([^"]+)"', html)]
            self._index = seasons, events
        return self._index

    def event_name(self, name):
        """FastF1 etapo pavadinimas -> FIA pavadinimas (pvz. „Barcelona Grand Prix“ -> „Barcelona-Catalunya ...“)."""
        events = self._load_index()[1]
        if name in events:
            return name
        first = name.split()[0].lower()
        return next((e for e in events if e.lower().startswith(first) and "grand prix" in e.lower()), name)

    def pdfs(self, season, event_name):
        seasons = self._load_index()[0]
        if season not in seasons:
            return []
        url = f"{DOCS}/season/{seasons[season]}/event/{quote(self.event_name(event_name))}"
        try:
            html = _get(url).text
        except requests.HTTPError:
            return []
        return sorted(set(BASE + h if h.startswith("/") else h for h in re.findall(r'href="([^"]+\.pdf)"', html)))

    @staticmethod
    def pages(url):
        return _pdf_text_pages(_get(url).content)


# ------------------------------------------------------------------ šaltiniai

class _FiaSource(DataSource):
    expected_s = 6.0

    def __init__(self, db, ref, docs):
        """docs – bendra FiaDocuments rodyklė (sources.registry ją sukuria vieną visiems FIA šaltiniams)."""
        super().__init__(db, ref)
        self.docs = docs

    def _done(self, kind):
        return set(map(tuple, self.db.query("SELECT season, round FROM fia_dokumentai WHERE tipas=?", (kind,)).values))

    def _mark(self, kind, season, rnd, url):
        self.db.write("fia_dokumentai", [dict(tipas=kind, season=season, round=rnd, url=url,
                                              gauta=datetime.now(timezone.utc).isoformat(timespec="seconds"))])

    def _events(self, season, days_ahead=4):
        """Etapai, kurių savaitgalis jau prasidėjo arba prasidės per kelias dienas."""
        limit = (datetime.now(timezone.utc) + timedelta(days=days_ahead)).date().isoformat()
        return self.db.query("SELECT round, name FROM events WHERE season=? AND date <= ? ORDER BY round",
                             (season, limit))

    def _driver_numbers(self, season):
        """{automobilio numeris: vairuotojas} pagal šio sezono rezultatus."""
        r = self.db.query("SELECT number, driver FROM results WHERE season=? AND number IS NOT NULL "
                          "ORDER BY round", (season,))
        return {int(float(n)): d for n, d in zip(r.number, r.driver) if str(n).replace(".0", "").isdigit()}


class UpgradeSource(_FiaSource):
    label = "FIA bolidų atnaujinimai"

    def update(self, season):
        if season < FIRST_SEASON:
            return
        done = self._done("car_presentation")
        events = self._events(season)
        for i, (_, ev) in enumerate(events.iterrows()):
            rnd = int(ev["round"])
            self.progress(i, len(events), ev["name"])
            if (season, rnd) in done:
                continue
            url = next((u for u in self.docs.pdfs(season, ev["name"]) if "car_presentation" in doc_key(u)), None)
            if not url:
                continue
            rows = parse_car_presentation(self.docs.pages(url))
            self.db.write("atnaujinimai", [dict(season=season, round=rnd, komanda=r["team"], nr=r["nr"],
                                                detale=r["component"], priezastis=r["reason"],
                                                aprasymas=r["description"], puslapis=r["page"]) for r in rows],
                          replace_where=("season=? AND round=?", (season, rnd)))
            self._mark("car_presentation", season, rnd, url)
            log.info("FIA atnaujinimai: %s %s – %s eil.", season, ev["name"], len(rows))


class GridSource(_FiaSource):
    """Starto rikiuotė su baudomis: artėjančioms lenktynėms ir sprintams, taip pat neseniai įvykusioms,
    jei rikiuotė nebuvo surinkta laiku, o oficialiuose rezultatuose starto vietų nėra."""
    label = "FIA starto rikiuotė"
    expected_s = 15.0
    DOC_FOR = {"R": ("final_starting_grid", "provisional_starting_grid"),
               "S": ("final_sprint_grid", "provisional_sprint_grid", "final_sprint_starting_grid",
                     "provisional_sprint_starting_grid")}
    BACKFILL_DAYS = 14

    def update(self, season):
        now = datetime.now(timezone.utc)
        pending = self.db.query(
            "SELECT s.round, s.session, e.name FROM sessions s JOIN events e USING(season, round) "
            "WHERE s.season=? AND s.session IN ('R', 'S') AND s.date_utc <= ? AND (s.status NOT IN ('ok', 'fia') "
            "  OR (s.date_utc >= ? AND NOT EXISTS (SELECT 1 FROM starto_rikiuote g WHERE g.season=s.season "
            "      AND g.round=s.round AND g.session=s.session) "
            "  AND NOT EXISTS (SELECT 1 FROM results r WHERE r.season=s.season AND r.round=s.round "
            "      AND r.session=s.session AND r.grid IS NOT NULL)))",
            (season, (now + timedelta(days=2)).isoformat(), (now - timedelta(days=self.BACKFILL_DAYS)).isoformat()))
        numbers = self._driver_numbers(season)
        groups = pending.groupby(["round", "name"])
        for i, ((rnd, name), group) in enumerate(groups):
            self.progress(i, groups.ngroups, name)
            pdfs = self.docs.pdfs(season, name)
            for session in group.session:
                url = next((u for kind in self.DOC_FOR[session] for u in pdfs if kind in doc_key(u)), None)
                if not url:
                    continue
                grid = [(pos, numbers[n]) for pos, n in parse_starting_grid(self.docs.pages(url)) if n in numbers]
                if grid:
                    self.db.write("starto_rikiuote",
                                  [dict(season=season, round=int(rnd), session=session, driver=d, grid=pos,
                                        dokumentas=doc_key(url)) for pos, d in grid],
                                  replace_where=("season=? AND round=? AND session=?", (season, int(rnd), session)))
                    log.info("FIA starto rikiuotė: %s %s %s (%s vairuotojų)", season, name, session, len(grid))


class ClassificationSource(_FiaSource):
    """Atsarginis rezultatų šaltinis: FIA klasifikacija (provisional/final), kai oficialus F1 laiko archyvas
    (FastF1) dar nepaskelbtas – tai kartais užtrunka kelias valandas. Sesija pažymima būsena „fia“
    (preliminarus); kai FastF1 duomenys atsiranda, jie rezultatą perrašo."""
    label = "FIA klasifikacija"
    DOC_FOR = {"Q": ("final_qualifying_classification", "provisional_qualifying_classification"),
               "SQ": ("final_sprint_qualifying_classification", "provisional_sprint_qualifying_classification"),
               "S": ("final_sprint_classification", "provisional_sprint_classification"),
               "R": ("final_race_classification", "provisional_race_classification")}
    PAD_MIN = 5          # FIA klasifikacija paprastai paskelbiama netrukus po sesijos pabaigos

    def update(self, season):
        now = datetime.now(timezone.utc)
        pending = self.db.query(
            "SELECT s.round, s.session, s.date_utc, e.name FROM sessions s JOIN events e USING(season, round) "
            "WHERE s.season=? AND s.session IN ('SQ', 'Q', 'S', 'R') AND s.status NOT IN ('ok', 'fia') "
            "AND s.date_utc >= ?", (season, (now - timedelta(days=7)).isoformat()))
        pending = pending[[ready_at(d, c, self.PAD_MIN) <= now for d, c in zip(pending.date_utc, pending.session)]]
        numbers, teams = self._driver_numbers(season), self._teams(season)
        groups = pending.groupby(["round", "name"])
        for i, ((rnd, name), group) in enumerate(groups):
            self.progress(i, groups.ngroups, name)
            pdfs = self.docs.pdfs(season, name)
            for session in group.session:
                url = next((u for kind in self.DOC_FOR[session] for u in pdfs if kind in doc_key(u)), None)
                if not url:
                    continue
                rows = [dict(season=season, round=int(rnd), session=session, driver=numbers[n], number=str(n),
                             team=teams.get(numbers[n]), position=pos, official_position=pos,
                             status="Finished" if session in ("R", "S") else None)
                        for pos, n in parse_starting_grid(self.docs.pages(url)) if n in numbers]
                if len(rows) < 3:
                    continue
                self.db.write("results", rows, replace_where=("season=? AND round=? AND session=?",
                                                              (season, int(rnd), session)))
                self.db.execute("UPDATE sessions SET status='fia', loaded_at=? WHERE season=? AND round=? AND session=?",
                                (now.isoformat(), season, int(rnd), session))
                log.info("FIA klasifikacija (preliminari): %s %s %s – %s vairuotojų", season, name, session, len(rows))

    def _teams(self, season):
        r = self.db.query("SELECT driver, team FROM results WHERE season=? ORDER BY round", (season,))
        return dict(zip(r.driver, r.team))
