# Smart Tagging: guía de códigos y etiquetas

Este documento explica las anotaciones de Smart Tagging incluidas en `tactical/BAR-ATH_tactical_smart_tagging.xml`. El XML contiene 638 intervalos generados automáticamente para el vídeo táctico del partido FC Barcelona–Athletic Club.

## Cómo leer una anotación

Cada `<instance>` tiene un identificador, un código (`<code>`), un inicio y un fin en segundos (`<start>` y `<end>`), y cero o más etiquetas agrupadas (`<label>`). Los códigos indican el tipo de fase o situación detectada; las etiquetas aportan contexto, como equipo, mitad, lado o tipo de reanudación.

Los tiempos son segundos desde el primer fotograma del vídeo táctico, no el minuto del marcador del partido. A 25 fps, la conversión usada por el cargador del proyecto es:

```text
fotograma = round(segundos × 25)
```

`start_frame` es el fotograma inicial. `end_frame` es el primer fotograma después del intervalo (intervalo semiabierto: `[start_frame, end_frame)`). Por tanto, el inicio o fin de una anotación no tiene por qué coincidir con el instante exacto de un pase, remate o gol. Las anotaciones son automáticas y pueden solaparse: describen fases y señales tácticas, no una partición exclusiva del partido ni etiquetas de posesión verificadas manualmente.

## Códigos de anotación

Las descripciones siguientes explican el sentido táctico de cada código. El conteo es el número de instancias del XML de este partido.

| Código | Instancias | Qué representa |
|---|---:|---|
| `PLAYERS IN THE BOX` | 97 | Una acción ofensiva en la que se registra cuántos jugadores atacantes hay dentro del área rival. El detalle suele venir en `Max Players in the box`. |
| `BALL IN FINAL THIRD` | 93 | El balón se juega o permanece en el tercio del campo más cercano a la portería rival. Puede incluir `Side` y `Max Players in the box`. |
| `BALL IN THE BOX` | 72 | El balón entra o se juega dentro del área rival, por pase, centro o conducción. Puede indicar dirección de entrada y número máximo de atacantes en el área. |
| `PROGRESSION` | 66 | Acciones ofensivas que avanzan el balón, a menudo a través del tercio medio y superando líneas rivales mediante pase, conducción o apoyos. |
| `DEFENDING IN MIDDLE THIRD` | 66 | Acciones defensivas en el tercio medio, como presionar, cerrar espacios y limitar el avance rival. |
| `SET PIECES` | 59 | Situaciones de reanudación tras una interrupción: saques de banda, córneres, tiros libres, saques de puerta e inicios de juego. El subtipo se indica en `Type`. |
| `CREATING CHANCES` | 30 | Acciones en zona de ataque que generan peligro o una oportunidad de remate, como un pase clave o una acción que deja a un compañero en buena posición. |
| `DEFENDING IN DEFENSIVE THIRD` | 30 | Acciones defensivas cerca de la propia portería, como marcar, cubrir, proteger el área o bloquear. |
| `LONG BALL` | 29 | Pase directo de larga distancia para ganar terreno o buscar el espacio a la espalda de la defensa. |
| `ATTACKING TRANSITION` | 24 | Ataque inmediatamente posterior a recuperar el balón, aprovechando que el rival aún está reorganizándose. |
| `DEFENSIVE TRANSITION` | 24 | Reacción inmediatamente posterior a perder el balón: presionar, proteger espacios o replegarse. |
| `BUILD UP` | 22 | Acciones con las que un equipo inicia y desarrolla la posesión desde su propio campo para superar la primera presión y avanzar. |
| `DEFENDING IN ATTACKING THIRD` | 22 | Acciones defensivas de presión y control del espacio en el tercio más cercano a la portería rival. |
| `GOALS` | 4 | Intervalo que el sistema asocia con un gol. Es una anotación de fase, no necesariamente una marca puntual del instante en que el balón cruza la línea. Comprueba el vídeo para localizar el momento exacto. |

Los intervalos de estos códigos pueden abarcar varios segundos o minutos y solaparse con códigos como `BALL IN THE BOX`. Para encontrar el instante preciso de una acción, el código es una pista temporal que se contrasta con el vídeo y con otras anotaciones cercanas.

## Grupos de etiquetas

Las etiquetas no aparecen todas en cada instancia. En el XML, el nombre del grupo distingue etiquetas que podrían tener textos parecidos.

| Grupo | Valores observados | Significado |
|---|---|---|
| `Team` | `Barcelona` (314), `Atletic Club` (288), `N/A` (36) | Equipo al que el sistema atribuye la acción. `N/A` significa que no se asignó un equipo. En estos datos aparece en todas las anotaciones de saque de banda; no debe convertirse automáticamente en Barcelona o Athletic. |
| `Half` | `1st Half` (320), `2nd Half` (318) | Mitad del partido a la que pertenece la anotación. Son cadenas de texto, no números. |
| `Type` | `Throw-in` (26), `Corner Kick` (12), `Goal Kick` (10), `Free Kick` (5), `Kick Off (After Goal)` (4), `Kick Off (Start)` (2) | Tipo de reanudación cuando el código es `SET PIECES`. |
| `Side` | `Central` (59), `Left` (19), `Right` (15) | Zona lateral o central asociada a la acción. Se usa en anotaciones de balón en el tercio final. |
| `Direction of ball entry` | `Horizontal` (34), `Vertical` (25), `Diagonal` (13) | Dirección aproximada con que el balón entra en el área rival. Se usa con `BALL IN THE BOX`. |
| `Max Players in the box` | `1` (59), `2` (43), `3` (27), `4` (65), `5` (31), `6` (27), `7+` (10) | Máximo de jugadores atacantes que el sistema detecta en el área durante la acción. Los valores son texto; `7+` representa siete o más. |

Los conteos de valores de etiquetas son por grupo y suman 638 para `Team` y `Half`. Los grupos condicionales (`Type`, `Side`, `Direction of ball entry` y `Max Players in the box`) solo aparecen en determinadas clases de anotación, por lo que sus conteos no suman 638.

## Límites de interpretación

- Smart Tagging es una salida automática, no una revisión humana ni verdad de terreno; puede omitir eventos o marcar alguno incorrectamente.
- Un intervalo etiquetado como fase no equivale necesariamente a una posesión completa ni a un evento instantáneo.
- `Team` puede ser `N/A`; conserva ese valor como desconocido.
- Para análisis por fotograma, expande cada intervalo con la convención `[start_frame, end_frame)` y evita tratar `end_frame` como un fotograma incluido.
- La fuente es el vídeo `tactical`; la grabación `broadcast` tiene otra línea temporal y no está sincronizada con esta anotación.

## Referencias del proyecto

- Datos y convención temporal: `Proyecto/DATA.md`, sección **Smart Tagging** y **Frame alignment**.
- Definiciones tácticas de los códigos: `Proyecto/OVERVIEW.md`, sección **Smart Tagging**.
- Conversión XML a intervalos/fotogramas: `Proyecto/starter/load_smart_tagging.py`.
