# Contexto del proyecto More Than a Hack 2027

Documento de traspaso para continuar el trabajo con otro agente de IA. Estado revisado el 24 de octubre de 2026. Separa los resultados comprobados de las hipótesis pendientes; no presupone que se haya enviado ninguna candidatura o solución.

## 1. Entorno y objetivo

El usuario es Rubén. Trabajamos en español y necesita explicaciones claras de las bases del proyecto. Carpeta de trabajo: `C:\Users\ruben\OneDrive\Escritorio\MoreThanAHack`. El repositorio está en la subcarpeta `Proyecto`; los datos están en las carpetas hermanas `tactical` y `broadcast`.

Repositorio: https://github.com/metrica-sports/more-than-a-hack-2027 . Rama main, referencia inspeccionada `3de6b60aeabd2475d95879a651d38b72bc4fba00` (Bibtex updated). No hemos realizado commits, push ni una entrega al concurso. Los archivos generados y scripts nuevos pueden estar sin seguimiento o ignorados: comprobar git status antes de modificar o publicar.

El objetivo de la primera fase es predecir el equipo con posesión en cada fotograma del vídeo táctico del Barcelona–Athletic, jornada 2 de LaLiga 2024–25. La fase va del 20 de octubre al 17 de noviembre de 2026. Se entrega un CSV, código público reproducible y una explicación técnica breve en PDF o Markdown. El formulario se comunica por correo; para fases posteriores se requieren equipos de 3 a 5 personas. Confirmar cualquier cambio de calendario en fuentes oficiales.

La página inicial https://talentarena.tech/es/more-than-a-hack-barca-innovation-hub/ conservaba información de la edición 2026 de IA generativa. Para esta edición se consultó https://landing.mobileworldcapital.com/more-than-a-hack-2027 y, sobre todo, la documentación del repositorio.

## 2. Trabajo realizado

Se analizó la convocatoria, el repositorio y los documentos README.md, CHALLENGE.md, DATA.md, EVALUATION.md, SUBMISSION.md, RULES.md, FAQ.md y OVERVIEW.md, además de las instrucciones de data/README.md. Se explicaron al usuario el problema, los datos, las métricas y la función del baseline.

Se generó un informe PDF inicial, se ejecutaron primeras pruebas del baseline y se crearon gráficos de intervalos de posesión, primero estáticos y después interactivos. El usuario detectó una discrepancia entre vídeo y baseline en 25:07–25:10. Se investigaron distancias, jugadores detectados y Smart Tagging, y se construyó un visor de tracking fotograma a fotograma.

A continuación se implementó la primera regla de posesión solicitada por el usuario, se evaluó, se incorporó su CSV al explorador de posesión y se amplió el visor espacial hasta cubrir todo el tracking ATD táctico. El último encargo antes de este documento fue esa ampliación completa.

## 3. Salida y evaluación del concurso

El CSV debe contener cabecera `frame,label` y 199319 filas de datos, con frames ordenados de 0 a 199318. Etiquetas: H = local Barcelona; A = visitante Athletic; D = balón parado; X = abstención.

La clasificación principal usa spell F1; macro F1 es el primer desempate. Cada secuencia contigua de H o A constituye una posesión; D la interrumpe. La posesión supone control, no cualquier roce o desvío. Un balón disputado o suelto puede conservar la posesión del equipo anterior.

La referencia completa procede de tracking corregido privado. La referencia pública solo contiene cinco minutos útiles: frames 11185–18684, ambos incluidos, 7500 fotogramas y 17 posesiones. El resto de su referencia se ignora mediante X. No optimizar únicamente esos 17 intervalos ni confundir la puntuación pública con la del partido completo. X penaliza macro F1; para métricas temporales se propaga la etiqueta anterior dentro de cada parte y se completa el inicio desde la primera conocida.

Ventanas evaluables: primera parte 11185–90651; segunda 110808–190197. Son 158857 frames. Quedan fuera 40462 frames: 0–11184, 90652–110807 y 190198–199318. La segunda ventana empieza antes del saque inicial efectivo, señalado en 113742: los 2934 frames anteriores son relevantes para modelar D.

## 4. Restricciones y cautelas

Las predicciones finales deben proceder del algoritmo; no corregir manualmente etiquetas para arreglar un fragmento. Se permiten pequeñas anotaciones para entrenamiento o validación según las reglas. No utilizar la referencia privada o el tracking corregido completo como fuente de posesión.

Los datos del concurso no se deben redistribuir. Esto incluye vídeo, extractos y exportaciones derivadas que permitan reconstruir tracking. Tampoco enviar datos restringidos o clips a modelos alojados de terceros. Los visores locales contienen coordenadas completas y no deben publicarse junto con el código. Revisar los archivos ignorados antes de cualquier publicación; no asumir que un HTML es inocuo por ser una visualización.

No se ha autorizado ni realizado publicación, envío de candidatura, commit o push. Mantener los archivos originales y el baseline de referencia. La implementación y las pruebas locales reversibles forman parte del trabajo solicitado.

## 5. Inventario y significado de los datos

### Datos tácticos: fuente utilizada

| Archivo en tactical | Contenido |
| --- | --- |
| BAR-ATH_tactical-001.mp4 | Vídeo 1920 × 1080, 25 fps, 199319 muestras, duración 7972,76 s (132:52,76); 5222307334 bytes |
| BAR-ATH_tactical_atd.xml | Metadatos, dimensiones, identificación de tracks y asignación de equipo; 59057 bytes |
| BAR-ATH_tactical_atd.txt | Tracking original: 199319 líneas, identificadores 1–199319; 195714285 bytes |
| BAR-ATH_tactical_homography.csv | Transformaciones campo-imagen, 199319 filas, todas válidas; 23187043 bytes |
| BAR-ATH_tactical_smart_tagging.xml | 638 eventos automáticos; 261055 bytes |

El ATD ofrece 46 slots de jugadores, no 46 jugadores presentes simultáneamente. Los identificadores de track no son dorsales ni permiten asumir una identidad real estable. El XML asigna los tracks a cada equipo. Las coordenadas XY están normalizadas entre 0 y 1; NaN indica ausencia de detección. El tercer canal de jugador es velocidad.

La estructura de una línea es aproximadamente `frame_id:x,y,speed;...:ball_x,ball_y,...`. Para distancias, el código aplica escala 105,3 × 68 metros, como el baseline y games.py; el XML declara 105 × 68. Conservar explícita esa pequeña diferencia al comparar cálculos.

**Correspondencia de índices ya resuelta:** en los ATD entregados, `video_frame = frame_id - 1`. Se verificó la continuidad completa. Los offsets de games.py describen el contador separado del tracking corregido privado; starter/load_atd.py lo explica expresamente. Hubo una duda inicial sobre este punto, pero no queda una contradicción pendiente y no hay que desplazar nuestros datos por esos offsets.

El balón aparece en 113488 de los 199319 frames (56,94 %). La documentación menciona aproximadamente 59,3 % dentro de ventanas evaluables; no son denominadores equivalentes. Faltan detecciones y pueden faltar jugadores: no interpolamos ni inventamos posiciones en los visores.

### Broadcast: disponible, todavía no utilizado

| Archivo en broadcast | Contenido |
| --- | --- |
| BAR-ATH_broadcast-001.mp4 | Vídeo 1920 × 1080, duración 6579,52 s; 13962360320 bytes |
| BAR-ATH_broadcast_atd.xml | Metadatos; 64956 bytes |
| BAR-ATH_broadcast_atd.txt | 164488 filas de tracking; 141966465 bytes |
| BAR-ATH_broadcast_homography.csv | 164488 filas; 15401635 bytes |

La inspección del contenedor de vídeo indicó 164487 muestras frente a 164488 filas ATD; no se ha decodificado todo para resolver esa diferencia. Hay 108248 homografías válidas (65,81 %) y 83121 frames con balón observado (50,53 %). Los vídeos táctico y broadcast no están sincronizados y no se ha construido un mapeo. Los cortes y repeticiones complican su uso. No se necesitan vídeos para ejecutar baseline, v1 o nuestros visores de tracking; podrían aportar evidencia adicional en futuras mejoras.

### Homografía y Smart Tagging

La homografía transforma coordenadas normalizadas del campo en píxeles del vídeo. Validez y error de reproyección son conceptos diferentes. No se usa en v1.

Los tiempos del Smart Tagging son segundos desde el comienzo del vídeo; se aproxima el frame con redondeo de tiempo × 25. Los eventos automáticos se solapan y no constituyen una verdad de posesión. Hay 36 eventos con equipo N/A. En acciones defensivas, Team identifica al defensor. No marcar como D todo un intervalo de SET PIECES: sus rangos incluyen contexto y pueden solaparse con juego activo.

Los nombres reales de vídeo incluyen -001, mientras que games.py espera algunos nombres sin ese sufijo. No se han renombrado los originales.

## 6. Baseline y resultados públicos

starter/baseline.py se conserva como referencia. Usa el mapa de equipos del XML y asigna el equipo del jugador detectado más cercano al balón, con coordenadas escaladas a metros. No exige distancia máxima. Si falta balón, el resultado bruto es D.

El suavizado `smooth=50` usa una ventana centrada de hasta 101 observaciones: 50 anteriores, la actual y 50 posteriores, unos 4,04 segundos. **Solo cuentan los votos H y A.** D no compite como un tercer voto: sale D si no hay votos H/A; los empates favorecen H. No utiliza vídeo, homografía ni Smart Tagging y no representa explícitamente el control persistente del balón.

Se generó evaluation/results/primera_prueba.csv con ese baseline suavizado. Las puntuaciones de la referencia pública guardadas en evaluation/scoreboard.csv son:

| Método | Macro F1 | Spell F1 | Posesiones predichas en la muestra |
| --- | ---: | ---: | ---: |
| Baseline sin suavizar | 0,597227 | 0,037838 | 131 |
| Suavizado 25 | 0,619991 | 0,286792 | 36 |
| Suavizado 50 / primera prueba | 0,620733 | 0,325581 | 26 |
| Suavizado 125 | 0,581185 | 0,424242 | 16 |
| Algoritmo v1 | 0,506882 | 0,279245 | 36 |

El suelo oficial publicado para smooth=50 sobre el partido completo es spell F1 0,2433. No compararlo directamente con el 0,325581 de nuestra muestra pública. No conocemos la puntuación privada de v1. La primera regla mejora la interpretación del fragmento investigado, pero **no mejora las métricas públicas globales**.

## 7. Investigación del fragmento 25:07–25:10

El usuario observó en el vídeo posesión del Barcelona mientras el baseline mostraba Athletic. Después indicó que faltaban jugadores en esos fotogramas. No presentar esa observación del vídeo como una revisión visual independiente del agente: la comprobación técnica realizada fue sobre datos, distancias, votos y etiquetas automáticas.

El intervalo [25:07,25:10) contiene 75 frames, 37675–37749; el visor SVG incluye también el extremo 37750 y por eso contiene 76. Los identificadores ATD correspondientes son una unidad mayores.

En los 75 frames aparece el balón y el jugador más cercano detectado es siempre Track 41 del Athletic, a distancias entre 8,792458 y 15,526707 m. A 25:07 hay 20 jugadores detectados, 10 por equipo; el más próximo del Barça es T2 a 20,018466 m y el del Athletic T41 a 13,475906980453116 m. Ser el menos alejado no equivale a controlar el balón.

| Instante | Distancia mínima Barcelona (m) | Distancia mínima Athletic (m) | Votos H/A del suavizado |
| --- | ---: | ---: | --- |
| 25:07 | 20,018466 | 13,475907 | 29 / 72 |
| 25:08 | 18,819650 | 14,355620 | 4 / 97 |
| 25:09 | 16,609240 | 11,005090 | 0 / 101 |
| 25:10 | 15,389050 | 8,705480 | 16 / 85 |

El baseline bruto y suavizado dan A de 25:06,16 a 25:11,40. Smart Tagging incluye BUILD UP Barcelona y defensa Athletic de 1494,64 a 1520,72 s, pero también intervalos solapados de balón en último tercio Athletic, córner Athletic y saque de puerta Barcelona. Son pistas contextuales, no una etiqueta manual ni verdad de referencia.

## 8. Primera lógica propia: algoritmo v1

La regla acordada por el usuario es: un jugador confirma posesión si está a **menos de 1 metro** del balón. Si después el balón se aleja y el jugador más próximo pertenece al rival pero está a más de un metro, el equipo anterior conserva la posesión.

Implementación en starter/possession_v1.py, clase PossessionTracker:

1. Encontrar el jugador detectado y finito más cercano al balón.
2. Si su distancia es estrictamente menor que el umbral, actualizar equipo, track y frame del último control confirmado.
3. Si nadie cumple el umbral, conservar el equipo anterior. También se conserva cuando falta balón o no hay jugadores válidos.
4. Antes del primer control confirmado de cada parte, emitir X; reiniciar estado entre partes y emitir X fuera de ventanas evaluables.
5. Si varios jugadores cumplen, gana el más cercano; un empate exacto se resuelve por orden de slots del XML.

No se suaviza ni se exige duración mínima del contacto. No hay caducidad de posesión ni detección de D. No utiliza vídeo, Smart Tagging o homografía. Estas son limitaciones reales, no funciones pendientes ya aceptadas por el usuario.

Resultado completo: H 79400, A 79455, X 40464, D 0; 199319 filas. De las X, 40462 están fuera de evaluación y dos preceden al primer control. Hay 491 cambios de equipo y 493 intervalos H/A en el partido. No confundirlos con los 36 intervalos de la muestra pública.

Motivos de auditoría: fuera de ventana 40462; sin control inicial 2; primer control 2; mantener por distancia 67369; cambio de equipo 491; control confirmado 26352; mantener por detección ausente 64641.

En los 75 frames investigados v1 mantiene H. A 25:07, el último control fue en frame 37639, 25:05,56, por Track 15 del Barcelona. T41 del Athletic está a 13,4759 m y no puede arrebatar posesión con esta regla. No se han corregido a mano esos frames.

Archivos de implementación y resultados dentro de Proyecto:

- starter/possession_v1.py: algoritmo y CLI con --data-dir, --threshold (1 por defecto), --out y --audit.
- tests/test_possession_v1.py: seis pruebas; inicio X, retención ante rival lejano, cambio con rival cercano, exclusión del metro exacto y conservación/reinicio con datos ausentes. Pasaron las seis.
- ALGORITMO_V1.md: explicación y reproducción de v1.
- evaluation/results/algoritmo_v1.csv: predicción completa, 1882093 bytes; validación oficial superada.
- evaluation/reports/algoritmo_v1_auditoria.csv: 9805470 bytes; columnas frame,label,nearest_track,nearest_team,nearest_distance_m,last_control_frame,last_control_track,reason.
- evaluation/reports/algoritmo_v1_resumen.json: resumen de ejecución.
- evaluation/reports/algoritmo_v1.json y algoritmo_v1_transitions.csv: métricas y transiciones.
- evaluation/scoreboard.csv: comparación pública guardada.

## 9. Entregables y visores

Rutas relativas a la carpeta MoreThanAHack, salvo que comiencen por Proyecto.

### Informe y explorador temporal de posesión

output/pdf/MoreThanAHack2027_Analisis_Completo.pdf: informe inicial de siete páginas, anterior a v1 y a las ampliaciones. No asumir que contiene el estado actual. Generador: tmp/pdfs/build_report.py; se usó PyMuPDF como alternativa al no estar reportlab disponible.

output/charts/Primera_prueba_intervalos_posesion.png: gráfico estático inicial del baseline. Generador: tmp/plot_primera_prueba.py.

output/charts/Primera_prueba_linea_temporal_interactiva.html: explorador temporal que incorpora baseline y v1. Contiene los datos embebidos, con 811 intervalos del baseline y 496 de v1 sobre todo el fichero, incluidos tramos excluidos. Por defecto muestra v1. Permite comparar ambos, acercar/alejar, arrastrar, ajustar la selección del resumen, saltar a un tiempo, consultar tabla y filtrar intervalos. Ofrece escalas de partido, parte, cinco minutos, minuto, diez segundos y segundo. Mantiene el zoom al cambiar de algoritmo; las estadísticas se calculan en ventanas evaluables y los tramos excluidos se traman. El fin de intervalo de la tabla es exclusivo.

Generador del explorador: tmp/build_interactive_timeline.py. Si cambia algún CSV hay que regenerar el HTML: no lo lee dinámicamente. El parámetro ?example=1 enfoca 25:04–25:13; ?test=1 ejecuta comprobaciones que pasaron en Chrome. El generador vive fuera del repo: conservarlo o trasladarlo si se prepara un paquete reproducible.

### Visor espacial SVG/XML de intervalos

Generador: Proyecto/starter/visualize_atd_interval.py. El usuario pidió inicialmente un XML interactivo; se entregó SVG, que es XML y puede ejecutar interacción en navegador si se abre directamente.

- Proyecto/evaluation/reports/ATD_2507_2510_interactivo.svg: 76 frames, 109993 bytes.
- Proyecto/evaluation/reports/ATD_2507_3000_interactivo.svg: 7326 frames, 9107318 bytes.
- Proyecto/evaluation/reports/ATD_2300_3000_interactivo.svg: 10501 frames, 13013025 bytes.

Incluye ambos extremos temporales. Representa campo escalado 1053 × 680, jugadores por equipo, balón y distancias; tabla de los 46 tracks incluyendo ausentes, selección de jugador y líneas de distancia. Flechas avanzan un frame, espacio reproduce y las velocidades son 0,25 a 4. El anillo amarillo marca al más cercano, no al poseedor confirmado. No interpola; X crece hacia la derecha y Y hacia abajo. Los números son tracks, no dorsales. Las comprobaciones ?test=1 pasaron, incluyendo ausencia de balón.

### Visor HTML de todo el ATD táctico: último entregable

Archivo: Proyecto/evaluation/reports/ATD_completo_interactivo.html, 81073863 bytes, unos 81 MB. Generador: Proyecto/starter/visualize_atd_full.py, que reutiliza la plantilla del generador SVG.

Contiene los 199319 frames tácticos completos, del 0 al 199318; último instante 132:52,72. No incluye el broadcast. Conserva los tres canales de los 46 tracks y los tres del balón en float64, incluidos NaN, sin reducción de fotogramas ni interpolación. Empaqueta los datos en 195 bloques de 1024 frames comprimidos con gzip y base64. Chrome los descomprime localmente con DecompressionStream; mantiene una caché LRU de seis bloques. Es autocontenido y funciona sin servidor ni conexión.

Permite saltar por tiempo mm:ss.cc (también coma decimal), por número de frame, al inicio, primera parte, segunda parte o 25:07; muestra el contexto de parte/descanso. Comienza en frame 11185, 07:27,40, pero su barra abarca todo el vídeo. Flechas permiten avanzar frame a frame; reproducción hasta 16 veces con reloj real. A velocidades altas se pueden omitir dibujos intermedios para mantener el tiempo; los datos y el avance manual conservan todos los frames.

Las navegaciones asíncronas priorizan la petición más reciente y comparten cargas pendientes. Las pruebas ?test=1 pasaron en Chrome: cobertura, frames de referencia incluidos extremos y frontera 1023/1024, distancia float64 exacta de T41 en 25:07, render inicial/final, salto temporal, navegación concurrente, 20 líneas de distancia y caché acotada. Evidencias internas: tmp/atd-full-dom.html y tmp/atd-full-preview.png.

Este visor muestra tracking y distancias, **no la posesión confirmada de v1**. El explorador temporal de posesión es otro HTML. No confundir ambos productos.

Para abrirlo, usar directamente Chrome con el archivo local; algunas previsualizaciones bloquean los scripts y fueron la causa de problemas de reproducción anteriores. Dirección local del visor completo:

```text
file:///C:/Users/ruben/OneDrive/Escritorio/MoreThanAHack/Proyecto/evaluation/reports/ATD_completo_interactivo.html
```

Chrome está instalado en C:\Program Files\Google\Chrome\Application\chrome.exe. Las pruebas se hicieron con un perfil temporal y modo headless; no es necesario para el uso normal. El SVG también debe abrirse directamente como documento, no insertado como imagen.

### Otros archivos existentes

Proyecto/SMART_TAGGING.md, smart_tagging_timeline.html y homografia-esquema.svg ya estaban presentes o procedían de otro hilo de trabajo. No atribuir su creación a esta secuencia ni modificarlos sin necesidad. SMART_TAGGING.md documenta los eventos; consultar su contenido si se trabaja en esa fuente.

## 10. Cómo reproducir y continuar

Entorno comprobado: Python 3.12.0, numpy 2.4.0, pandas 3.0.2. También están disponibles Pillow y fitz/PyMuPDF. No se creó un entorno virtual. matplotlib, plotly y reportlab no estaban disponibles; la instalación de reportlab falló por red. Los scripts de posesión no requieren decodificar el vídeo ni kloppy. Algunos notebooks originales sí necesitan dependencias adicionales.

Desde la raíz de Proyecto, manteniendo tactical y broadcast en la carpeta padre:

```powershell
python starter/possession_v1.py --data-dir ..
python evaluation/validate_submission.py evaluation/results/algoritmo_v1.csv
python evaluation/run_evaluation.py --no-detail
python -m unittest discover -s tests -p test_possession_v1.py
python starter/visualize_atd_interval.py --data-dir .. --start 23:00 --end 30:00
python starter/visualize_atd_full.py --data-dir ..
```

Para reconstruir la primera prueba sin alterar el baseline original, desde Proyecto:

```powershell
$env:MTAH_DATA_DIR = (Resolve-Path '..').Path
python -c "from starter.baseline import build,smooth,write_submission; write_submission('evaluation/results/primera_prueba.csv',smooth(build(),50))"
```

Para regenerar el explorador comparativo, desde MoreThanAHack:

```powershell
python tmp/build_interactive_timeline.py
```

El generador HTML completo vuelve a empaquetar todo el ATD y produce un archivo grande. No hace falta ejecutarlo para abrir el resultado existente. Conservar los generadores de tmp si se reorganiza la carpeta; hoy no están incluidos en el repositorio Proyecto.

Al clonar hubo un fallo de certificado con OpenSSL. Se resolvió usando el backend schannel de Git solo para el comando de clonado, sin desactivar verificación SSL ni cambiar configuración global. No es un problema del algoritmo.

## 11. Próximos pasos razonables, todavía no implementados

No se ha acordado una segunda regla concreta. Los candidatos son detectar balón parado y reinicios, exigir contacto sostenido para evitar cambios espurios de un solo frame, estudiar la incertidumbre causada por jugadores ausentes y valorar Smart Tagging como pista débil. La ausencia del balón no demuestra por sí sola una interrupción. Los intervalos automáticos solapados tampoco permiten etiquetar D sin más.

Si se cambia la lógica, mantener v1 y baseline para comparar; documentar una regla general en lugar de introducir excepciones manuales para 25:07–25:10. Validar el CSV, ejecutar pruebas relevantes y medir sobre la referencia pública reconociendo su escaso tamaño. La detección de D es especialmente importante porque v1 no produce ninguna D y mantiene posesión indefinidamente durante datos ausentes o interrupciones.

El vídeo es opcional para lograr una primera solución válida y no se ha usado como entrada del algoritmo. Si aporta valor más adelante, habrá que resolver un objetivo concreto de visión o validación y respetar las restricciones del concurso. No afirmar que el modelo ha aprendido: v1 es una regla determinista, sin entrenamiento.

Para cualquier continuación: leer este documento, comprobar git status y los archivos reales, distinguir tracking observado de control confirmado y de referencia de evaluación, y explicar al usuario las consecuencias de cada cambio con lenguaje sencillo.

