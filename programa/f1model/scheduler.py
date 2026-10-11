"""Automatinio duomenų atnaujinimo grafikas: KADA atnaujinti (be jokio tinklo ar sąsajos – lengva tikrinti).

- Tarp etapų – kas `idle_min` minučių (naujienos, lažybos, prognozės keičiasi lėtai).
- Lenktynių savaitgalį (nuo paros prieš pirmą sesiją iki kelių valandų po paskutinės) – kas `weekend_min`.
- Papildomai: kai tik turėtų pasirodyti įvykusios sesijos rezultatai (`config.ready_at`), ir likus
  `PRE_SESSION_MIN` minučių iki kiekvienos spėjamos sesijos (naujausios lažybos, orai, starto rikiuotė).
Nustatymai laikomi lentelėje `nustatymai` (keičiami programos šoniniame meniu).
"""
from dataclasses import dataclass
from datetime import datetime, timedelta

from .config import COMPETITIVE, ready_at

PRE_SESSION_MIN = 45
WEEKEND_BEFORE_H, WEEKEND_AFTER_H = 24, 4
KEYS = {"enabled": "auto_atnaujinimas", "idle_min": "auto_tarp_etapu_min", "weekend_min": "auto_savaitgali_min"}


@dataclass
class AutoUpdatePolicy:
    enabled: bool = True
    idle_min: int = 180
    weekend_min: int = 20

    @classmethod
    def load(cls, prefs):
        d = cls()
        return cls(enabled=prefs.get(KEYS["enabled"], "1") == "1",
                   idle_min=int(prefs.get(KEYS["idle_min"], d.idle_min)),
                   weekend_min=int(prefs.get(KEYS["weekend_min"], d.weekend_min)))

    def save(self, prefs):
        prefs.set(KEYS["enabled"], "1" if self.enabled else "0")
        prefs.set(KEYS["idle_min"], self.idle_min)
        prefs.set(KEYS["weekend_min"], self.weekend_min)

    @staticmethod
    def in_weekend(sessions, now):
        """sessions – [(sesija, pradžia ISO UTC)]."""
        return any(datetime.fromisoformat(d) - timedelta(hours=WEEKEND_BEFORE_H) <= now
                   <= ready_at(d, s) + timedelta(hours=WEEKEND_AFTER_H) for s, d in sessions)

    def next_due(self, last_iso, sessions, now):
        """Kada kitas automatinis atnaujinimas (datetime UTC) arba None (išjungta).
        last_iso – paskutinio atnaujinimo laikas (None – dar niekada; tada iškart)."""
        if not self.enabled:
            return None
        if not last_iso:
            return now
        last = datetime.fromisoformat(last_iso)
        interval = self.weekend_min if self.in_weekend(sessions, now) else self.idle_min
        moments = [last + timedelta(minutes=interval)]
        for s, d in sessions:
            moments.append(ready_at(d, s))                       # rezultatai turėtų būti paskelbti
            if s in COMPETITIVE:
                moments.append(datetime.fromisoformat(d) - timedelta(minutes=PRE_SESSION_MIN))
        return min(m for m in moments if m > last)

    def due(self, last_iso, sessions, now):
        nxt = self.next_due(last_iso, sessions, now)
        return nxt is not None and nxt <= now
