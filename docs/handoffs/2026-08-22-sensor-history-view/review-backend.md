# backend review — Historial de sensores

Slug: `2026-08-22-sensor-history-view` · Revisado: `backend/sensors/{api,serializers,aggregation,urls,tests}.py`,
`backend/sensors/management/commands/seed_sensor_readings.py`, `backend/sensors/fixtures/initial_sensors.json`,
`backend/backend/urls.py`, `Makefile`, `backend/makefile`.

## Verdict

CHANGES REQUESTED — 2 hallazgos bloqueantes, 10 no bloqueantes.

La rebanada es sólida: el contrato se honra endpoint por endpoint (verificado contra datos
reales sembrados, no solo contra tests), el ownership no tiene fugas —incluido el caso sutil
del lote propio bajo otra finca—, el bucketing coincide con la tabla del contrato en los
**cuatro límites exactos**, los agregados no se inflan por joins, y el export streamea de
verdad con un cursor de servidor. Lo que bloquea es que `make test` **no pasa de forma
reproducible** (un test del seeder es aleatorio y falló en mi primera corrida, contradiciendo
el titular del handoff) y que un parámetro documentado en el contrato (`page_size`) no tiene
ninguna aserción.

## How this was verified

- Leídos en orden: `backend/CLAUDE.md`, `CLAUDE.md` raíz, `docs/ARCHITECTURE.md` §Backend,
  `contract.md`, `acceptance-criteria.md`, `plan.md` §0–§1, `backend.md`.
- `make test` desde `backend/` — **corrida 1: `FAILED (failures=1)`** sobre 145 tests;
  corrida 2 (idéntica, sin cambios): `OK`, 145 tests. Ver **B1**.
- `ruff check` sobre los 7 archivos de la rebanada: `All checks passed!`.
  `ruff check .` en todo el backend: 177 errores, **ninguno** en archivos de esta rebanada
  (deuda preexistente, coincide con *Gotchas* 8).
- `makemigrations --check --dry-run` → `No changes detected`. `sensors/migrations/__init__.py`
  y `sensors/management/__init__.py` + `commands/__init__.py` presentes. `sensors/views.py`
  sigue siendo el stub. Sin `ViewSet`/`router` de DRF (los `SnippetViewSet` de
  `wagtail_hooks.py` son preexistentes y ajenos a la API).
- Peticiones reales contra la base de dev sembrada (144 026 lecturas, `APIClient` +
  `force_authenticate`) sobre los seis endpoints: sobre `{count,page,page_size,results}` sin
  `next`/`previous`, `value` como `float`, `recorded_at` terminado en `Z`, `bucket_seconds`
  presente, `Content-Disposition` con `filename` + `filename*`, primeros bytes del CSV
  `ef bb bf` (BOM) seguidos de la cabecera, JSON de export válido.
- SQL inspeccionado: `ORDER BY "recorded_at" DESC, "id" DESC` presente de verdad.
- `bucket_size_for` evaluado en los límites exactos (2, 8, 40 días y sus vecinos por
  0.0001 días): 900 / 3600 / 21600 / 86400 — coincide con la tabla del contrato.
- Inflación de promedios descartada: `build_plot_averages` vs. un `Count`/`Avg` crudo
  independiente por `(plot, variable)` → idénticos (671 muestras, 39.0136928…) en tres pares.
- Coste de los exports medido con `CaptureQueriesContext`: **3 queries** (ownership + `COUNT` +
  `DECLARE "_django_curs_…" NO SCROLL CURSOR WITH HOLD`) → el streaming y la constancia de
  AC20 son reales, aunque ningún test los fija (ver **N9**).
- Paginación sin desempate ejercitada a mano sobre datos reales (5 344 filas, 49 filas por
  timestamp): páginas 1 y 2 **no** se solapan ni con `-id` ni sin él en ese plan — ver **N2**.
- `page_size` probado en vivo con `5 / 100 / 1000 / 0 / -3 / abc` → 5 / 100 / 100 / 20 / 20 / 20.
- Tasa de fallo de **B1** estimada con 2 000 simulaciones Monte Carlo de la curva del seeder:
  **1.8 %** por corrida.
- Sin ningún comando `git`; sin `python manage.py` fuera de contenedor.

## Blocking

### B1 — `backend/sensors/tests.py:1075` (+ causa raíz en `backend/sensors/management/commands/seed_sensor_readings.py:45`): test aleatorio; `make test` falla ~1 de cada 55 corridas

`test_solar_radiation_is_dark_at_night_and_peaks_around_midday` termina en:

```python
brightest = max(readings, key=lambda reading: reading[1])
self.assertIn(brightest[0].hour, range(11, 14))
```

**Escenario de fallo concreto (observado, no hipotético).** Primera corrida de `make test` en
esta revisión, sin tocar una línea:

```
FAIL: test_solar_radiation_is_dark_at_night_and_peaks_around_midday
  File "/app/sensors/tests.py", line 1075, in ...
    self.assertIn(brightest[0].hour, range(11, 14))
AssertionError: 10 not found in range(11, 14)
Ran 145 tests in 9.137s
FAILED (failures=1)
```

La segunda corrida, idéntica y sin cambios, dio `OK`.

**Por qué.** El test invoca `call_command("seed_sensor_readings", days=2, verbosity=0)` **sin
`seed=`**, así que `seed_sensor_readings.py:104` hace `random.Random(None)` y se resiembra
desde el SO en cada corrida. La curva de `solar_radiation`
(`seed_sensor_readings.py:44-45`) es casi plana en el entorno del mediodía —`base` vale 779
W/m² a las 10:00 y 900 a las 12:00— mientras el ruido es `gauss(0, base*0.06)`, es decir
σ ≈ 47–54 W/m², **del mismo orden que la diferencia entre las horas candidatas**; encima el
`clamped(..., 0, 950)` empata artificialmente los picos. Con 2 días × 96 lecturas/día el
`argmax` cae de hecho al azar entre las 10:00 y las 15:00. Simulando la misma generación
2 000 veces, la aserción falla el **1.8 %** de las veces (y `days=30` en un `make loaddata`
real lo empeora, porque hay más sorteos cerca del pico).

**Impacto.** `make test` no es reproducible → CI en rojo intermitente, y sobre todo el titular
del handoff (`backend.md:8`, *"`make test`: **145 tests verdes**"*) y el preámbulo del
`## AC self-check` (`backend.md:65`, *"`make test` = los 145 tests"*) **no son reproducibles
tal como están escritos**.

**Arreglo sugerido** (cualquiera de los dos):
1. Pasar `seed=<n fijo>` en la llamada del test —el flag ya existe y
   `test_the_seed_flag_makes_the_series_reproducible` demuestra que funciona—; con eso el
   `argmax` queda fijado y el test sigue midiendo lo que dice medir.
2. O aseverar sobre un estadístico robusto al ruido en vez del `argmax` de una sola lectura:
   p. ej. `mean(valores de 11:00–13:00) > mean(valores de 07:00–09:00)` y
   `> mean(valores de 16:00–18:00)`, que es lo que la AC realmente quiere ("pico al mediodía").

Y actualizar `backend.md:8`/`:65` una vez que la suite pase de forma reproducible.

### B2 — `backend/sensors/api.py:100-102` + `backend/sensors/tests.py:487-494`: `page_size` es comportamiento del contrato y no tiene ninguna aserción

`SensorHistoryPagination` declara `page_size_query_param = 'page_size'` y `max_page_size = 100`,
y el contrato lo documenta explícitamente (`contract.md:83-84`: *"`page` (int, 1-based) y
`page_size` (int, default 20, máx 100)"*). El handoff lo reafirma como parte del cable
(`backend.md:145`, *Gotchas* 6).

El único test que envía el parámetro es:

```python
def test_the_query_count_does_not_grow_with_the_page_size(self):
    self.record_series(25)
    with self.assertNumQueries(3):
        self.history("history-readings", page_size=5)
    with self.assertNumQueries(3):
        self.history("history-readings", page_size=100)
```

…y **no mira el cuerpo**. `grep -n "page_size" sensors/tests.py` confirma que las únicas otras
apariciones (`:317`, `:320`) son sobre la respuesta *por defecto*, sin parámetro.

**Escenario concreto de regresión no detectada.** Borra `page_size_query_param` y
`max_page_size` de `sensors/api.py:101-102`. La suite entera de 145 tests **sigue en verde**:
las dos ramas del test de arriba siguen costando 3 queries con el tamaño por defecto 20, y
25 filas sembradas caben igual. Sin embargo el cable cambia de forma observable:
`GET .../history/readings/?page_size=5` pasa de devolver `{"page_size": 5, "results": [5 filas]}`
a `{"page_size": 20, "results": [20 filas]}` — el control de paginación del frontend, que se
alimenta de `page_size` para calcular `itemsPerPage`, empezaría a mentir sobre cuántas filas
hay por página. Y quitar solo `max_page_size` dejaría a `?page_size=100000` serializando el
set completo sin que nada lo note.

Verifiqué en vivo que **hoy el comportamiento es correcto**
(`5 → 5`, `100 → 100`, `1000 → 100`, `0/-3/abc → 20`): esto es estrictamente una laguna de
cobertura sobre comportamiento nuevo y documentado en el contrato, no un bug de salida.

**Arreglo.** Un test que envíe `page_size=5` y asevere `body["page_size"] == 5` y
`len(body["results"]) == 5`, y otro que envíe `page_size=1000` y asevere que el sobre reporta
`100` (el tope), en `SensorHistoryReadingsTests`.

## Non-blocking

### N1 — `backend/sensors/api.py:171` / `aggregation.py:74-77`: el origen de los buckets es el `date_from` crudo, así que `t` sale con microsegundos

Declarado por el ingeniero (`backend.md:128-132`, *Gotchas* 2) y confirmado en vivo con el
rango por defecto: `{"t": "2026-08-16T03:04:15.283117Z", "value": 34.0763, "sample_count": 4}`.
El contrato (`contract.md:151`) ejemplifica `"2026-08-15T00:00:00Z"`. No rompe nada —el
frontend rellena huecos con `t + bucket_seconds`— pero significa que dos peticiones del "mismo"
rango separadas por 1 ms producen `t` distintos, lo que ensucia cualquier caché por valor y
hace ilegible el eje si el cliente olvida alinear. Sugerencia: alinear el origen en el servidor
(`date_from` truncado al múltiplo de `bucket_size`) y dejar de depender de la disciplina del
cliente; si se prefiere el comportamiento actual, conviene escribirlo en `contract.md`.

### N2 — `backend/sensors/tests.py:341-349`: el test del desempate `-id` es probabilístico, no determinista

`test_readings_sharing_a_timestamp_page_deterministically` es buena idea y **el desempate está
de verdad en el SQL** (lo verifiqué: `ORDER BY "recorded_at" DESC, "id" DESC`). Pero el test no
lo *fija*: depende de que PostgreSQL elija planes distintos para `LIMIT 20` y
`LIMIT 20 OFFSET 20`. Ejercité el escenario a mano sobre los datos sembrados (5 344 filas,
49 empatadas por timestamp) comparando `order_by('-recorded_at')` contra
`order_by('-recorded_at','-id')`: **ambos dieron 0 solapamientos**. Es decir, quitar `-id` de
`READING_ORDER` puede perfectamente dejar el test en verde. Sugerencia: añadir una aserción
directa —`self.assertEqual(READING_ORDER, ("-recorded_at", "-id"))` o
`assertIn('"id" DESC', str(queryset.query))`— junto a la prueba de comportamiento actual.

### N3 — `backend/sensors/tests.py:569-575`: los límites exactos de los tiers de bucket no están cubiertos

`test_the_bucket_size_follows_the_span_of_the_range` usa 1 / 7 / 30 / 60 días, todos cómodamente
dentro de su tier. Los bordes del contrato son 2, 8 y 40 días exactos. Verifiqué el código y
`bucket_size_for` los resuelve **correctamente** (`<=`, `aggregation.py:38-41`), pero un cambio
de `<=` a `<` no rompería ningún test. Añadir `(2, 900), (8, 3600), (40, 21600)` al `subTest`
cuesta tres líneas.

### N4 — `contract.md` no se actualizó pese a las tres desviaciones

El propio contrato se declara autoridad y fija el procedimiento (`contract.md:7-9`):
*"si un lado no puede honrarlo, **se actualiza aquí** y el otro lado se ajusta"*. Las tres
desviaciones quedaron solo en `backend.md`. Como el frontend se construye **en paralelo contra
`contract.md`**, quien lo lea seguirá creyendo que `variables` ignora `date_from`/`variable` en
vez de validarlos. Recomiendo que el orquestador amplíe `contract.md` §1 con la nota de la
desviación 1 (una sola frase). *Veredicto sobre las tres desviaciones:*
- **1 (validar los params compartidos también en `variables`) — ACEPTAR.** Resuelve un choque
  real entre `contract.md:61` y AC19 a favor de la AC, y es la dirección segura (falla ruidoso
  en vez de silencioso). Verificado en vivo: `?plot=` vacío sigue dando 200 gracias a
  `allow_null=True` (`serializers.py:20`), así que el riesgo práctico para el frontend es nulo.
- **2 (`APIView` a mano en vez de `ListAPIView`) — ACEPTAR el resultado, corregir la
  justificación** (ver N5). Forma del cable y códigos verificados idénticos, incluido el 404 de
  DRF más allá de la última página.
- **3 (el tope de export es inalcanzable con la semilla por defecto) — ACEPTAR**: es un error
  del plan §1.7, bien diagnosticado y con receta de reproducción. Debe viajar a QA como
  prerrequisito de AC16, no quedarse solo en *Gotchas*.

### N5 — `backend.md:54-56`: la desviación 2 se apoya en una regla que no existe

Dice *"la regla dura del repo es una subclase de `APIView` por endpoint"*. Esa regla **no está
en `backend/CLAUDE.md`** (lo único que dice sobre el tema, línea 14, es *dónde* viven las
vistas), y `farm/api.py` la contradice: `FarmListAPIView`/`FarmPlotListAPIView` son
`generics.ListAPIView` y `PlotDetailAPIView` es `generics.RetrieveAPIView`. El código
entregado está bien y bien probado; lo que hay que corregir es citar una regla inexistente
como razón para apartarse del plan. Si el equipo la quiere, hay que escribirla (ver
*Proposed improvements*).

### N6 — cobertura de ownership desigual entre endpoints

`test_a_plot_of_another_farm_of_the_same_owner_is_not_found` existe en `variables` (`:267`),
`readings` (`:531`) y `series` (`:630`), pero **no** en `plot-averages` ni en los dos export
—precisamente las tres superficies que exportan o comparan datos de toda la finca—. El camino
es compartido (`resolve_history_scope`, `api.py:62-78`) y lo verifiqué en vivo (`404
{"detail": "Not found."}` para un lote de la finca 2 pedido bajo `farms/1/`), así que no hay
fuga; es solo que la red de seguridad no cubre las tres superficies donde más dolería.

### N7 — `backend/sensors/management/commands/seed_sensor_readings.py:109-110`: la rejilla solo es estable si el intervalo divide a 60

`newest -= timedelta(minutes=newest.minute % options['interval_minutes'])` alinea dentro de la
hora. Con `--interval-minutes 7`, dos corridas separadas por una hora producen rejillas
distintas y `--seed` deja de reproducir la serie (que es justo lo que el flag promete).
Además `--interval-minutes 0` revienta con `ZeroDivisionError` en `:109`. Es un comando de
desarrollo, así que basta con validar el argumento (divisor de 60 y > 0) o documentar la
restricción en el `help`.

### N8 — `backend/sensors/api.py:89-90`: `iso_utc` conserva los microsegundos en los exports

`recorded_at` sale como `2026-08-22T14:30:00.123456Z` si la lectura los trae. Los tests nunca
lo ejercitan (`cls.now` hace `replace(microsecond=0)`, `tests.py:171`) y el seeder tampoco los
genera, así que hoy no se ve; con ingesta real por `x-api-key` sí. El contrato ejemplifica
precisión de segundo (`contract.md:215`). Cosmético y consistente entre CSV, JSON y `readings`.

### N9 — los dos export no tienen `assertNumQueries`

Declarado con honestidad en `backend.md:115-116`. Lo medí yo: **3 queries** exactas en ambos
(ownership + `COUNT(*)` + `DECLARE … NO SCROLL CURSOR WITH HOLD`), o sea que la afirmación es
cierta *y* el streaming es real. Fijarlo cuesta un `with self.assertNumQueries(3):` alrededor
de la lectura de `streaming_content` y cierra AC20 del todo, ya que un export **es** un
endpoint de lectura del historial.

### N10 — el ✓ de AC21 es más ancho que los tests que cita

Cubre `readings` (inactivo + nulo), `series` (inactivo), `plot-averages` (inactivo) y `export`
(nulo). Faltan: **nulo** en `series` y en `plot-averages`, e **inactivo** en el export. El
filtro vive en un único sitio (`aggregation.py:52-53`), así que el comportamiento se sostiene
—no es un hallazgo de corrección—, pero la matriz 4×2 está cubierta a la mitad y el ✓ afirma
las cuatro superficies. Vale la pena porque un `Avg` que dejara entrar nulos inflaría
`sample_count` sin cambiar `average`, un fallo silencioso.

## Verified — focus areas

**Contrato, endpoint por endpoint** (petición real + test):

| Punto del contrato | Resultado |
|---|---|
| Sobre `{count,page,page_size,results}` | ✔ exacto; `set(body)` fijado en `tests.py:317` |
| `next`/`previous` ausentes | ✔ `api.py:104-115`; verificado en vivo |
| `value` número JSON, no string | ✔ `FloatField` (`serializers.py:68`) + `float()` en ambos export (`api.py:281`, `:329`); en vivo `type == float` |
| `recorded_at` termina en `Z` | ✔ en vivo `"2026-08-23T02:45:00Z"` |
| `bucket_seconds` en cada serie | ✔ `aggregation.py:94` |
| Buckets vacíos omitidos (ni `0` ni `null`) | ✔ por construcción (`GROUP BY`), fijado en `tests.py:552-567` |
| Series ordenadas por `name`, puntos por `t` asc | ✔ `aggregation.py:81` |
| Dos variables con el mismo `semantic_key` = dos series | ✔ `tests.py:586-596` |
| `plot-averages` ordenado por `plot_name`, `variable_name`; lote sin datos ausente | ✔ `aggregation.py:120-123`, `tests.py:697` |
| `series` sin `plot` → 400 | ✔ `api.py:168-169`, `tests.py:625` |
| `plot-averages` ignora `plot` | ✔ `api.py:188`, `tests.py:723` |
| 401 sin token en los seis | ✔ 5 clases de test |
| 404 genérico `{"detail": "Not found."}`, nunca 403 | ✔ `get_owned_or_404`; verificado en vivo |
| 400 con mapa `{campo: [mensajes]}` en rango inválido | ✔ 5 tests |
| Filtros de datos (`is_active`, `value__isnull=False`, `gte`/`lt`) | ✔ `aggregation.py:51-57` |
| Tabla de tiers de bucket | ✔ **en los cuatro límites exactos** (ver *How this was verified*) |
| CSV: BOM antes de la cabecera | ✔ bytes reales `ef bb bf` + `recorded_at,plot,…` |
| CSV/JSON: cabecera y claves | ✔ `CSV_HEADER` (`api.py:36-44`) y las 10 claves de `SensorReading` menos `id` |
| `Content-Disposition` con `filename` + `filename*` | ✔ en vivo, `historial-sensores-finca-el-tesoro-20260816_20260823.csv` |
| Tope: cuenta **antes** de emitir, 400 con `code/count/limit` | ✔ `api.py:223-239` se ejecuta antes de construir la `StreamingHttpResponse`; nunca hay archivo a medias |
| JSON válido con cero filas | ✔ `[]` (`tests.py:872`) |
| Export streamea de verdad | ✔ `DECLARE … NO SCROLL CURSOR WITH HOLD` observado; memoria constante |
| Dos rutas de export, no `?format=` | ✔ `urls.py:35-46` |

**Ownership.** Intenté las tres rutas de fuga y ninguna abre:
1. Finca ajena → 404 aunque tenga datos (`tests.py:534-546`).
2. **Lote propio colgado de otra finca que la del `farm_id`** → 404: el lookup lleva
   `pk=plot_id, farm_id=farm_id, farm__owner__user=request.user` en la **misma** llamada
   (`api.py:72-77`), así que las tres condiciones se evalúan juntas. Verificado en vivo con un
   lote de la finca 2 pedido bajo `farms/1/`.
3. Lote de otro dueño en una finca propia → imposible por FK, y de todos modos el lookup lo
   corta. El cuerpo del 404 viene de `NotFound` de DRF, **sin nombrar el modelo** (a diferencia
   de `get_object_or_404` de Django) — que es el motivo de existir de `get_owned_or_404`.
   El scope nunca pasa por `request.user.farmer`.

**ORM / DRF.**
- N+1 en `readings`: cubierto por `select_related('sensor_variable__env_variable',
  'sensor_variable__sensor__plot')` (`api.py:151-154`), y el `assertNumQueries(3)` **sí lo
  detectaría**: las 25 filas del test cuelgan del mismo `sensor_variable`, pero DRF instancia
  un modelo por fila y sin `select_related` cada una dispararía sus propias cargas perezosas.
- `distinct` en `variables` (`api.py:134`): necesario y presente. Las dos condiciones sobre
  `field_sensor_variables__…` van en **una sola** llamada a `.filter()`, así que comparten el
  join: exige que *el mismo* `FieldSensorVariable` sea de un sensor activo **y** del scope. Si
  se separaran en dos `.filter()` encadenados, la finca podría colar una variable que solo un
  sensor inactivo mide. Hoy está bien; conviene no tocarlo sin releer esto.
- **Inflación de agregados descartada empíricamente**, no solo por inspección: toda la cadena
  `SensorMeasurement → FieldSensorVariable → FieldSensor → Plot` y `→ EnvironmentalVariable`
  es FK directa (many-to-one), y el contraste contra un `Count`/`Avg` independiente dio
  cifras idénticas.
- `Meta.ordering` explícito en los modelos expuestos (`SensorMeasurement`, línea 461;
  `EnvironmentalVariable`, línea 74) — sin cambios de modelo, sin migración pendiente.
- El `order_by(...)` explícito de `build_series`/`build_plot_averages` limpia el
  `Meta.ordering` por defecto, así que no se cuela `recorded_at` en el `GROUP BY`.
- `assertNumQueries` **que sí valen**: variables 2, readings 3 (con `page_size` 5 y 100),
  series 2 (con 1 y con 3 variables), plot-averages 2 (con 2 y con 12 lotes). Los cuatro
  llevan el comentario que nombra cada query y la advertencia de no subir el número. El de
  plot-averages es especialmente honesto: construye una segunda finca de 12 lotes de verdad.

**Cumplimiento de `backend/CLAUDE.md`.** Vistas en `api.py` (`views.py` sigue siendo el stub);
`permission_classes = [IsAuthenticated]` **explícito en las seis** (`api.py:119, 141, 164, 181,
243, 288`); scoping por lookup, nunca `request.user.farmer`; recurso anidado resuelto con
404-por-lookup; `Meta.ordering` presente; guard clauses en vez de anidamiento
(`api.py:124-127`, `:168-169`, `:249-250`); identificadores sin abreviar (`sensor_variable`,
`measurements`, `attributes`, `sensor_variables`); comentarios que explican solo el *porqué*
(`api.py:105-107`, `:146-148`, `:229-230`, `aggregation.py:11-13`, `serializers.py:15-17`) sin
narrar el diff. Montaje con tupla de namespace en `backend/urls.py:43`. Sin `pip install` en
caliente. Sin Celery en esta rebanada.

## AC self-check audit

Verdicto sobre cada ✓ del handoff (`backend.md:63-121`):

| AC | ✓ del ingeniero | Mi verdicto |
|---|---|---|
| AC1 | Fixtures + seeder dan datos a los lotes 1–4; lote 29 vacío; 30 días | **Confirmado.** Comprobé además que farm 1 = lotes {1, 2, 29} y farm 2 = {3, 4}, así que `SEEDED_PLOTS` cubre *todos* los lotes con sensores de ambas fincas y el 29 es el vacío que la AC pide. `test_the_default_span_covers_a_full_month_of_history` es determinista (2 881 lecturas × 15 min = 30 días exactos). |
| AC5 | Solo variables de sensores activos, acotable por lote | **Confirmado**, y reproducido en vivo: farm 1 devuelve exactamente las 4 variables reales y `other` está ausente porque solo la mide el sensor 4 (inactivo). |
| AC9 | 20 filas, `count`, orden, columnas | **Confirmado.** |
| AC10 | Desempate `-id` | **Confirmado en el código** (`-id` está de verdad en el `ORDER BY`), pero el test que lo respalda es probabilístico — ver **N2**. El ✓ es correcto; la red de seguridad, floja. |
| AC11 | `plot_name` viaja siempre; ocultar la columna es del frontend | **Confirmado y honesto** (dice explícitamente que el servidor no puede satisfacerla solo). |
| AC12 | Vacíos honestos en las tres superficies | **Confirmado.** |
| AC13 | CSV completo, no solo la página | **Confirmado**; el nombre de archivo generado coincide con el afirmado. |
| AC14 | JSON = mismas filas y orden | **Confirmado.** |
| AC15 | BOM + UTF-8 | **Confirmado**, con la salvedad de Excel **declarada** por el propio ingeniero. La honestidad aquí es ejemplar: nombra lo que no verificó. |
| AC16 | 400 con `code/count/limit` | **Confirmado** (tests con el tope parcheado a 2), y el aviso de que no se dispara con la semilla por defecto es cierto: probé un rango de 90 días sobre la finca 1 y devolvió 200 streameado, no 400. |
| AC17 | Finca ajena y lote de otra finca del mismo dueño → 404 | **Confirmado en vivo.** El ✓ acota correctamente los tests a "variables/readings/series"; ver **N6** por las tres superficies sin test. |
| AC18 | 401 en los seis | **Confirmado.** |
| AC19 | 400 nombrando el campo | **Confirmado**, los cinco tests existen y aseveran la clave culpable. |
| AC20 | Conteos constantes; exports sin test | **Confirmado**, incluida la parte que el ingeniero admite no haber fijado: medí los exports y dan 3 queries constantes. El ✓ es reproducible aunque incompleto en cobertura (**N9**). |
| AC21 | Inactivos y nulos fuera de las cuatro superficies | **Confirmado en comportamiento**; el ✓ es más ancho que los tests citados (**N10**). |

**Lo único no reproducible del handoff** es el titular de `backend.md:8` / `:65`
(*"145 tests verdes"*, *"`make test` = los 145 tests"*): mi primera corrida falló → **B1**.
El apartado *"Fuera de mi rebanada"* (AC2–AC4, AC6–AC8, AC22–AC24, `AC-A11Y-*`) está bien
delimitado; ninguna de esas AC depende de nada que el backend deba y no haya entregado.

## Proposed improvements

Reglas candidatas, solo reusables y de largo plazo. **No las apliqué** — el orquestador las
lleva al usuario.

1. **`backend/CLAUDE.md`** — *"Un test que dependa de `random` sin semilla fija es un test
   aleatorio: o pasas una semilla explícita al comando/factoría, o aseveras sobre un
   estadístico robusto (media de una ventana, monotonía) en vez de sobre el `argmax` o el
   extremo de una muestra ruidosa."* Es el patrón exacto de **B1** y reaparecerá en cuanto se
   siembren series para `predictions`.
2. **`backend/CLAUDE.md`** — *"Todo query-param que el contrato documente necesita un test que
   asevere su **efecto en el cuerpo**, no solo que la petición responda 200 o que el conteo de
   queries no cambie."* Cubre **B2**; un `assertNumQueries` alrededor de un parámetro no lo
   prueba.
3. **`backend/CLAUDE.md`** — *"En cualquier endpoint paginado, `order_by` debe terminar en un
   desempate único (`-id`): con solo un timestamp, PostgreSQL puede reordenar los empates entre
   la query de la página 1 y la de la página 2, y las filas se repiten o desaparecen. Y como el
   plan de PostgreSQL puede ocultar el fallo, el test que lo protege debe aseverar el
   `order_by` además del comportamiento."* (Propuesta 1 del ingeniero, `backend.md:207-209`,
   **con la segunda frase añadida por mí** a raíz de **N2**.)
4. **`backend/CLAUDE.md`** — *"Nunca uses `?format=` como discriminador propio: DRF reserva ese
   param (`api_settings.URL_FORMAT_OVERRIDE`) y devuelve 404 'Invalid format'. Un formato de
   descarga distinto = una `path()` distinta."* (Propuesta 2 del ingeniero — la respaldo tal
   cual; es una trampa cara y no evidente.)
5. **`backend/CLAUDE.md`** — *"Un `DecimalField` de DRF se renderiza como string. Todo valor
   numérico que alimente un gráfico o un cálculo en el cliente va como `FloatField` (o
   `float(...)`)."* (Propuesta 3 del ingeniero — la respaldo; ya hay dos precedentes en el repo
   y un `Plot.area_hectares` que demuestra el fallo.)
6. **`backend/CLAUDE.md`** — *"Al filtrar por una relación multivaluada con más de una
   condición, ponlas en **una sola** llamada a `.filter()` (comparten el join) y añade
   `.distinct()`; encadenar `.filter().filter()` crea un join por llamada y deja pasar filas
   que ninguna fila individual satisface."* Es la diferencia entre listar y no listar variables
   de sensores apagados en `SensorHistoryVariablesAPIView`, y ninguna regla del repo lo
   recoge hoy.
7. **`backend/CLAUDE.md`** — *"Los management commands de semilla se ejecutan dos veces: dentro
   de `@transaction.atomic`, borra el subconjunto que vas a recrear antes de `bulk_create`, y
   ancla los timestamps a una rejilla (no a `now()` crudo) para que `--seed` reproduzca de
   verdad la serie."* (Propuesta 4 del ingeniero — la respaldo.)
8. **`backend/CLAUDE.md`** — *"Las vistas de lista/detalle sencillas usan los genéricos de DRF
   (`ListAPIView`/`RetrieveAPIView`), como `farm/api.py`; baja a `APIView` solo cuando la vista
   arma su propia respuesta (streaming, sobres a medida). No existe una regla de
   'un `APIView` por endpoint'."* Escribirlo cierra la ambigüedad que produjo **N5**, en la que
   una desviación del plan se justificó con una regla no escrita.
9. **`CLAUDE.md` raíz (§Tests)** — *"Antes de tocar código, corre la suite del área para tener
   el baseline en números; al terminar, repórtalo como 'baseline N → M' y **corre la suite dos
   veces** antes de afirmar que está verde — una sola corrida no distingue 'pasa' de 'pasa casi
   siempre'."* (Propuesta 5 del ingeniero, **con la segunda mitad añadida por mí**: es lo que
   habría atrapado **B1** antes del handoff.)
10. **Spec del agente de plan (`.claude/agents/…`)** — *"Todo número de volumen que el plan use
    para justificar un caso límite ('90 días ≈ 69 000 filas → dispara el tope') debe derivarse
    del alcance real del seeder, no extrapolarse."* (Propuesta 6 del ingeniero — la respaldo:
    el error dejó AC16 sin forma de reproducirse en dev y solo se descubrió al implementar.)
11. **Spec del agente de contrato / del orquestador** — *"Una desviación del contrato aceptada
    se escribe **en `contract.md`**, no solo en el handoff de quien se desvía: el contrato se
    declara autoridad y el otro lado se construye en paralelo contra él."* Cubre **N4**; sin
    esto, cada rebanada acumula divergencias que solo conoce quien las cometió.
