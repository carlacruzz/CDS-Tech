"""Possession v1: confirm control below one metre; retain the last controlling team.

From the repository root (data in the parent folder):
    python starter/possession_v1.py --data-dir ..

This version deliberately has no dead-ball detector or temporal smoothing.
Far observations preserve the last team until another close control. A frame where the
system does not detect the ball is labelled D (the remembered team is kept for afterwards).
Two-teammate change: a rival's control under one metre only changes possession once a
different player of that team also controls the ball next, or once that same player
keeps it under one metre for more than one second; the change then starts at the first
player's control. For the pass, both controls must be real touches: if the ball keeps its
direction and changes speed only in proportion while it is within a metre of the player,
it went past him and that control does not count. Goalkeeper veto: a change is not made when the rival who would win the ball is nearer
the centre of the goal the current team defends than that team's goalkeeper.
Dead ball behind the goalkeeper: while the ball is outside the pitch (a slow ball on the pitch is
still in play), a control by a player inside the rival's penalty area and nearer that goal line
than the rival goalkeeper is ignored (it is not possession for anybody; e.g. the ball in the net
after a goal).
Memory resets between halves. Ungraded frames and uninitialised halves are X.
"""
import argparse
import csv
import json
import math
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from games import GAME, GAMES, half_video_blocks, require, source_frames
from starter.baseline import team_of_each_track

BOX_DEPTH, BOX_WIDTH = 16.5, 40.3  # penalty area, metres
# Touch test. The ATD ball path is smoothed, so a kick shows as a ramp over several
# frames: compare the ball's velocity over TOUCH_WINDOW frames before the contact starts
# with the one over TOUCH_WINDOW frames after it ends.
TOUCH_WINDOW = 8          # frames (0.32 s)
TOUCH_ANGLE = 30.0        # degrees of direction change that mean a touch
TOUCH_SPEED_RATIO = 1.5   # speed multiplied or divided by more than this means a touch
TOUCH_MIN_SPEED = 1.0     # m/s; slower than this a direction is noise and speeds are floored


class PossessionTracker:
    def __init__(self, threshold=1.0, hold_frames=25):
        if not math.isfinite(threshold) or threshold <= 0:
            raise ValueError('threshold must be finite and positive')
        self.threshold = threshold
        self.hold_frames = hold_frames  # a held control must last longer than this (1 s at 25 fps)
        self.reset()

    def reset(self):
        self.team = None
        self.track = None
        self.last_control = None
        self.pending = None   # (team, track, frame) of a rival's first control, awaiting confirmation
        self.pending_touched = False  # whether that first player really touched the ball
        self.held_since = None  # start of the pending player's current uninterrupted control
        self.backfill = None  # set by update(): first frame to relabel after a confirmed change

    def _change(self, team, track, frame):
        self.backfill = self.pending[2]
        self.team, self.track, self.last_control = team, track, frame
        self.pending = self.held_since = None

    def update(self, frame, team=None, track=None, distance=None, goal_distance=None, keeper_distance=None,
               touch=None, ignored=False):
        """Nearest observed player; absent/invalid observations never imply D.

        goal_distance: that player's distance to the goal defended by the other team.
        keeper_distance: the other team's goalkeeper's distance to that same goal.
        touch: False when the ball went past this player without changing its course
        (see contact_touches); True or None (unknown) count as a touch.
        ignored: True when the ball is outside the pitch and this player is in the rival's penalty area
        behind its goalkeeper; the control then counts as nobody's (like no contact).

        A rival's control under the threshold only changes possession when either the next
        control is by a different player of that team (a pass, both controls being real
        touches), or that same player keeps
        the ball under the threshold for longer than hold_frames. Frames without a ball or
        player observation do not interrupt the hold; a frame with the ball observed and
        nobody under the threshold does. The change starts at the first player's control
        frame, given back in self.backfill.

        A frame without a ball observation is labelled D; the remembered team and any pending
        change are kept for when the ball reappears.
        """
        self.backfill = None
        observed = distance is not None and math.isfinite(distance)
        confirmed = (team in (0, 1) and observed and 0 <= distance < self.threshold)
        ignored = confirmed and ignored
        if ignored:
            confirmed = False
        behind_keeper = (confirmed and self.team is not None and team != self.team
                         and goal_distance is not None and keeper_distance is not None
                         and goal_distance < keeper_distance)
        if not observed:
            return 'D', 'balon_no_detectado'
        if behind_keeper:
            self.held_since = None
            reason = 'cambio_bloqueado_portero'
        elif confirmed and self.team is not None and team != self.team:
            real = touch is not False
            if self.pending and self.pending[0] == team and self.pending[1] != track:
                if real and self.pending_touched:
                    self._change(team, track, frame)
                    reason = 'cambio_equipo'
                elif real:
                    # the first player only let the ball go past: this one is the first touch
                    self.pending, self.pending_touched, self.held_since = (team, track, frame), True, frame
                    reason = 'cambio_pendiente'
                else:
                    self.held_since = None
                    reason = 'cambio_pendiente_sin_toque'
            else:
                if not (self.pending and self.pending[0] == team):
                    self.pending, self.pending_touched = (team, track, frame), False
                self.pending_touched = self.pending_touched or real
                if self.held_since is None:
                    self.held_since = frame
                if frame - self.held_since + 1 > self.hold_frames:
                    self._change(team, track, frame)
                    reason = 'cambio_por_control'
                else:
                    reason = 'cambio_pendiente'
        elif confirmed:
            reason = 'primer_control' if self.team is None else 'control_confirmado'
            self.team, self.track, self.last_control = team, track, frame
            self.pending = self.held_since = None
        else:
            self.held_since = None
            reason = ('control_ignorado_tras_portero' if ignored else
                      'sin_control_inicial' if self.team is None else 'mantener_sin_contacto')
        return ('X' if self.team is None else 'H' if self.team == 0 else 'A'), reason


def defended_goals(meta_path):
    """Goal x (0 or 1) each team defends in the first half; teams swap ends in the second."""
    teams = ET.parse(meta_path).getroot().iter('Team')
    return [int(t.find(".//ProviderParameter[Name='attack_direction_first_half']/Value").text
                != 'left_to_right') for t in teams]


def in_box(px, py, goal_x, pitch):
    """Whether normalised (px, py) is inside the penalty area of the goal at x = goal_x."""
    length, width = pitch
    y0, y1 = (width - BOX_WIDTH) / 2 / width, (width + BOX_WIDTH) / 2 / width
    return y0 <= py <= y1 and (px <= BOX_DEPTH / length if goal_x == 0 else px >= 1 - BOX_DEPTH / length)


def keepers(players, team_by_slot, goal, pitch):
    """Per team, (distance in metres to the centre of the goal it defends, (px, py)) of its goalkeeper.

    Goalkeeper: the team's only track inside its own penalty area; with several, the one
    nearest the goal centre. None when no track of the team is in that area.
    """
    length, width = pitch
    out = [None, None]
    for slot, (px, py) in players:
        t = int(team_by_slot[slot])
        if not in_box(px, py, goal[t], pitch):
            continue
        d = math.hypot((px - goal[t]) * length, (py - .5) * width)
        if out[t] is None or d < out[t][0]:
            out[t] = (d, (px, py))
    return out


def keeper_distances(players, team_by_slot, goal, pitch):
    """Per team, its goalkeeper's distance in metres to the centre of the goal it defends (see keepers)."""
    return [None if k is None else k[0] for k in keepers(players, team_by_slot, goal, pitch)]


def nearest_observations(path, team_by_slot, pitch, goals=None):
    """Stream complete frame ids and nearest finite 2D observation, in metres.

    goals(frame) -> goal x each team defends. When given, also yields the nearest player's
    distance to the goal the other team defends and that team's goalkeeper's distance to it,
    and whether that player is inside the other team's penalty area nearer its goal line than
    its goalkeeper (behind_keeper; False without a goalkeeper in the area).
    """
    length, width = pitch
    expected_frame = 0
    with open(path, encoding='utf-8') as handle:
        for line in handle:
            parts = line.rstrip().split(':')
            if len(parts) != 3:
                raise ValueError(f'Malformed ATD record {expected_frame + 1}')
            frame = int(parts[0]) - 1
            if frame != expected_frame:
                raise ValueError(f'Expected video frame {expected_frame}, got {frame}')
            expected_frame += 1
            bx, by = map(float, parts[2].split(',')[:2])
            nearest_slot = nearest_team = distance = goal_distance = keeper_distance = None
            behind_keeper = False
            if math.isfinite(bx) and math.isfinite(by):
                groups = parts[1].split(';')
                if len(groups) != len(team_by_slot):
                    raise ValueError(f'Track count mismatch at frame {frame}')
                best_squared = math.inf
                players = []
                for slot, group in enumerate(groups):
                    px, py = map(float, group.split(',')[:2])
                    if not (math.isfinite(px) and math.isfinite(py)):
                        continue
                    players.append((slot, (px, py)))
                    dsq = ((px - bx) * length) ** 2 + ((py - by) * width) ** 2
                    if dsq < best_squared:
                        best_squared = dsq
                        nearest_slot, nearest_team, nearest_xy = slot + 1, int(team_by_slot[slot]), (px, py)
                if nearest_slot is not None:
                    distance = math.sqrt(best_squared)
                    if goals is not None:
                        goal, other = goals(frame), 1 - nearest_team
                        px, py = nearest_xy
                        goal_distance = math.hypot((px - goal[other]) * length, (py - .5) * width)
                        keeper = keepers(players, team_by_slot, goal, pitch)[other]
                        if keeper is not None:
                            keeper_distance, (kx, _) = keeper
                            behind_keeper = (in_box(px, py, goal[other], pitch)
                                             and abs(px - goal[other]) < abs(kx - goal[other]))
            ball = (bx * length, by * width) if math.isfinite(bx) and math.isfinite(by) else None
            yield frame, nearest_team, nearest_slot, distance, goal_distance, keeper_distance, ball, behind_keeper


def contact_touches(observations, threshold, window=TOUCH_WINDOW, fps=25):
    """Per frame, whether the nearest player under the threshold really touched the ball.

    A contact is a run of frames with the same nearest track under the threshold. Its
    ball velocity over `window` frames before the run is compared with the one over
    `window` frames after it: a direction change above TOUCH_ANGLE, or a speed change
    above TOUCH_SPEED_RATIO either way, is a touch; otherwise the ball went past. None
    when the ball is missing at the ends of those windows. Frames outside a contact are None.
    """
    ball = [o[6] for o in observations]
    out = [None] * len(observations)

    def velocity(a, b):
        if a < 0 or b >= len(ball) or ball[a] is None or ball[b] is None:
            return None
        return ((ball[b][0] - ball[a][0]) * fps / (b - a), (ball[b][1] - ball[a][1]) * fps / (b - a))

    frame = 0
    while frame < len(observations):
        track, distance = observations[frame][2], observations[frame][3]
        if track is None or distance is None or not distance < threshold:
            frame += 1
            continue
        end = frame
        while (end + 1 < len(observations) and observations[end + 1][2] == track
               and observations[end + 1][3] is not None and observations[end + 1][3] < threshold):
            end += 1
        before, after = velocity(frame - window, frame), velocity(end, end + window)
        touched = None
        if before and after:
            s0, s1 = math.hypot(*before), math.hypot(*after)
            turned = False
            if min(s0, s1) >= TOUCH_MIN_SPEED:
                cos = (before[0] * after[0] + before[1] * after[1]) / (s0 * s1)
                turned = math.degrees(math.acos(max(-1.0, min(1.0, cos)))) > TOUCH_ANGLE
            ratio = max(s0, s1, TOUCH_MIN_SPEED) / max(min(s0, s1), TOUCH_MIN_SPEED)
            touched = turned or ratio > TOUCH_SPEED_RATIO
        out[frame:end + 1] = [touched] * (end - frame + 1)
        frame = end + 1
    return out


def ball_out(observations, pitch):
    """Per frame, whether the ball is outside the pitch (beyond a goal line or touchline).

    Speed plays no part: a ball slowing down on the pitch is still in play. False when missing.
    """
    length, width = pitch
    return [o[6] is not None and not (0 <= o[6][0] <= length and 0 <= o[6][1] <= width)
            for o in observations]


def generate(data_dir=None, threshold=1.0, out=None, audit=None, keeper_veto=True):
    meta, raw = require(['atd_meta', 'atd_raw'], GAME, data_dir)
    team_by_slot = team_of_each_track(meta)
    tracker = PossessionTracker(threshold)
    blocks = half_video_blocks(GAME)
    starts = {start for _, start, _ in blocks}
    first_half, second_start = defended_goals(meta), blocks[1][1]
    goals = lambda frame: first_half if frame < second_start else [1 - g for g in first_half]
    out = Path(out or ROOT/'evaluation/results/algoritmo_v1.csv')
    audit = Path(audit or ROOT/'evaluation/reports/algoritmo_v1_auditoria.csv')
    for path in (out, audit):
        path.parent.mkdir(parents=True, exist_ok=True)
    reasons = Counter()
    observations = list(nearest_observations(raw, team_by_slot, GAMES[GAME]['pitch'], goals))
    touches = contact_touches(observations, threshold)
    outs = ball_out(observations, GAMES[GAME]['pitch'])
    rows = []  # audit rows, buffered: a confirmed change relabels frames back to its first control
    for (frame, nearest_team, nearest_track, distance, goal_distance, keeper_distance, _, behind_keeper), touch, out_of_play \
            in zip(observations, touches, outs):
        if not keeper_veto:
            goal_distance = keeper_distance = None
        if frame in starts:
            tracker.reset()
        graded = any(start <= frame <= end for _, start, end in blocks)
        if graded:
            label, reason = tracker.update(frame, nearest_team, nearest_track, distance, goal_distance,
                                           keeper_distance, touch, out_of_play and behind_keeper)
            if tracker.backfill is not None:
                for row in rows[tracker.backfill:frame]:
                    if row[7] != 'balon_no_detectado':
                        row[1] = label
        else:
            tracker.reset()
            label, reason = 'X', 'fuera_evaluacion'
        rows.append([frame, label, nearest_track, '' if nearest_team is None else 'H' if nearest_team == 0 else 'A',
                     '' if distance is None else f'{distance:.8f}',
                     tracker.last_control, tracker.track, reason,
                     '' if goal_distance is None else f'{goal_distance:.8f}',
                     '' if keeper_distance is None else f'{keeper_distance:.8f}',
                     '' if touch is None else int(touch), int(out_of_play), int(behind_keeper)])
        reasons[reason] += 1
    n_frames = len(rows)
    counts = Counter(row[1] for row in rows)
    with out.open('w', newline='', encoding='utf-8') as output, audit.open('w', newline='', encoding='utf-8') as report:
        writer, debug = csv.writer(output), csv.writer(report)
        writer.writerow(['frame', 'label'])
        writer.writerows(row[:2] for row in rows)
        debug.writerow(['frame', 'label', 'nearest_track', 'nearest_team', 'nearest_distance_m',
                        'last_control_frame', 'last_control_track', 'reason',
                        'nearest_to_rival_goal_m', 'rival_keeper_to_goal_m', 'ball_touched',
                        'ball_out_of_pitch', 'nearest_behind_rival_keeper'])
        debug.writerows(rows)
    if n_frames != source_frames():
        raise ValueError(f'Expected {source_frames()} frames, got {n_frames}')
    summary = {'frames': n_frames, 'threshold_m_strictly_less_than': threshold,
               'labels': dict(counts), 'reasons': dict(reasons), 'submission': str(out),
               'audit': str(audit), 'dead_ball_detection': False, 'smoothing': False,
               'keeper_veto': keeper_veto,
               'contact_frames_touch': Counter('desconocido' if t is None else 'toque' if t else 'pasa_de_largo'
                                               for t, o in zip(touches, observations)
                                               if o[3] is not None and o[3] < threshold)}
    (audit.parent/'algoritmo_v1_resumen.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path)
    parser.add_argument('--threshold', type=float, default=1.0)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--audit', type=Path)
    parser.add_argument('--no-keeper-veto', action='store_true',
                        help='Allow a change won by a rival closer to the goal than its goalkeeper')
    args = parser.parse_args()
    print(json.dumps(generate(args.data_dir, args.threshold, args.out, args.audit,
                              not args.no_keeper_veto), indent=2))
