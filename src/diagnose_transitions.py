"""Diagnóstico automático de los cambios de estado en los 5 minutos públicos.

Para cada cambio real del ground truth (H->A, A->D, D->H, ...) dice si v1 lo detecta
y, si no, la causa más probable. Solo imprime conteos y porcentajes agregados.

Uso, desde la raíz de CDS-Tech:
    python src/diagnose_transitions.py
    python src/diagnose_transitions.py --switch-team 10     # otra configuración
"""
import argparse
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v1_viterbi as v1  # noqa: E402

GT = v1.ROOT / "mtah" / "evaluation" / "gt" / "BAR-ATH_possession_gt_public.csv"
FIRST, LAST = 11185, 18684
TOL = 25  # un cambio cuenta como detectado si v1 cambia al mismo estado a ±1 s


def read_labels(path):
    labels = np.loadtxt(path, delimiter=",", skiprows=1, dtype=str, usecols=1)
    return np.array([x.strip().upper() for x in labels])


def segments(labels):
    """Lista de (inicio, fin_exclusivo, etiqueta) de rachas consecutivas."""
    out, start = [], 0
    for t in range(1, len(labels) + 1):
        if t == len(labels) or labels[t] != labels[start]:
            out.append((start, t, labels[start]))
            start = t
    return out


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
    dead, _, _ = v1.deadness(f, v1.GAMES[v1.GAME]["pitch"])
    pred_all = v1.segment(e_home, e_away, dead, n,
                          v1.transition_matrix(args.switch_team, args.switch_dead))

    sl = slice(FIRST, LAST + 1)
    gt, pred = read_labels(GT)[sl], pred_all[sl]
    ev = {"H": e_home[sl], "A": e_away[sl]}
    ball = ~np.isnan(f["bx"][sl])
    dd = dead[sl]

    segs = segments(gt)
    print("cambios reales: {}   (coste de cambio de equipo = {:.0f} frames)\n".format(
        len(segs) - 1, args.switch_team))
    print("{:>3}  {:>6}  {:>6}  {:>5}  {:>7}  {:>7}  {:>6}  {:>6}  {}".format(
        "#", "seg", "cambio", "dur_s", "ev_new", "ev_old", "balón", "dead", "resultado"))

    causes = Counter()
    for k in range(1, len(segs)):
        (_, _, old), (s, e, new) = segs[k - 1], segs[k]
        lo, hi = max(0, s - TOL), min(len(pred), s + TOL + 1)
        detected = any(pred[t] == new and pred[t - 1] != new for t in range(max(1, lo), hi))

        dur = (e - s) / 25.0
        ev_new = int(ev[new][s:e].sum()) if new in ev else 0
        ev_old = int(ev[old][s:e].sum()) if old in ev else 0
        ball_pct = 100.0 * ball[s:e].mean()
        dead_mean = float(dd[s:e].mean())

        if detected:
            cause = "detectado"
        elif new == "D":
            cause = "parada no detectada" if dead_mean < 0.5 else "parada detectada tarde"
        elif old == "D":
            majority = Counter(pred[s:e]).most_common(1)[0][0]
            cause = ("reanuda el equipo equivocado" if majority in "HA" and majority != new
                     else "salida de parada mal situada")
        elif ev_new == 0:
            cause = "sin evidencia del nuevo equipo"
        elif ev_new - ev_old < args.switch_team:
            cause = "evidencia insuficiente para el coste"
        else:
            cause = "otra causa"
        causes[cause] += 1

        print("{:>3}  {:>6}  {:>6}  {:>5.1f}  {:>7}  {:>7}  {:>5.0f}%  {:>6.2f}  {}".format(
            k, "{}-{}".format(s, e), "{}->{}".format(old, new), dur,
            ev_new, ev_old, ball_pct, dead_mean, cause))

    print("\nresumen")
    for cause, count in causes.most_common():
        print("  {:<40} {}".format(cause, count))
    print("\nseg = frames relativos al saque inicial; ev_new/ev_old = frames con control del")
    print("nuevo/antiguo equipo durante el nuevo tramo; balón = % de frames con balón visible;")
    print("dead = media de la señal de parada (0 vivo, 1 parado).")


if __name__ == "__main__":
    main()
