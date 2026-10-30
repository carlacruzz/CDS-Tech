"""Línea de tiempo de los 5 minutos públicos: ground truth, predicción y evidencias.

Uso, desde la raíz de CDS-Tech:
    python src/plot_timeline.py                      # parámetros por defecto de v1
    python src/plot_timeline.py --switch-team 10     # misma vista con otro coste

Escribe eval/timeline_public.png. Es para mirarlo en local: lleva datos derivados del
tracking, así que no se sube al repo ni se comparte fuera del equipo.
"""
import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import ListedColormap  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v1_viterbi as v1  # noqa: E402

GT = v1.ROOT / "mtah" / "evaluation" / "gt" / "BAR-ATH_possession_gt_public.csv"
FIRST, LAST = 11185, 18684
CODE = {"H": 0, "A": 1, "D": 2, "X": 3}
CMAP = ListedColormap(["#2f6fd8", "#d9541e", "#9aa0a6", "#ffffff"])


def read_labels(path):
    labels = np.loadtxt(path, delimiter=",", skiprows=1, dtype=str, usecols=1)
    return np.array([CODE[x.strip().upper()] for x in labels])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--switch-team", type=float, default=v1.SWITCH_TEAM_COST)
    parser.add_argument("--switch-dead", type=float, default=v1.SWITCH_DEAD_COST)
    parser.add_argument("--radius", type=float, default=v1.CONTROL_RADIUS_M)
    parser.add_argument("--margin", type=float, default=v1.CONTROL_MARGIN_M)
    args = parser.parse_args()

    f = v1.load_features()
    n = len(f["bx"])
    e_home, e_away = v1.control_evidence(f, args.radius, args.margin)
    dead, speed, _ = v1.deadness(f, v1.GAMES[v1.GAME]["pitch"])
    pred = v1.segment(e_home, e_away, dead, n,
                      v1.transition_matrix(args.switch_team, args.switch_dead))

    sl = slice(FIRST, LAST + 1)
    t = np.arange(FIRST, LAST + 1)
    secs = (t - FIRST) / 25.0
    gt = read_labels(GT)[sl]
    pr = np.array([CODE[x] for x in pred[sl]])

    fig, ax = plt.subplots(5, 1, figsize=(18, 8), sharex=True,
                           gridspec_kw={"height_ratios": [1, 1, 1.2, 1.2, 1.2]})
    for a, row, title in ((ax[0], gt, "ground truth"), (ax[1], pr, "v1")):
        a.imshow(row[None, :], aspect="auto", cmap=CMAP, vmin=0, vmax=3,
                 extent=(secs[0], secs[-1], 0, 1), interpolation="nearest")
        a.set_yticks([])
        a.set_ylabel(title, rotation=0, ha="right", va="center")

    ax[2].fill_between(secs, 0, e_home[sl], step="mid", color="#2f6fd8", label="control H")
    ax[2].fill_between(secs, 0, -e_away[sl], step="mid", color="#d9541e", label="control A")
    ax[2].set_ylabel("control", rotation=0, ha="right", va="center")
    ax[2].legend(loc="upper right", fontsize=8)

    ball = ~np.isnan(f["bx"][sl])
    ax[3].fill_between(secs, 0, ball, step="mid", color="#5f6b7a")
    ax[3].set_ylabel("balón visible", rotation=0, ha="right", va="center")

    ax[4].plot(secs, dead[sl], color="#5f6b7a", label="deadness")
    ax[4].plot(secs, speed[sl] / 4.0, color="#2a9d8f", lw=0.8, label="vel. media / 4")
    ax[4].axhline(0.5, color="k", lw=0.5, ls=":")
    ax[4].set_ylabel("parada", rotation=0, ha="right", va="center")
    ax[4].legend(loc="upper right", fontsize=8)
    ax[4].set_xlabel("segundos desde el saque inicial")

    # marca los cambios de etiqueta del ground truth en todas las filas
    for c in np.flatnonzero(np.diff(gt)) + 1:
        for a in ax:
            a.axvline(secs[c], color="k", lw=0.4, alpha=0.4)

    out = v1.ROOT / "eval" / "timeline_public.png"
    out.parent.mkdir(exist_ok=True)
    fig.tight_layout()
    fig.savefig(out, dpi=120)
    print("escrito:", out.relative_to(v1.ROOT))


if __name__ == "__main__":
    main()
