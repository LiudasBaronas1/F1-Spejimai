"""Automatinis spėjimas prieš kiekvieną sesiją (Windows užduotis kas 15 min. -> `cli.py automatinis`).

Jei per artimiausias BEFORE_MIN minučių prasideda sesija ir jai dar nebuvo spėjimo – atnaujina visus
šaltinius, paruošia ir išsaugo spėjimą bei parodo pranešimą (`notify` – keičiama priklausomybė).
"""
import logging
import subprocess
from datetime import datetime, timedelta, timezone

from . import model
from .config import COMPETITIVE, SEASON, SESSION_NAMES_LT
from .dataset import kind_of

BEFORE_MIN = 40
log = logging.getLogger("f1")


def windows_toast(title, text):
    """Windows pranešimas (toast) per PowerShell – be papildomų programų."""
    t, x = (s.replace("'", "’") for s in (title, text))
    ps = ("[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType=WindowsRuntime] | Out-Null;"
          "$x = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02);"
          f"$x.GetElementsByTagName('text')[0].AppendChild($x.CreateTextNode('{t}')) | Out-Null;"
          f"$x.GetElementsByTagName('text')[1].AppendChild($x.CreateTextNode('{x}')) | Out-Null;"
          "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("
          "'{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\\WindowsPowerShell\\v1.0\\powershell.exe')"
          ".Show([Windows.UI.Notifications.ToastNotification]::new($x))")
    subprocess.run(["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps],
                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), timeout=60)


def due_sessions(db, now=None):
    """Artėjančios sesijos, kurioms dar nėra šviežio spėjimo."""
    now = now or datetime.now(timezone.utc)
    s = db.query("SELECT s.round, s.session, s.date_utc, e.name FROM sessions s JOIN events e USING(season, round) "
                 "WHERE s.season=? AND s.status NOT IN ('ok', 'fia') AND s.date_utc > ? AND s.date_utc <= ?",
                 (SEASON, now.isoformat(), (now + timedelta(minutes=BEFORE_MIN)).isoformat()))
    fresh = (now - timedelta(minutes=BEFORE_MIN + 20)).isoformat()
    return [r for _, r in s[s.session.isin(COMPETITIVE)].iterrows()
            if db.query("SELECT COUNT(*) n FROM predictions WHERE season=? AND round=? AND session=? AND created_at>=?",
                        (SEASON, int(r["round"]), r.session, fresh)).n.iloc[0] == 0]


def run(app, due=None, notify=windows_toast):
    due = due_sessions(app.db) if due is None else due
    if not due:
        return
    app.update(SEASON)
    data = app.dataset()
    fitted = model.fit_all(data)
    for r in due:
        rnd, session = int(r["round"]), r.session
        out = model.predict(data, SEASON, rnd, session, weights=fitted[kind_of(session)][0])
        model.save_prediction(app.db, SEASON, rnd, session, out)
        ev = data.event(SEASON, rnd)
        app.write_report(data, fitted, last=(ev["name"], session, out, ev.circuit))
        start = datetime.fromisoformat(r.date_utc).astimezone().strftime("%H:%M")
        msg = f"{' – '.join(out['pick'])}  (tikėtini taškai {out['expected']:.1f}, lietus {out['rain']:.0%}, pradžia {start})"
        log.info("%s %s: %s", r["name"], session, msg)
        try:
            notify(f"F1: {r['name'].replace(' Grand Prix', '')} – {SESSION_NAMES_LT[session]}", msg)
        except Exception as e:
            log.warning("Pranešimo parodyti nepavyko: %s", e)
