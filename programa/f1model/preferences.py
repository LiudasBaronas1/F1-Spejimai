"""Programos pasirinkimai (pvz. sąsajos kalba), laikomi DB lentelėje `nustatymai` (raktas -> reikšmė).
Modelio parametrai čia nelaikomi – jie parametrai.json (settings.py)."""


class Preferences:
    def __init__(self, db):
        self.db = db

    def get(self, key, default=None):
        r = self.db.query("SELECT reiksme FROM nustatymai WHERE raktas = ?", (key,))
        return r.reiksme.iloc[0] if not r.empty else default

    def set(self, key, value):
        if self.get(key) != str(value):
            self.db.write("nustatymai", [dict(raktas=key, reiksme=str(value))])
