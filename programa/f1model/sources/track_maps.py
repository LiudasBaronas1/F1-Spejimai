"""Trasų žemėlapiai: kontūras iš greičiausio kvalifikacijos rato padėties duomenų (FastF1) ir posūkiai.

Kiekvienai trasai tai daroma VIENĄ kartą. Didelė telemetrijos talpykla kuriama laikiname aplanke ir
iškart ištrinama – DB lieka tik ~250 taškų kontūras (trasu_konturai). Posūkiai imami iš FastF1
trasų informacijos; jei jos nėra (naujos trasos) – randami pagal kontūro kreivumą.
"""
import json
import shutil
import tempfile

import numpy as np

from . import DataSource, log

N_POINTS = 250


def _rotate(xy, degrees):
    a = np.radians(degrees)
    return xy @ np.array([[np.cos(a), np.sin(a)], [-np.sin(a), np.cos(a)]])


def _pca_angle(xy):
    """Kampas, kuriuo pasukus ilgiausia trasos ašis tampa horizontali."""
    c = xy - xy.mean(axis=0)
    v = np.linalg.eigh(np.cov(c.T))[1][:, -1]
    return np.degrees(np.arctan2(v[1], v[0]))


def _resample(xy, n):
    seg = np.r_[0, np.cumsum(np.hypot(*np.diff(xy, axis=0).T))]
    t = np.linspace(0, seg[-1], n)
    return np.column_stack([np.interp(t, seg, xy[:, 0]), np.interp(t, seg, xy[:, 1])])


def detect_corners(xy, min_turn_deg=35, min_gap=8):
    """Posūkiai pagal kryptį: kur kryptis per trumpą atkarpą pasikeičia daugiau nei min_turn_deg."""
    heading = np.unwrap(np.arctan2(*np.diff(np.vstack([xy, xy[:2]]), axis=0).T[::-1]))
    turn = np.degrees(np.abs(np.convolve(np.diff(heading), np.ones(5), mode="same")))
    corners, i = [], 0
    while i < len(turn):
        if turn[i] > min_turn_deg:
            j = i
            while j < len(turn) and turn[j] > min_turn_deg:
                j += 1
            k = i + int(np.argmax(turn[i:j]))
            if not corners or k - corners[-1] >= min_gap:
                corners.append(k)
            i = j
        i += 1
    return corners


def normalise(xy):
    xy = xy - xy.min(axis=0)
    return xy / xy.max()


def outline(session):
    """(kontūras, posūkiai[(nr, x, y)]) normalizuotose koordinatėse 0..1."""
    xy = session.laps.pick_fastest().get_pos_data()[["X", "Y"]].to_numpy(float)
    info = None
    try:
        info = session.get_circuit_info()
    except Exception:
        pass
    angle = info.rotation if info is not None else -_pca_angle(xy)
    pts = _resample(_rotate(xy, angle), N_POINTS)
    lo, scale = pts.min(axis=0), (pts - pts.min(axis=0)).max()
    pts = (pts - lo) / scale
    if info is not None and len(info.corners):
        c = (_rotate(info.corners[["X", "Y"]].to_numpy(float), angle) - lo) / scale
        corners = [(f"{int(n)}{l or ''}", float(x), float(y)) for n, l, (x, y) in
                   zip(info.corners.Number, info.corners.Letter, c)]
    else:
        corners = [(str(i + 1), float(pts[k, 0]), float(pts[k, 1])) for i, k in enumerate(detect_corners(pts))]
    return pts.round(4).tolist(), corners


class TrackMapSource(DataSource):
    label = "trasų žemėlapiai"

    def update(self, season):
        import fastf1
        have = set(self.db.query("SELECT trasa FROM trasu_konturai").trasa)
        sessions = self.db.query(
            "SELECT s.season, s.round, e.location FROM sessions s JOIN events e USING(season, round) "
            "WHERE s.session='Q' AND s.status='ok' ORDER BY s.date_utc DESC")
        todo = {}
        for _, r in sessions.iterrows():  # naujausia kvalifikacija kiekvienai trūkstamai trasai
            circ = self.ref.tracks.circuit(r.location)
            if circ not in have and circ not in todo:
                todo[circ] = (int(r.season), int(r["round"]))
        if not todo:
            return
        tmp = tempfile.mkdtemp(prefix="f1_konturai_")
        try:
            fastf1.Cache.enable_cache(tmp, use_requests_cache=False)
            for circ, (yr, rnd) in todo.items():
                try:
                    s = fastf1.get_session(yr, rnd, "Q")
                    s.load(laps=True, telemetry=True, weather=False, messages=False)
                    pts, corners = outline(s)
                except Exception as e:
                    log.warning("Trasos kontūras %s: %s", circ, e)
                    continue
                self.db.write("trasu_konturai", [dict(trasa=circ, taskai=json.dumps(pts), posukiai=json.dumps(corners),
                                                      sezonas=yr, etapas=rnd)])
                log.info("Trasos kontūras: %s (%s posūkiai)", circ, len(corners))
        finally:
            from ..config import CACHE_DIR
            fastf1.Cache.enable_cache(str(CACHE_DIR), use_requests_cache=False)  # grąžiname įprastą talpyklą
            shutil.rmtree(tmp, ignore_errors=True)
