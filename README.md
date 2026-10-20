# CDS-Tech · More than a Hack 2027 — Fase 1: posesión del balón

Objetivo: generar un CSV `frame,label` con 199.319 filas que diga, para cada frame del vídeo
táctico, si el balón es del Barcelona (`H`), del Athletic (`A`), está muerto (`D`) o no
respondemos (`X`). Entrega: **17 de noviembre de 2026**. Contexto completo en la presentación
del equipo y en `context/`.

## Instalación

```bash
git clone --recurse-submodules <url-de-este-repo>
cd CDS-Tech
conda create -n mtah python=3.11 -y
conda activate mtah
pip install -r requirements.txt
```

Los datos no están en el repo y **nunca se suben**. Colocadlos en `dataset/tactical/` y
`dataset/broadcast/` con sus nombres originales, y en cada terminal:

```bash
export MTAH_DATA_DIR="$PWD/dataset"
```

Si añadís una dependencia, actualizad `requirements.txt` en el mismo commit: el repo tiene que
regenerar exactamente el CSV entregado.

## Estructura

```
context/     documentación oficial del reto
mtah/        repo oficial de los organizadores (scorer, GT público, baseline). No tocar
src/         nuestro pipeline
notebooks/   exploración
docs/        documento técnico de la entrega
dataset/     datos del partido (ignorado por git)
outputs/     CSV generados (ignorado por git)
eval/        informes de evaluación (ignorado por git)
```

## Generar, validar y evaluar

```bash
python mtah/evaluation/validate_submission.py outputs/<fichero>.csv
python mtah/evaluation/run_evaluation.py --results outputs --out eval
```

Para comprobar la instalación, regenerad antes los baselines con
`python mtah/starter/baseline.py --out outputs`: `baseline_smooth50` debe dar spellF1 0.3256.