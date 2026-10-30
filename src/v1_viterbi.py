"""v1: evidencia de control + detección de balón muerto + segmentación con Viterbi.

Uso, desde la raíz de CDS-Tech:
    export MTAH_DATA_DIR="$PWD/dataset"
    python src/v1_viterbi.py            # escribe outputs/v1_viterbi.csv
    python mtah/evaluation/run_evaluation.py --results outputs --out eval

Qué cambia respecto al baseline
-------------------------------
1. Control, no cercanía: un frame solo aporta evidencia para un equipo si el balón está
   visible, no va rápido (no es un pase en vuelo) y hay un jugador a menos de
   CONTROL_RADIUS_M. Si nadie está cerca, el frame no opina.
2. Balón muerto con señales propias, no "no veo el balón":
   - balón fuera del campo;
   - jugadores casi parados (velocidad media de todos los jugadores, suavizada), que es lo
     que pasa en las paradas y está disponible aunque falte el balón;
   - antes del saque inicial de cada parte (frames publicados en FAQ.md).
3. Viterbi con tres estados (H, A, D) en lugar de voto por ventana. Cambiar de estado
   tiene un coste fijo, así que solo hay cambio de posesión si la evidencia contraria
   acumulada lo supera (~1 s de control rival). Un toque o un desvío no bastan, que es
   lo que pide la definición de "posesión controlada". Y el corte se coloca donde empieza
   la evidencia, no en el centro de una ventana.

Los parámetros están fijados a priori con criterio futbolístico y NO se han ajustado contra
los 5 minutos públicos (17 posesiones no permiten elegir parámetros; ver EVALUATION.md).

La primera ejecución lee el ATD (uno o dos minutos) y guarda los rasgos en cache/
(añadid cache/ al .gitignore: es derivado de los datos y no se publica).
"""
import argparse
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "mtah"))
sys.path.insert(0, str(ROOT / "mtah" / "starter"))

from games import GAME, GAMES, half_video_blocks, require, source_frames  # noqa: E402
from baseline import team_of_each_track, write_submission  # noqa: E402

# ---------------------------------------------------------------- parámetros (a priori)
CONTROL_RADIUS_M = 2.0        # jugador a menos de esto del balón = posible control
CONTROL_MARGIN_M = 0.0        # el rival más cercano debe estar al menos esto más lejos
MAX_CONTROL_BALL_SPEED = 12.0 # m/s; por encima, el balón va en un pase o tiro
OUT_MARGIN_M = 1.0            # tolerancia antes de considerar el balón fuera
DEAD_SPEED_MS = 1.4           # velocidad media de jugadores típica de una parada
DEAD_SPEED_SCALE = 0.25       # suavidad de la transición alrededor de ese umbral
SPEED_SMOOTH_HALF = 50        # ventana ±2 s para suavizar la velocidad media
SWITCH_TEAM_COST = 25.0       # ~1 s de control rival neto para cambiar de posesión
SWITCH_DEAD_COST = 50.0       # ~2 s de evidencia para entrar o salir de balón muerto
KICKOFF_FRAMES = (11185, 113742)  # saque inicial de cada parte (FAQ.md / DATA.md)

BIG = 1e9
STATES = np.array(["H", "A", "D"])
CACHE = ROOT / "cache" / "atd_features.npz"
FEATURES = ("bx", "by", "bv", "d_home", "d_away", "mean_speed")


# ---------------------------------------------------------------- lectura del ATD
def parse_features(meta_path, raw_path, n_frames, pitch):
    """Rasgos por frame: balón (m, m/s), distancia al jugador más cercano de cada equipo
    y velocidad media de los jugadores. NaN donde no hay observación."""
    team = team_of_each_track(meta_path)
    length, width = pitch
    f = {k: np.full(n_frames, np.nan, dtype=np.float32) for k in FEATURES}

    with open(raw_path) as handle:
        for line in handle:
            parts = line.rstrip("\n").split(":")
            if len(parts) != 3:
                continue
            i = int(parts[0]) - 1  # frame_id empieza en 1, la entrega en 0
            if not 0 <= i < n_frames:
                continue

            players, speeds = [], []
            for slot, group in enumerate(parts[1].split(";")):
                if not group or group[0] == "N" or slot >= len(team):
                    continue
                v = group.split(",")
                players.append((float(v[0]) * length, float(v[1]) * width, team[slot]))
                if len(v) > 2 and v[2] and v[2][0] != "N":
                    speeds.append(float(v[2]))
            if speeds:
                f["mean_speed"][i] = sum(speeds) / len(speeds)

            ball = parts[2].strip()
            if not ball or ball[0] == "N":
                continue
            v = ball.split(",")
            bx, by = float(v[0]) * length, float(v[1]) * width
            f["bx"][i], f["by"][i] = bx, by
            if len(v) > 2 and v[2] and v[2][0] != "N":
                f["bv"][i] = float(v[2])

            d_home = d_away = math.inf
            for x, y, t in players:
                d = math.hypot(x - bx, y - by)
                if t == 0:
                    d_home = min(d_home, d)
                else:
                    d_away = min(d_away, d)
            if d_home < math.inf:
                f["d_home"][i] = d_home
            if d_away < math.inf:
                f["d_away"][i] = d_away
    return f


def load_features(use_cache=True):
    if use_cache and CACHE.exists():
        data = np.load(CACHE)
        return {k: data[k] for k in FEATURES}
    meta_path, raw_path = require(["atd_meta", "atd_raw"], GAME, None)
    print("leyendo el ATD (solo la primera vez) ...")
    f = parse_features(meta_path, raw_path, source_frames("tactical", GAME),
                       GAMES[GAME]["pitch"])
    CACHE.parent.mkdir(exist_ok=True)
    np.savez(CACHE, **f)
    return f


# ---------------------------------------------------------------- evidencias
def rolling_nanmean(x, half):
    valid = ~np.isnan(x)
    cs = np.concatenate(([0.0], np.cumsum(np.where(valid, x, 0.0))))
    cn = np.concatenate(([0], np.cumsum(valid)))
    idx = np.arange(len(x))
    lo, hi = np.maximum(0, idx - half), np.minimum(len(x), idx + half + 1)
    n = cn[hi] - cn[lo]
    out = np.full(len(x), np.nan)
    out[n > 0] = (cs[hi] - cs[lo])[n > 0] / n[n > 0]
    return out


def control_evidence(f, radius=CONTROL_RADIUS_M, margin=CONTROL_MARGIN_M):
    """(eH, eA): 1 en los frames donde un jugador de ese equipo parece controlar el balón."""
    d_home = np.where(np.isnan(f["d_home"]), np.inf, f["d_home"])
    d_away = np.where(np.isnan(f["d_away"]), np.inf, f["d_away"])
    nearest = np.minimum(d_home, d_away)
    fast = np.nan_to_num(f["bv"], nan=0.0) > MAX_CONTROL_BALL_SPEED
    ok = ~np.isnan(f["bx"]) & (nearest <= radius) & ~fast
    # con margin > 0, un balón disputado (rival casi igual de cerca) no cuenta para nadie
    e_home = (ok & (d_home + margin <= d_away)).astype(float)
    e_away = (ok & (d_away + margin < d_home)).astype(float)
    return e_home, e_away


def deadness(f, pitch):
    """Entre 0 (juego vivo) y 1 (parada), a partir de balón fuera y jugadores parados."""
    length, width = pitch
    speed = rolling_nanmean(f["mean_speed"], SPEED_SMOOTH_HALF)
    by_speed = 1.0 / (1.0 + np.exp((speed - DEAD_SPEED_MS) / DEAD_SPEED_SCALE))
    by_speed = np.where(np.isnan(by_speed), 0.5, by_speed)

    bx, by = f["bx"], f["by"]
    with np.errstate(invalid="ignore"):
        out = ((bx < -OUT_MARGIN_M) | (bx > length + OUT_MARGIN_M) |
               (by < -OUT_MARGIN_M) | (by > width + OUT_MARGIN_M))
    return np.maximum(by_speed, out.astype(float)), speed, out


# ---------------------------------------------------------------- segmentación
def transition_matrix(team_cost=SWITCH_TEAM_COST, dead_cost=SWITCH_DEAD_COST):
    return np.array([
        [0.0, team_cost, dead_cost],
        [team_cost, 0.0, dead_cost],
        [dead_cost, dead_cost, 0.0],
    ])


def viterbi(cost, transition):
    """Camino de coste mínimo: suma de costes por frame más costes de cambio de estado."""
    n, k = cost.shape
    back = np.zeros((n, k), dtype=np.int8)
    acc = cost[0].copy()
    for t in range(1, n):
        cand = acc[:, None] + transition
        back[t] = cand.argmin(axis=0)
        acc = cand.min(axis=0) + cost[t]
    path = np.empty(n, dtype=np.int8)
    path[-1] = acc.argmin()
    for t in range(n - 1, 0, -1):
        path[t - 1] = back[t, path[t]]
    return path


def segment(e_home, e_away, dead, n_frames, transition=None):
    transition = transition_matrix() if transition is None else transition
    labels = np.full(n_frames, "X", dtype="<U1")
    for half, first, last in half_video_blocks(GAME):
        sl = slice(first, last + 1)
        cost = np.stack([
            e_away[sl] + dead[sl],   # H: le cuesta ver control rival o señales de parada
            e_home[sl] + dead[sl],   # A: idem
            1.0 - dead[sl],          # D: le cuesta ver juego vivo
        ], axis=1)
        kickoff = KICKOFF_FRAMES[half - 1]
        if kickoff > first:
            cost[: kickoff - first, :2] = BIG  # antes del saque inicial solo cabe D
        labels[sl] = STATES[viterbi(cost, transition)]
    return labels


# ---------------------------------------------------------------- resumen (solo agregados)
def describe(labels, f, e_home, e_away, speed, out):
    graded = labels != "X"
    pct = lambda m: 100.0 * np.mean(m[graded])  # noqa: E731
    s = speed[graded & ~np.isnan(speed)]
    print("velocidad media jugadores (puntuados)  p10 {:.2f}  p50 {:.2f}  p90 {:.2f} m/s".format(
        *np.percentile(s, [10, 50, 90])))
    print("frames con evidencia de control  {:.1f}%".format(pct((e_home + e_away) > 0)))
    print("frames con balón fuera del campo {:.1f}%".format(pct(out)))

    runs, lengths = 0, []
    for _, first, last in half_video_blocks(GAME):
        seq = labels[first:last + 1]
        start = 0
        for t in range(1, len(seq) + 1):
            if t == len(seq) or seq[t] != seq[start]:
                if seq[start] in "HA":
                    runs += 1
                    lengths.append(t - start)
                start = t
    counts = {s: int(np.sum(labels == s)) for s in "HAD"}
    print("predicción  H {H}  A {A}  D {D}".format(**counts))
    print("posesiones  {}  duración media {:.1f} s".format(runs, np.mean(lengths) / 25.0))


def main():
    parser = argparse.ArgumentParser(description="v1: control + balón muerto + Viterbi")
    parser.add_argument("--no-cache", action="store_true", help="releer el ATD")
    parser.add_argument("--switch-team", type=float, default=SWITCH_TEAM_COST)
    parser.add_argument("--switch-dead", type=float, default=SWITCH_DEAD_COST)
    parser.add_argument("--radius", type=float, default=CONTROL_RADIUS_M)
    parser.add_argument("--margin", type=float, default=CONTROL_MARGIN_M)
    parser.add_argument("--name", default="v1_viterbi", help="nombre del CSV en outputs/")
    args = parser.parse_args()

    f = load_features(use_cache=not args.no_cache)
    n_frames = len(f["bx"])
    e_home, e_away = control_evidence(f, args.radius, args.margin)
    dead, speed, out = deadness(f, GAMES[GAME]["pitch"])
    labels = segment(e_home, e_away, dead, n_frames,
                     transition_matrix(args.switch_team, args.switch_dead))

    describe(labels, f, e_home, e_away, speed, out)
    dest = ROOT / "outputs" / "{}.csv".format(args.name)
    write_submission(str(dest), labels)
    print("escrito:", dest.relative_to(ROOT))


if __name__ == "__main__":
    main()
