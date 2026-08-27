# backend handoff — Historial de sensores

Slug: `2026-08-22-sensor-history-view` · Contexto: [`spec.md`](spec.md) · [`contract.md`](contract.md) · [`acceptance-criteria.md`](acceptance-criteria.md) · [`plan.md`](plan.md)

**Summary.** Seis endpoints de solo lectura bajo `api/sensors/` (variables, readings paginado,
series con `date_bin`, promedios por lote, export CSV/JSON en streaming), más las 10 filas
`FieldSensorVariable` nuevas y el comando `seed_sensor_readings` que por fin crea
`SensorMeasurement`. `make test`: **150 tests verdes** (baseline 59 + 91 nuevos), verificado
en **tres corridas seguidas** tras los arreglos de review (ver *Review fixes*).

## Review fixes

Ronda de review `review-backend.md`: los **2 bloqueantes** y **3 de los no bloqueantes**
(N2, N5 y el titular no reproducible). Solo cambió `backend/sensors/tests.py` y este doc —
**ninguna línea de `api.py`/`aggregation.py`/`serializers.py`/`urls.py`/el seeder**, porque los
cinco hallazgos eran de cobertura, determinismo o redacción, no de salida.

- **B1 — test aleatorio (`test_solar_radiation_is_dark_at_night_and_peaks_around_midday`).**
  Dos arreglos, no uno: la llamada al seeder pasa `seed=20260822`, y la aserción del pico dejó
  de mirar el `argmax` de una sola lectura para comparar **medias de ventana**
  (11–14 h contra 7–10 h y 16–19 h, helper `mean_between`). Hacía falta lo segundo: `--seed` fija
  la *secuencia* de ruido, pero la rejilla de timestamps se mueve con el reloj de pared en cada
  corrida, así que el `argmax` seguiría bailando. *Verificación*: 5 000 simulaciones Monte Carlo
  de la misma curva variando el origen de la rejilla → la aserción vieja falla **48 veces**
  (0.96 %), la nueva **0**; los márgenes son enormes (midday ≈ 865 W/m², mañana ≈ 502,
  tarde ≈ 174, con σ de la media ≈ 10). Sigue probando lo mismo: noche en cero + pico al mediodía.
  Y `make test` corrido **tres veces seguidas**: `Ran 150 tests … OK` las tres.
- **B2 — `page_size` sin aserciones.** Cuatro tests nuevos en `SensorHistoryReadingsTests`:
  `test_the_page_size_param_narrows_the_page` (5 → `page_size: 5` y 5 filas),
  `test_the_page_size_param_widens_the_page_up_to_the_cap` (100 → 100 filas de 100 sembradas),
  `test_a_page_size_above_the_cap_is_clamped_to_a_hundred` (1000 → 100 sobre 101 filas) y
  `test_an_unusable_page_size_falls_back_to_the_default` (`0`, `-3`, `abc` → 20, en `subTest`).
  Todos aseveran el **cuerpo** (`page_size` del sobre + `len(results)`), no el conteo de queries.
  *Verificación por mutación*: borrando `page_size_query_param` **y** `max_page_size` de
  `api.py` → 3 fallos; borrando **solo** `max_page_size` → 1 fallo (el del clamp). Antes de esto,
  las dos mutaciones dejaban la suite entera en verde.
- **N2 — el test del desempate `-id` era probabilístico.**
  `test_readings_sharing_a_timestamp_page_deterministically` ahora asevera la **secuencia exacta**
  de ids de las páginas 1+2 (25 lecturas con el mismo `recorded_at`, el borde de página cae dentro
  del empate), no un conjunto sin solapes; y se suma
  `test_the_reading_order_ends_in_a_unique_tie_break`, que fija `READING_ORDER` y el `ORDER BY`
  compilado (`"recorded_at" DESC, "id" DESC`) — esa es la aserción que **no puede** pasar por
  suerte del planificador. *Verificación por mutación*: con `READING_ORDER = ('-recorded_at',)`
  **fallan los dos**; antes no fallaba ninguno.
- **N5 — justificación de la desviación 2.** Reescrita: no existe ninguna regla
  "un `APIView` por endpoint" en `backend/CLAUDE.md`, y `farm/api.py` usa genéricos. La razón real
  es el encargo con el que se me despachó; queda dicho tal cual, con el contraejemplo del repo.
- **Titular "145 tests verdes".** Corregido a **150** en el *Summary* y en el preámbulo del
  *AC self-check*, ya con las tres corridas seguidas detrás.

**No atendidos a propósito** (no bloqueantes fuera del encargo de esta ronda): N1, N3, N4, N6–N10.
N4 (llevar las desviaciones a `contract.md`) es del orquestador; N3, N6, N9 y N10 son cobertura
adicional barata que recomiendo a quien retome la rebanada.

`make lint-backend` en los archivos de la rebanada: **All checks passed!**
(los ~174 errores de `ruff check .` siguen siendo deuda preexistente en archivos ajenos — *Gotchas* 8).

## Files changed

**Nuevos**
- `backend/sensors/aggregation.py`
- `backend/sensors/serializers.py`
- `backend/sensors/api.py`
- `backend/sensors/urls.py`
- `backend/sensors/management/commands/seed_sensor_readings.py`

**Modificados**
- `backend/sensors/fixtures/initial_sensors.json` (pks 43–52 de `fieldsensorvariable`)
- `backend/backend/urls.py` (montaje `api/sensors/` con tupla de namespace)
- `backend/sensors/tests.py` (+7 clases, 91 tests)
- `Makefile`, `backend/makefile` (`seed_sensor_readings` en `loaddata` + target `seed-sensors`)

**Sin migraciones.** No hay cambios de modelo; `makemigrations --check` dice `No changes detected`.
El índice `Index(['sensor_variable','recorded_at'])` ya existente cubre estas queries (plan §1.6).

## Contract

Todo **per `contract.md`** salvo lo listado en *Contract deviations*.

| Método + ruta | Nombre de `reverse()` |
|---|---|
| `GET /api/sensors/farms/<farm_id>/history/variables/` | `sensors:history-variables` |
| `GET /api/sensors/farms/<farm_id>/history/readings/` | `sensors:history-readings` |
| `GET /api/sensors/farms/<farm_id>/history/series/` | `sensors:history-series` |
| `GET /api/sensors/farms/<farm_id>/history/plot-averages/` | `sensors:history-plot-averages` |
| `GET /api/sensors/farms/<farm_id>/history/export/csv/` | `sensors:history-export-csv` |
| `GET /api/sensors/farms/<farm_id>/history/export/json/` | `sensors:history-export-json` |

Formas verificadas contra datos reales sembrados (no solo contra tests): sobre
`{count,page,page_size,results}` sin `next`/`previous`, `value` como número JSON,
`recorded_at` terminado en `Z`, series con `bucket_seconds` y buckets vacíos omitidos,
CSV con BOM y `Content-Disposition` con `filename` + `filename*`.

## Contract deviations

1. **Los seis endpoints validan los params compartidos; `variables` los *ignora* pero no los
   *acepta ciegos*.** El contrato dice de `variables`: *"Acepta solo `plot` (los demás params se
   ignoran)"*, mientras que **AC19** exige 400 en *cualquier* endpoint del historial ante un rango
   inválido. Resolución: `variables` corre el `SensorHistoryFilterSerializer` completo (una fecha
   ilegible o un `variable` fuera de las choices → 400) pero no aplica `date_from`/`date_to`/
   `variable` a su query. Impacto en el frontend: cero si solo manda `plot` o fechas válidas.
2. **Ninguna vista usa `generics.ListAPIView`.** El contrato (Decisions §1) y el plan §1.4
   contemplan `readings` como `ListAPIView`. Lo implementé con `APIView` porque así lo pedía el
   encargo con el que se me despachó ("un `APIView` por endpoint, sin ViewSets/generics/router").
   **No es una regla de `backend/CLAUDE.md`** —ahí no existe— y `farm/api.py` usa genéricos
   (`FarmListAPIView`/`FarmPlotListAPIView` son `ListAPIView`; `PlotDetailAPIView`,
   `RetrieveAPIView`), así que el repo no la respalda: si el equipo quiere una u otra convención,
   hay que escribirla. `SensorHistoryReadingsAPIView` es un `APIView` que instancia
   `SensorHistoryPagination` a mano (`paginate_queryset` + `get_paginated_response`). **La forma
   del cable y los códigos de estado son idénticos**, incluido el 404 de DRF al pedir una página
   más allá de la última.
3. **El tope de export no es alcanzable con la semilla por defecto** — ver *Gotchas* 4. Es un
   error del plan §1.7, no del contrato: el endpoint y su 400 funcionan y están cubiertos por tests.

## AC self-check

Uno por uno, con cómo lo verifiqué. `make test` = los 150 tests (tres corridas seguidas en verde);
"smoke" = petición real contra la base de dev sembrada con `make loaddata`.

- **AC1 ✓** — `SensorSeedDataContractTests` (fixtures + `seed_sensor_readings`) fija que los lotes
  1–4 miden y **tienen lecturas** de las 4 variables reales, y que `Lote Sin Mapear` (plot 29)
  devuelve `count: 0` y `[]` sin error. La cobertura de 30 días la fija
  `test_the_default_span_covers_a_full_month_of_history` (`newest - oldest == 30 días` exactos).
  Smoke: farm 1 = 5 352 lecturas en 7 días, 23 024 en 30 días.
- **AC5 ✓** (lado servidor) — `SensorHistoryVariablesTests`: solo variables de sensores **activos**,
  acotado por lote cuando se pasa `plot`, y la variable medida solo por un sensor inactivo está
  ausente. La opción "Todas las variables" es del frontend. Smoke sobre farm 1: exactamente las
  4 variables reales, `other` ausente (solo la mide el sensor 4, inactivo).
- **AC9 ✓** (servidor) — `test_the_first_page_holds_twenty_rows_and_the_total_count`,
  `test_the_rows_run_from_the_newest_reading_to_the_oldest`,
  `test_a_row_names_the_plot_the_sensor_and_the_variable` (fecha, lote, sensor, variable, valor,
  unidad en cada fila).
- **AC10 ✓** (servidor) — `test_the_second_page_continues_where_the_first_ended`,
  `test_readings_sharing_a_timestamp_page_deterministically` (25 lecturas con **idéntico**
  `recorded_at`: páginas 1+2 dan la secuencia exacta de ids, no solo un conjunto sin solapes) y
  `test_the_reading_order_ends_in_a_unique_tie_break`, que asevera el `ORDER BY` compilado.
  Con `-id` fuera de `READING_ORDER` **ambos fallan** (comprobado mutando el código).
  Los tamaños de página del contrato los fijan los cuatro tests de `page_size` (ver *Review fixes*).
- **AC11 ✓** (servidor) — `plot_name` viaja **siempre** en cada fila
  (`test_a_row_names_the_plot_the_sensor_and_the_variable`); ocultar la columna es decisión del
  frontend. El servidor no puede satisfacer AC11 por sí solo.
- **AC12 ✓** (servidor) — vacíos honestos: `test_a_plot_without_readings_returns_an_empty_list`
  (series `[]`), `test_the_plot_without_sensors_reports_an_empty_history` (`count: 0`, `results: []`),
  `test_the_json_export_of_an_empty_set_is_an_empty_array`. El estado vacío visible es del frontend.
- **AC13 ✓** (servidor) — `test_the_csv_carries_a_header_and_one_row_per_reading`,
  `test_the_csv_exports_the_whole_filtered_set_not_just_the_first_page` (25 sembradas → 26 líneas,
  no 20), `test_the_export_respects_the_filters`, `test_the_filename_names_the_farm_and_the_range`
  → `historial-sensores-finca-el-tesoro-20260801_20260822.csv`.
- **AC14 ✓** (servidor) — `test_the_json_export_is_an_array_with_the_same_rows_and_order`: mismas
  filas y mismo orden que el CSV, claves de `SensorReading` menos `id`, `value` float.
- **AC15 ✓** (servidor) — `test_the_csv_is_utf8_with_a_byte_order_mark_so_excel_reads_the_accents`
  comprueba el BOM y que `Radiación solar` / `W/m²` viajan intactos. **La apertura real en Excel
  no la verifiqué** (no tengo Excel); lo que está fijado es el BOM + UTF-8, que es la causa raíz.
- **AC16 ✓** (servidor) — `test_a_set_over_the_cap_is_rejected_naming_the_count_and_the_limit` y
  `test_the_json_export_honours_the_same_cap`: 400 con
  `{detail, code: "export_too_large", count, limit}`, sin archivo truncado. **Aviso**: con la
  semilla por defecto (30 días) ninguna finca supera 50 000 filas — ver *Gotchas* 4 para el
  comando que hace el caso reproducible en e2e.
- **AC17 ✓** — `test_a_farm_owned_by_someone_else_leaks_nothing` (crea datos en la finca ajena y
  aun así 404 con `{"detail": "Not found."}`), y `test_a_plot_of_another_farm_of_the_same_owner_is_not_found`
  en variables/readings/series. **Nunca 403.** Smoke: `GET farms/3/history/readings/` → 404.
- **AC18 ✓** — `test_it_requires_authentication` en las 5 clases de endpoint (los dos export en el
  mismo test). 401 en los seis.
- **AC19 ✓** — `test_a_range_wider_than_the_cap_is_rejected` (91 días),
  `test_a_range_that_ends_before_it_starts_is_rejected`, `test_an_unreadable_date_is_rejected_naming_the_field`,
  `test_an_unknown_variable_is_rejected_naming_the_field`, `test_an_invalid_range_is_rejected` (export).
  Todos 400 con el campo culpable como clave.
- **AC20 ✓** — `assertNumQueries`: variables **2**, readings **3** (y no crece con `page_size`
  5→100), series **2** (con 1 y con 3 variables), plot-averages **2** (finca de 2 lotes y de 12).
  Los dos export no llevan `assertNumQueries`: son 1 ownership + 1 `count()` + 1 cursor de
  servidor, constante por construcción pero **no fijado por un test**.
- **AC21 ✓** — `test_a_reading_of_an_inactive_sensor_is_absent`, `test_a_reading_without_a_value_is_absent`,
  `test_readings_of_an_inactive_sensor_never_enter_a_series`, `test_an_inactive_sensor_does_not_contribute`,
  `test_a_reading_without_a_value_is_absent_from_the_export`. Tablas, series, promedios y export.

**Fuera de mi rebanada** (frontend/QA): AC2–AC4, AC6–AC8, AC22–AC24 y todos los `AC-A11Y-*`.

## Gotchas

1. **`date_bin` funciona** — el spike del plan §1e pasó: `Value(timedelta, output_field=DurationField())`
   se adapta a `interval` en psycopg3 contra PostgreSQL 15.0.8. **No se usó el fallback**
   `TruncHour`/`TruncDay`; los cuatro tiers (900/3600/21600/86400 s) están vivos.
2. **El origen de los buckets es literalmente el `date_from` pedido** (así lo manda el contrato).
   Si el frontend manda `date_from` con milisegundos, los `t` salen con milisegundos
   (`2026-08-16T02:50:28.001920Z` en el smoke con el rango por defecto). Para etiquetas de eje
   redondas, **manda un `date_from` alineado** (inicio de hora/día). El relleno de huecos con
   `t + bucket_seconds` funciona igual con cualquier origen.
3. **`-id` como desempate no es cosmético.** Sin él la paginación repite/pierde filas: el seeder
   escribe todas las variables de un sensor en el mismo instante. Está en `READING_ORDER` y lo
   fija un test.
4. **El tope de export no se dispara con la semilla por defecto.** El plan §1.7 afirmaba que
   90 días sobre la finca 1 ≈ 69 000 filas; es falso porque el seeder solo escribe **30 días**
   (medido: 23 024 filas por finca en 30 días). Para reproducir AC16 de punta a punta:
   `docker compose exec backend python manage.py seed_sensor_readings --days 90`
   (≈ 432 000 filas, ~3 min) y luego pedir un rango de 90 días sobre la finca 1.
5. **Idiomas de los mensajes de error.** El `detail` del tope de export va en español (verbatim
   del contrato); los mensajes de validación de rango van en inglés, junto a los propios de DRF
   (`"Datetime has wrong format…"`). El frontend debería construir su copia i18n desde `code` y
   los campos, no desde `detail`.
6. **`page_size`** se acepta tal como lo documenta el contrato (default 20, máx 100): `5 → 5`,
   `100 → 100`, `1000 → 100` (acotado), y `0` / `-3` / `abc` → 20. Los cuatro casos están
   fijados por tests.
7. **`plot` en `plot-averages` se acepta y se ignora** a propósito (test que lo fija), para que el
   frontend pueda mandar el mismo query object a los cuatro endpoints de lectura.
8. **`ruff` en `backend/` tiene ~175 errores preexistentes** en archivos que no toqué
   (`sensors/models.py`, `admin.py`, `weather_station_providers/`…). Los **7 archivos de esta
   rebanada pasan limpios**; no limpié la deuda ajena para no inflar el diff.

## Decisions

- **Sin `django-filter`**: 4 params, 3 con validación cruzada, y `DEFAULT_FILTER_BACKENDS` es
  global (tocarlo alcanza a `farm/`). `serializers.Serializer` a mano.
- **Paginación solo a nivel de vista**, nunca `DEFAULT_PAGINATION_CLASS`.
- **`aggregation.py` es la capa de datos** (`DateBin`, `bucket_size_for`, `history_measurements`,
  `build_series`, `build_plot_averages`); `api.py` solo orquesta y serializa.
- **Curvas realistas en el seeder** (senos diarios + `gauss`), no ruido uniforme: radiación 0 de
  noche y pico al mediodía, humedad en anti-fase con temperatura, humedad de suelo con ciclo de
  riego de 3 días. Los timestamps se **alinean a la rejilla del intervalo** (`:00/:15/:30/:45`)
  para que `--seed` reproduzca de verdad la serie.
- **La semilla expone los caminos infelices**: el `sensor_variable` de pk más bajo pierde sus
  últimas 6 h (hueco en el gráfico) y el de pk más alto lleva filas `value=None`.
- **Fuera de alcance**: índices nuevos (medición, no especulación), ingesta real por `x-api-key`,
  ordenamiento server-side de la tabla, cualquier cosa en `frontend/` o `e2e/`.

## How to load the seed

Desde `backend/` (el stack docker arriba):

```bash
make loaddata      # fixtures + seed_weather_readings + seed_sensor_readings (30 días, ~144 000 filas, ~1 min)
make seed-sensors  # solo re-sembrar las lecturas de sensores
```

Ya lo corrí contra la base de dev: **144 026 lecturas en 50 `FieldSensorVariable` activos**.
`seed_sensor_readings` es idempotente (borra y recrea); `--keep` añade en vez de reemplazar.
Flags: `--days 30`, `--interval-minutes 15`, `--farm`, `--plot`, `--seed`, `--keep`.
Para la contraseña del usuario e2e sigue aplicando el paso del plan §4 (`make shell` →
`set_password`); esta rebanada no la toca.

## For next agent

**Frontend**
- Los seis endpoints están vivos y devuelven exactamente el contrato. `variable_id` identifica,
  `semantic_key` presenta; `?variable=` toma un `semantic_key`.
- `series/` **requiere `plot`** → 400 `{"plot": [...]}` si falta. `plot-averages/` ignora `plot`.
- Manda `date_from` alineado a hora/día si quieres etiquetas de eje redondas (*Gotchas* 2).
- El 400 del tope de export trae `code: "export_too_large"`, `count` y `limit`: construye el
  mensaje de AC16 con esos números, no con `detail`.
- Filas con `value = null` y sensores inactivos ya vienen filtrados; no hace falta defenderse.
- Datos reales disponibles hoy: fincas 1 y 2 de `juan.perez@email.com`, lotes 1–4 con las 4
  variables, lote 29 vacío a propósito, finca 13 sin lotes.

**QA**
- AC16 necesita `seed_sensor_readings --days 90` para ser reproducible (*Gotchas* 4).
- El lote 29 (`Lote Sin Mapear`) es el caso vacío listo para usar; el sensor 4 (inactivo, mide
  `other`) es el caso "variable que no debe aparecer".
- Un lote de la finca 2 pedido bajo `farms/1/...` debe dar **404**, no datos: caso AC17 ya cubierto
  por tests, vale la pena repetirlo en `e2e/backend/`.

## Proposed improvements

Reglas candidatas (no las apliqué; el orquestador las lleva al usuario):

1. **`backend/CLAUDE.md`** — *"En cualquier endpoint paginado, `order_by` debe terminar en un
   desempate único (`-id`): con solo un timestamp, PostgreSQL puede reordenar los empates entre
   la query de la página 1 y la de la página 2, y las filas se repiten o desaparecen."*
2. **`backend/CLAUDE.md`** — *"Nunca uses `?format=` como discriminador propio: DRF reserva ese
   param (`api_settings.URL_FORMAT_OVERRIDE`) y devuelve 404 'Invalid format'. Un formato de
   descarga distinto = una `path()` distinta."*
3. **`backend/CLAUDE.md`** — *"Un `DecimalField` de DRF se renderiza como string. Todo valor
   numérico que alimente un gráfico o un cálculo en el cliente va como `FloatField` (o `float(...)`),
   siguiendo el precedente de `FarmWeatherAPIView`."*
4. **`backend/CLAUDE.md`** — *"Los management commands de semilla se ejecutan dos veces: dentro de
   `@transaction.atomic`, borra el subconjunto que vas a recrear antes de `bulk_create`. Y ancla
   los timestamps a una rejilla (no a `now()` crudo) para que un flag `--seed` reproduzca de
   verdad la serie."*
5. **`CLAUDE.md` raíz (Continuous Improvement o Tests)** — *"Antes de tocar código, corre la suite
   del área para tener el baseline en números; al terminar, reporta 'baseline N → M'. Un plan que
   afirma 'no rompe nada' se verifica, no se cree."*
6. **`backend/CLAUDE.md`** — *"Un test que consume `random` sin semilla explícita es un test
   aleatorio. Pásale la semilla **y** asevera sobre un estadístico robusto (media de una ventana,
   monotonía), nunca sobre el `argmax` o el extremo de una muestra ruidosa: la semilla fija el
   ruido, pero no el resto de la entrada (aquí, la rejilla de timestamps anclada al reloj)."*
   (Raíz de **B1**; solapa con la propuesta 1 del reviewer — que el orquestador funda las dos.)
7. **`backend/CLAUDE.md`** — *"Todo query-param documentado en el contrato necesita un test que
   asevere su **efecto en el cuerpo** (y sus valores basura), no que la petición dé 200 ni que el
   conteo de queries no cambie. Comprobación barata: borra la línea que lo implementa y confirma
   que un test se pone rojo."*  (Raíz de **B2**; la segunda frase es lo que separó los tests
   nuevos de los que ya había.)
8. **`backend/CLAUDE.md`** — *"Escribe la convención de vistas: genéricos de DRF
   (`ListAPIView`/`RetrieveAPIView`) para listas y detalles simples —como `farm/api.py`— y
   `APIView` cuando la vista arma su propia respuesta. Hoy no está escrita y una desviación del
   plan se justificó con una regla inexistente."* (Raíz de **N5**.)
9. **Spec del agente de plan (`.claude/agents/...`)** — *"Todo número de volumen que el plan use
   para justificar un caso límite ('90 días ≈ 69 000 filas → dispara el tope') debe derivarse del
   alcance real del seeder, no extrapolarse. Aquí el seeder solo escribe 30 días, así que el tope
   de export resultó inalcanzable en dev."*
