# Algoritmo de posesión v1: contacto a menos de un metro

Regla acordada: un jugador confirma el control si su distancia al balón es
**estrictamente inferior a 1 metro**. Se asigna la posesión a su equipo.
Si el jugador observado más cercano queda a un metro o más, el último equipo
con control confirmado conserva la posesión, aunque ese jugador sea rival.

## Decisiones de esta primera versión

- Se elige al jugador más cercano entre los tracks con coordenadas finitas.
  Si dos jugadores están a menos de un metro, se elige el más cercano.
- **Cambio con dos compañeros.** Un control rival a menos de 1 m no cambia la posesión
  por sí solo: queda pendiente (`cambio_pendiente`) hasta que el siguiente control lo
  hace otro jugador (otro track) de ese mismo equipo. Entonces se confirma el cambio y
  la posesión del nuevo equipo empieza en el fotograma del primer jugador; esos
  fotogramas se reescriben hacia atrás. Si antes vuelve a controlar el equipo con
  posesión, el cambio pendiente se anula. Los controles repetidos del primer jugador
  no cuentan como segundo. El primer control de cada parte no necesita confirmación.
- **Toque real en el pase.** Para la regla de los dos compañeros, cada uno de los dos
  controles tiene que ser un toque real. Un contacto es la racha de fotogramas en que
  el mismo track es el más cercano a menos de 1 m. Se compara la velocidad del balón en
  los 8 fotogramas (0,32 s) anteriores al contacto con la de los 8 posteriores: si la
  dirección cambia más de 30° o la velocidad se multiplica o divide por más de 1,5
  (con un mínimo de 1 m/s), hubo toque. Si mantiene dirección y velocidad, o la cambia
  de forma proporcionada, el balón pasó de largo y ese control no cuenta para el pase
  (motivo `cambio_pendiente_sin_toque`). Si el primer jugador no lo tocó, el siguiente
  compañero que sí lo toque pasa a ser el primero. Sin balón en esas ventanas el
  resultado es desconocido y cuenta como toque. Se usa una ventana amplia porque el
  balón del ATD está suavizado: un golpeo aparece como una rampa de varios fotogramas.
  La regla no afecta al control de más de 1 s ni a los controles del equipo que tiene
  la posesión. La auditoría añade la columna `ball_touched`.
- **Cambio por control de más de 1 s.** Si no hay pase a un compañero, el cambio
  pendiente también se confirma cuando el primer jugador mantiene el balón a menos de
  1 m durante más de un segundo (más de 25 fotogramas seguidos; motivo
  `cambio_por_control`). Los fotogramas sin balón o sin jugadores observados no
  interrumpen el control; un fotograma con balón y nadie a menos de 1 m sí lo
  interrumpe y el segundo vuelve a contar desde el siguiente control. El cambio
  empieza igualmente en el primer control de ese jugador.
- **Desaparece el track del poseedor.** No hace falta una regla aparte: si el track
  del jugador con el balón desaparece, su equipo conserva la posesión hasta que el
  rival cumpla una de las condiciones de cambio (dos compañeros o control > 1 s, sin
  veto del portero). En el partido ocurre 16 veces: 11 terminan por pase rival y 5
  por control de más de 1 s.
- **Balón no detectado.** Cuando el sistema no detecta el balón en un fotograma, la
  etiqueta es D. El equipo que tenía la posesión y cualquier cambio pendiente se
  conservan, de modo que al reaparecer el balón se retoma el estado anterior. Si un
  cambio se confirma después, el retroceso hasta el primer control no sobrescribe los
  fotogramas D intermedios.
  No se ha ajustado el umbral con la referencia pública.
- Si falta el balón o no hay jugadores observados, se conserva la última posesión.
- Antes del primer contacto confirmado de cada parte se escribe `X`.
- La memoria se reinicia al cambiar de parte. Fuera de los bloques evaluados se
  escribe `X`; las posiciones ATD siguen alineadas por `video_frame = frame_id - 1`.
- Esta versión no detecta balón parado (`D`). La continuidad no tiene tiempo
  máximo, así que también puede prolongar una posesión durante una interrupción.
- Las distancias son euclídeas sobre las coordenadas normalizadas escaladas por
  las dimensiones oficiales del código, 105,3 por 68 metros.
- Los identificadores de track no son dorsales ni identidades estables.
- **Veto del portero.** Si un equipo tiene la posesión y un rival confirma el control
  (menos de 1 m) estando más cerca del centro de la portería que defiende el equipo
  con posesión —(0, 0,5) o (1, 0,5)— que el portero de ese equipo, el cambio no se
  ejecuta y se mantiene la posesión anterior (motivo `cambio_bloqueado_portero`).
  Un control vetado tampoco cuenta como primer jugador de un cambio.
  Portero: el único track del equipo dentro de su área grande (16,5 × 40,3 m) o, si
  hay varios, el más cercano al centro de su portería. Sin nadie del equipo en su área
  no hay veto. La portería defendida sale de `attack_direction_first_half` del XML y
  se invierte en la segunda parte. `--no-keeper-veto` desactiva la regla.
- **Balón parado detrás del portero.** Balón parado significa aquí balón fuera del
  terreno de juego (más allá de una línea de gol o de banda, por ejemplo en la red); un
  balón que solo frena dentro del campo sigue en juego y no hace perder la posesión.
  Mientras el balón está fuera, el control de un jugador que está dentro del área rival
  y más cerca de esa línea de gol que el portero rival no cuenta como posesión para
  nadie (motivo `control_ignorado_tras_portero`), tampoco para su propio equipo; se
  trata como un fotograma sin contacto. En el partido completo el balón está fuera del
  campo en 4.964 fotogramas y solo en 4 de ellos el más cercano está detrás del portero
  rival, siempre a más de 1 m: la regla no cambia ninguna etiqueta (macroF1 0,6712,
  spellF1 0,3152 en los cinco minutos públicos).

## Reproducción

Desde la raíz del repositorio, con las carpetas tactical y broadcast en el padre:

```powershell
python starter/possession_v1.py --data-dir ..
python evaluation/validate_submission.py evaluation/results/algoritmo_v1.csv
python evaluation/run_evaluation.py --no-detail
python -m unittest discover -s tests -p test_possession_v1.py
```

La predicción se escribe en `evaluation/results/algoritmo_v1.csv`.
La auditoría de cada decisión se escribe en
`evaluation/reports/algoritmo_v1_auditoria.csv`: observación más cercana, distancia,
etiqueta, último frame/track con control confirmado, motivo de la decisión y, para el
veto, la distancia del jugador y del portero rival al centro de la portería.
Los resultados y datos de auditoría quedan en carpetas ignoradas por Git.

## Verificación de la primera ejecución

- 199.319 filas, formato validado por el validador oficial.
- Seis pruebas de comportamiento superadas: primer control, rival lejano,
  cambio confirmado, umbral exacto, observaciones ausentes y reinicio de memoria.
- De 25:07,00 a 25:10,00, excluyendo el extremo final: `H` en los 75 fotogramas.
  En 25:07 el rival más cercano está a 13,4759 m; se conserva el control del
  Barcelona confirmado por el track 15 en el fotograma 37.639 (25:05,56).

Resultados exclusivamente sobre los cinco minutos públicos:

| Método | macroF1 | spellF1 |
|---|---:|---:|
| Primera prueba / baseline smooth50 | 0,6207 | 0,3256 |
| Algoritmo v1 sin veto del portero | 0,5069 | 0,2792 |
| Algoritmo v1 con veto del portero | 0,5124 | 0,2824 |
| Algoritmo v1 con veto + cambio con dos compañeros | 0,5362 | 0,3724 |
| Algoritmo v1 con veto + dos compañeros o control > 1 s | 0,5362 | 0,3724 |
| Ídem + hueco sin balón anula el cambio pendiente (regla retirada) | 0,5403 | 0,3862 |
| Ídem + el pase exige toque real (regla retirada con el hueco; histórico) | 0,5403 | 0,3862 |
| Versión actual: sin anulación por hueco, D cuando no se detecta el balón | 0,6712 | 0,3152 |

Con solo el veto, en el partido completo actuaba en 5 episodios (272 fotogramas) y
cambiaba 489 etiquetas: 15.654 (T24), 50.996 (T46), 67.188 (T33), 114.206 (T46) y
135.011 (T24).

Con el cambio con dos compañeros el partido completo pasa de unas 490 posesiones a
139 (media de 45,7 s), y en los cinco minutos públicos de 34 a 12 frente a 17 reales:
ahora se pierden cambios de posesión reales (por ejemplo, un robo seguido de un
tiro o de una pérdida inmediata).

Al añadir el control de más de 1 s, 48 cambios del partido completo se confirman por
esa vía y las posesiones pasan de 139 a 175 (media de 36,3 s). En los cinco minutos
públicos no aparece ningún caso, así que su puntuación no cambia.

[Histórico] La regla de anular el cambio pendiente tras un hueco sin balón se ha
eliminado. Ahora cada fotograma sin balón detectado se etiqueta D (64.643 fotogramas
en el partido completo, el 40,7 % de los evaluados) y el estado se conserva para
cuando el balón reaparece. La puntuación de la versión actual sobre los cinco minutos
públicos es macroF1 0,6712 y spellF1 0,3152 (16 posesiones frente a 17 reales).

Con el toque real, de 27.615 fotogramas de contacto 22.373 son toque, 3.072 son balón
que pasa de largo y 2.170 desconocidos. Los cambios por pase bajan de 117 a 84, los
de control > 1 s suben de 48 a 55 y el partido queda en 141 posesiones (media de
45,1 s); cambian 8.637 etiquetas. En 16:44–16:54 el contacto de T29 (16:46,28) ya no
confirma el pase de T30: el Athletic gana la posesión con T32 en 16:48,60.

La corrección del caso observado no supone una mejora global. Falta incorporar
la detección de interrupciones y estudiar los cambios provocados por contactos
aislados. El resultado del partido completo sigue siendo privado.
