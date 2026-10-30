"""Automatic detection of suspicious ATD tracker behaviour, for review in the video.

Four situations, all with physical thresholds that apply to every frame alike (no
frame-specific rules), restricted to the graded halves:

  salto      a track moves faster than a human can run between two consecutive frames
  aparicion  a track starts inside the pitch, not out of another player's occlusion, and
             with no track (of either team: team labels flip) lost nearby just before it
  corta      a track lives less than one second before vanishing again
  exceso     a team has more than 11 tracks on the pitch at the same time

Each event is [first_frame, last_frame, slot, team, value] in video frames; slot is -1
for exceso. value is m/s (salto), metres to the nearest other track at that moment
(aparicion), frames alive (corta) and peak track count (exceso).
"""
import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from games import half_video_blocks

LENGTH, WIDTH, FPS = 105.3, 68.0, 25
MAX_SPEED = 12.0        # m/s; elite sprint peaks are ~10-11 m/s
ORIGIN_WINDOW = 5 * FPS  # frames back to look for a lost track that could be the same person
ORIGIN_RADIUS = 3.0      # m, plus ORIGIN_SPEED for every second of gap
ORIGIN_SPEED = 8.0       # m/s; sustained running speed while out of sight
OCCLUSION = 1.0          # m; closer than this to another track it is re-emerging from behind them
EDGE = 2.0               # m from a pitch line; closer than this it is entering the field of play
MIN_LIFE = FPS           # frames; anything shorter is a flicker
MAX_PER_TEAM = 11
MERGE_GAP = 5            # frames; nearby flagged frames form one event


def runs(mask, gap=0):
    """Start and end indices of True runs, merging runs separated by <= gap frames."""
    edges = np.flatnonzero(np.diff(np.r_[0, mask.astype(np.int8), 0]))
    out = []
    for s, e in zip(edges[::2], edges[1::2] - 1):
        if out and s - out[-1][1] - 1 <= gap:
            out[-1][1] = e
        else:
            out.append([s, e])
    return out


def detect(values, team, game='BAR-ATH'):
    """values: (frames, 3 * (slots + 1)) raw ATD rows; team: 0/1 per slot."""
    n = len(team)
    x, y = values[:, 0:n * 3:3] * LENGTH, values[:, 1:n * 3:3] * WIDTH
    present = np.isfinite(x) & np.isfinite(y)
    graded = np.zeros(len(values), bool)
    for _, first, last in half_video_blocks(game):
        graded[first:last + 1] = True
    events = {'salto': [], 'aparicion': [], 'corta': [], 'exceso': []}

    speed = np.hypot(np.diff(x, axis=0), np.diff(y, axis=0)) * FPS
    jump = np.zeros_like(present)
    jump[1:] = np.nan_to_num(speed) > MAX_SPEED
    jump &= graded[:, None]
    for k in range(n):
        for s, e in runs(jump[:, k], MERGE_GAP):
            events['salto'].append([s, e, k, int(team[k]), round(float(np.nanmax(speed[s - 1:e, k])), 2)])

    starts = present & ~np.r_[np.zeros((1, n), bool), present[:-1]]
    ends = present & ~np.r_[present[1:], np.zeros((1, n), bool)]
    for f, k in zip(*np.nonzero(starts & graded[:, None])):
        if f == 0 or not graded[f - 1]:
            continue
        if min(x[f, k], LENGTH - x[f, k], y[f, k], WIDTH - y[f, k]) < EDGE:
            continue
        others = present[f].copy()
        others[k] = False
        near = float(np.hypot(x[f, others] - x[f, k], y[f, others] - y[f, k]).min()) if others.any() else np.inf
        if near < OCCLUSION:
            continue
        lo = max(0, f - ORIGIN_WINDOW)
        if any(j != k and np.hypot(x[f, k] - x[g + lo, j], y[f, k] - y[g + lo, j])
               <= ORIGIN_RADIUS + ORIGIN_SPEED * (f - g - lo) / FPS
               for g, j in zip(*np.nonzero(ends[lo:f]))):
            continue
        events['aparicion'].append([int(f), int(f), int(k), int(team[k]), round(near, 2) if np.isfinite(near) else -1])

    for k in range(n):
        for s, e in runs(present[:, k]):
            if e - s + 1 < MIN_LIFE and graded[s:e + 1].all():
                events['corta'].append([s, e, k, int(team[k]), int(e - s + 1)])

    for t in (0, 1):
        count = present[:, team == t].sum(1)
        for s, e in runs((count > MAX_PER_TEAM) & graded, MERGE_GAP):
            events['exceso'].append([s, e, -1, t, int(count[s:e + 1].max())])

    for name in events:
        events[name] = sorted([int(v) if i < 4 else v for i, v in enumerate(ev)] for ev in events[name])
    return events
