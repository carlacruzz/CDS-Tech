"""Comprueba dos hipótesis en los 5 minutos públicos, antes de programar nada.

1. Toques: ¿el ground truth cambia de equipo justo cuando el balón cambia bruscamente de
   velocidad o dirección cerca de un jugador del NUEVO equipo? Si casi siempre es así,
   la posesión del GT se parece a "último equipo que tocó el balón".
2. Paradas: ¿se ve el balón junto a una línea justo antes de cada parada? ¿El Smart
   Tagging marca un reinicio cerca del final de cada parada?

Solo imprime valores agregados por evento (equipo, distancias, desfases en frames).
test
Uso, desde la raíz de CDS-Tech:
    python src/diagnose_moments.py
"""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v1_viterbi as v1  # noqa: E402
from games import asset_paths  # noqa: E402

GT = v1.ROOT / "mtah" / "evaluation" / "gt" / "BAR-ATH_possession_gt_public.csv"
FIRST, LAST = 11185, 18684
SEARCH = 12   # busca el toque en ±12 frames (~0,5 s) alrededor del cambio del GT
LAG = 3       # cambio de velocidad medido entre t-LAG y t+LAG


def read_labels(path):
    labels = np.loadtxt(path, delimiter=",", skiprows=1, dtype=str, usecols=1)
    return np.array([x.strip().upper() for x in labels])


def segments(labels):
    out, start = [], 0
    for t in range(1, len(labels) + 1):
        if t == len(labels) or labels[t] != labels[start]:
            out.append((start, t, labels[start]))
            start = t
    return out


def ball_kick(f):
    """Magnitud del cambio de velocidad del balón (m/s) entre t-LAG y t+LAG."""
    bx, by = f["bx"].astype(float), f["by"].astype(float)
    vx = np.full_like(bx, np.nan)
    vy = np.full_like(by, np.nan)
    vx[1:-1] = (bx[2:] - bx[:-2]) * 12.5   # 25 fps, diferencia centrada
    vy[1:-1] = (by[2:] - by[:-2]) * 12.5
    kick = np.full_like(bx, np.nan)
    kick[LAG:-LAG] = np.hypot(vx[2 * LAG:] - vx[:-2 * LAG], vy[2 * LAG:] - vy[:-2 * LAG])
    return kick


def nearest(f, t):
    """(equipo, distancia) del jugador más cercano al balón en el frame t."""
    dh, da = f["d_home"][t], f["d_away"][t]
    dh = np.inf if np.isnan(dh) else dh
    da = np.inf if np.isnan(da) else da
    if np.isinf(dh) and np.isinf(da):
        return "-", np.nan
    return ("H", dh) if dh <= da else ("A", da)


def distance_to_line(f, t, pitch):
    x, y = f["bx"][t], f["by"][t]
    length, width = pitch
    return min(x, length - x, y, width - y)


def smart_tagging_starts():
    """[(frame_inicio, code, type)] de todas las instancias del Smart Tagging."""
    root = ET.parse(asset_paths()["smart_tagging"]).getroot()
    out = []
    for inst in root.iter("instance"):
        start = inst.findtext("start")
        if start is None:
            continue
        labels = {(lab.findtext("group") or "").strip().lower(): (lab.findtext("text") or "").strip()
                  for lab in inst.findall("label")}
        out.append((int(round(float(start) * 25)), (inst.findtext("code") or "").strip().upper(),
                    labels.get("type", "")))
    return sorted(out)


def main():
    f = v1.load_features()
    pitch = v1.GAMES[v1.GAME]["pitch"]
    kick = ball_kick(f)
    gt = read_labels(GT)
    segs = [(s + FIRST, e + FIRST, lab) for s, e, lab in segments(gt[FIRST:LAST + 1])]

    # ------------------------------------------------------------ 1. toques
    print("1. CAMBIOS DE EQUIPO (H<->A, y salidas de parada D->H/A)\n")
    print("{:>3}  {:>6}  {:>9}  {:>7}  {:>11}  {:>11}  {}".format(
        "#", "cambio", "toque_off", "dv_m/s", "cerca@toque", "cerca@GT", "¿nuevo equipo toca?"))
    hits = total = 0
    for k in range(1, len(segs)):
        old, (s, _, new) = segs[k - 1][2], segs[k]
        if new == "D":
            continue
        window = np.arange(s - SEARCH, s + SEARCH + 1)
        kw = kick[window]
        if np.all(np.isnan(kw)):
            off, dv, near_t = None, np.nan, ("-", np.nan)
        else:
            i = int(np.nanargmax(kw))
            off, dv = int(window[i] - s), float(kw[i])
            near_t = nearest(f, window[i])
        near_gt = nearest(f, s)
        ok = near_t[0] == new and near_t[1] <= 3.0
        total += 1
        hits += ok
        print("{:>3}  {:>6}  {:>9}  {:>7.1f}  {:>4} {:>5.1f}m  {:>4} {:>5.1f}m  {}".format(
            k, "{}->{}".format(old, new), "-" if off is None else "{:+d}".format(off), dv,
            near_t[0], near_t[1], near_gt[0], near_gt[1], "sí" if ok else "no"))
    print("\n  el nuevo equipo está a <3 m del balón en el pico de cambio de velocidad: "
          "{} de {}\n".format(hits, total))

    # ------------------------------------------------------------ 2. paradas
    tags = smart_tagging_starts()
    print("2. PARADAS (tramos D del ground truth)\n")
    print("{:>3}  {:>6}  {:>13}  {:>11}  {:>22}  {}".format(
        "#", "dur_s", "últ.balón_off", "dist_línea", "tag más cercano al fin", "desfase"))
    for k, (s, e, lab) in enumerate(segs):
        if lab != "D":
            continue
        seen = np.flatnonzero(~np.isnan(f["bx"][s - 250:s + 1]))
        if len(seen):
            last = s - 250 + int(seen[-1])
            last_off = "{:+d}".format(last - s)
            line = "{:.1f}m".format(distance_to_line(f, last, pitch))
        else:
            last_off, line = "sin balón", "-"
        if tags:
            j = int(np.argmin([abs(t0 - e) for t0, _, _ in tags]))
            t0, code, typ = tags[j]
            tag = "{} {}".format(code[:12], typ[:9]).strip()
            lag = "{:+d} fr".format(t0 - e)
        else:
            tag, lag = "-", "-"
        print("{:>3}  {:>6.1f}  {:>13}  {:>11}  {:>22}  {}".format(
            k, (e - s) / 25.0, last_off, line, tag, lag))
    print("\núlt.balón_off = frame en que se vio el balón por última vez, relativo al inicio de")
    print("la parada; dist_línea = distancia de ese balón a la línea más cercana; desfase =")
    print("inicio del tag menos fin de la parada (negativo: el tag empieza antes del reinicio).")


if __name__ == "__main__":
    main()
