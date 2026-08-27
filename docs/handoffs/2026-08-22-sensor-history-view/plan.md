<!-- Plan aprobado por el usuario el 2026-08-22. Los links son relativos a la raíz del repo. -->

Slug: `2026-08-22-sensor-history-view` · Contexto: [`spec.md`](spec.md) · [`contract.md`](contract.md) · [`acceptance-criteria.md`](acceptance-criteria.md)

# Plan — Vista de Historial de sensores

## Contexto

El dashboard hoy solo muestra el **estado actual**: mapa de lotes, conteos y las últimas
lecturas de la estación meteorológica (`FarmWeatherAPIView`). No hay forma de ver cómo
evolucionó una variable, ni de comparar lotes, ni de sacar los datos de la plataforma.

Esta feature agrega `/dashboard/history`: un historial filtrable por **finca, lote y variable
ambiental**, visible como **gráficos** o como **tabla paginada de 20 filas**, con **exportación
a `.csv` y `.json`**. Es la primera página que consume series temporales, y por eso es la
primera en el repo que necesita paginación DRF, filtrado por query-params, exportación en
streaming y gráficos — ninguno de los cuatro existe hoy.

**Obstáculo central resuelto:** el filtro "por lote" no era posible con los datos actuales.
`WeatherMeasurement` cuelga de `WeatherStation → Farm` (nivel finca), y `SensorMeasurement`
—el único modelo ligado a `Plot`— **nunca se crea en ningún sitio del código**. La feature
por tanto incluye poblar esa cadena.

### Decisiones ya tomadas (no re-litigar)

| # | Decisión |
|---|---|
| 1 | **Fuente de datos = sensores de campo** (`SensorMeasurement` → `FieldSensorVariable` → `FieldSensor` → `Plot`). Requiere ampliar fixtures + un seeder nuevo. |
| 2 | **Rango de fechas = presets (24h / 7d / 30d) + date-picker personalizado.** Default 7 días. |
| 3 | **Export = todo el set filtrado**, generado en el servidor, en streaming, con tope duro de 50 000 filas (400 si se excede, nunca truncado silencioso). |
| 4 | **Gráficos = uno por variable, en grilla**, cada uno con su eje Y y su unidad. Sin normalizar. |
| 5 | Modo solo-finca (promedio por lote) usa **barras agrupadas** — el eje X es categórico. |
| 6 | Fixtures: completar **solo los lotes de `juan.perez`** (1–4). Los lotes 5–28 quedan desiguales a propósito (preserva el caso límite "finca con una sola variable"). |
| 7 | **`make all-test` / `make e2e-test` quedan fuera de alcance.** Correr suites a mano. |

---

## 0. Fundamentos de datos

### 0.1 Fixtures — 9 filas nuevas, ningún test roto

Se mantienen los **42 `FieldSensor` intactos** (así `PlotQuerySet.with_sensor_count()` y los
tests de `farm/tests.py` que fijan `sensor_count` no se ven afectados) y se agregan filas
`FieldSensorVariable` — `unique_together` es `(sensor, env_variable)`, así que un sensor puede
llevar varias variables.

En [initial_sensors.json](backend/sensors/fixtures/initial_sensors.json), pks 43–52:

| pk | sensor | lote | env_variable | propósito |
|---|---|---|---|---|
| 43 | 1 | 1 | 2 (solar_radiation) | lote 1 → {1,2,3,4} |
| 44 | 4 | 1 | 5 (`other`, barométrica) | solo un sensor **inactivo** la mide → fixture negativa |
| 45–47 | 5 | 2 | 1, 2, 3 | lote 2 → {1,2,3,4} |
| 48–49 | 6, 7 | 3 | 1, 2 | lote 3 → {1,2,3,4} |
| 50–52 | 8 | 4 | 1, 2, 3 | lote 4 → {1,2,3,4} |

Tests existentes que rompe: **ninguno**. `with_sensor_count()` cuenta `field_sensors` filtrando
por `is_active` y nunca toca `FieldSensorVariable`; `SeedWeatherReadingsCommandTests` solo
mira modelos de estación. Verificarlo empíricamente con `make test` es el paso 1d.

### 0.2 Identidad de una variable en el cable

`semantic_key` **no es único** en `EnvironmentalVariable`. `FarmWeatherAPIView` se salva porque
devuelve una lectura por clave y excluye `OTHER`; un historial crudo no puede.

- **Identidad de serie/fila = `variable_id` (pk).**
- `semantic_key` viaja al lado como clave de **presentación** (íconos/colores/labels, igual que
  [constants/weather.ts](frontend/layers/dashboard/app/constants/weather.ts)).
- El **filtro `?variable=` toma un `semantic_key`** (mantiene el precedente del cable).
- Payload por fila/serie: `variable_id`, `semantic_key`, `name`, `unit`.
- **`other` NO se excluye** — a diferencia del endpoint de clima. El historial muestra lo que
  los sensores realmente miden. Es la única divergencia deliberada entre ambos endpoints.

### 0.3 Ownership y errores (todos los endpoints)

Se reutiliza `get_owned_or_404` de [farm/api.py](backend/farm/api.py) (devuelve
`{"detail": "Not found."}` genérico, así una fila ajena es indistinguible de una inexistente).
Un helper resuelve el scope completo en **exactamente una query** en ambas ramas:

```python
def resolve_history_scope(request, farm_id, plot_id):
    """Return (farm, plot); ownership enforced. `plot` is None when unfiltered."""
    if plot_id is None:
        return get_owned_or_404(Farm.objects.all(), pk=farm_id, owner__user=request.user), None
    plot = get_owned_or_404(
        Plot.objects.select_related('farm'),
        pk=plot_id, farm_id=farm_id, farm__owner__user=request.user,
    )
    return plot.farm, plot
```

Sin ciclo de imports: `sensors/api.py` importa de `farm`, nunca al revés.
Caso sutil que merece test: **un lote que el usuario sí posee pero de OTRA finca que la del
`farm_id` debe dar 404**, no devolver sus datos.

---

## 1. Backend

**Nuevos:** `backend/sensors/{api,serializers,urls,aggregation}.py`,
`backend/sensors/management/commands/seed_sensor_readings.py`
**Modificados:** [backend/backend/urls.py](backend/backend/urls.py),
[initial_sensors.json](backend/sensors/fixtures/initial_sensors.json),
[sensors/tests.py](backend/sensors/tests.py), `Makefile`, `backend/makefile`
`sensors/views.py` sigue siendo el stub vacío (regla de `backend/CLAUDE.md`: las vistas API van en `api.py`).

### 1.1 Rutas — `sensors/urls.py`, `app_name = "sensors"`

```python
path('farms/<int:farm_id>/history/variables/',     SensorHistoryVariablesAPIView.as_view(),     name='history-variables'),
path('farms/<int:farm_id>/history/readings/',      SensorHistoryReadingsAPIView.as_view(),      name='history-readings'),
path('farms/<int:farm_id>/history/series/',        SensorHistorySeriesAPIView.as_view(),        name='history-series'),
path('farms/<int:farm_id>/history/plot-averages/', SensorHistoryPlotAveragesAPIView.as_view(),  name='history-plot-averages'),
path('farms/<int:farm_id>/history/export/csv/',    SensorHistoryCsvExportAPIView.as_view(),     name='history-export-csv'),
path('farms/<int:farm_id>/history/export/json/',   SensorHistoryJsonExportAPIView.as_view(),    name='history-export-json'),
```

Montaje con tupla de namespace (sin ella `reverse("sensors:...")` no funciona en tests):
`path("api/sensors/", include((sensors_urlpatterns, "sensors")))`.

**Endpoints separados, no un `?mode=`:** las tres formas de lectura son tipos genuinamente
distintos (sobre de paginación / lista de series / matriz lote×variable); el caché difiere
(readings quiere `keepPreviousData` por página, series no); solo readings puede ser un
`ListAPIView` con `pagination_class`.

**Dos rutas de export, NO `?format=`** — esto es una trampa, no estilo: `api_settings.URL_FORMAT_OVERRIDE`
es literalmente `'format'`, así que `?format=csv` hace que DRF busque un renderer llamado `csv`
y devuelva **404 "Invalid format"**.

### 1.2 Filtrado — `serializers.Serializer` a mano, **sin `django-filter`**

Sopesado según la regla "build vs. reuse" del `CLAUDE.md` raíz: la superficie son 4 params y
3 necesitan **validación cruzada** que un `FilterSet` no hace (el lote debe pertenecer a *esta*
finca; `from < to`; rango ≤ tope). Además `DEFAULT_FILTER_BACKENDS` es global y tocar
`REST_FRAMEWORK` pone en riesgo los endpoints de `farm` existentes. La decisión no está cerca.

```python
class SensorHistoryFilterSerializer(serializers.Serializer):
    plot = serializers.IntegerField(required=False, allow_null=True)
    variable = serializers.ChoiceField(choices=SemanticKey.choices, required=False)
    date_from = serializers.DateTimeField(required=False)
    date_to = serializers.DateTimeField(required=False)

    def validate(self, attributes): ...  # defaults + from < to + span <= HISTORY_MAX_RANGE_DAYS
```

Cable: `?plot=&variable=&date_from=&date_to=&page=`. Defaults: `date_to = timezone.now()`,
`date_from = date_to - timedelta(days=7)`. `HISTORY_MAX_RANGE_DAYS = 90` → 400.

### 1.3 Bucketing / downsampling — `sensors/aggregation.py`

Postgres es 15 (`postgis/postgis:15-3.4`), así que `date_bin` (PG 14+) está disponible; el SQL
específico de Postgres ya está sancionado (`.distinct('...')` en `FarmWeatherAPIView`).

```python
class DateBin(Func):
    """PostgreSQL `date_bin(stride, source, origin)` — fixed-width buckets anchored on the
    requested range start, so bucket edges line up with what the chart asks for."""
    function = 'date_bin'
    arity = 3
    output_field = models.DateTimeField()
```

| Rango | Bucket | Máx puntos/serie |
|---|---|---|
| ≤ 2 días (preset 24h) | 15 min | 192 |
| > 2 y ≤ 8 días (preset 7d) | 1 hora | 192 |
| > 8 y ≤ 40 días (preset 30d) | 6 horas | 160 |
| > 40 días (personalizado) | 1 día | ≤ 90 |

**`bucket_seconds` viaja en la respuesta** — el frontend lo necesita para insertar `null` en los
buckets vacíos y que `VisLine` corte la línea en vez de dibujar una recta mentirosa sobre un
hueco (`interpolateMissingData` es `false` por defecto).

Series — **una sola sentencia SQL** sin importar cuántas variables:

```python
buckets = (
    SensorMeasurement.objects.filter(
        sensor_variable__sensor__plot_id=plot.pk,
        sensor_variable__sensor__is_active=True,
        recorded_at__gte=range_start, recorded_at__lt=range_end,
        value__isnull=False,
    )
    .annotate(bucket=DateBin(Value(bucket_size, output_field=models.DurationField()),
                             F('recorded_at'), Value(range_start)))
    .values('bucket', 'sensor_variable__env_variable_id',
            'sensor_variable__env_variable__semantic_key',
            'sensor_variable__env_variable__name',
            'sensor_variable__env_variable__unit')
    .annotate(average=Avg('value'), sample_count=Count('id'))
    .order_by('sensor_variable__env_variable__name', 'bucket')
)
```

Agrupado a series en una pasada Python. Valores con `float(...)` (precedente de
`FarmWeatherAPIView`), **no** el `DecimalField` de DRF que renderiza string.

Promedios por lote: misma forma, `.values()` sobre `sensor_variable__sensor__plot_id/__plot__name`
+ las 4 columnas de variable, `.annotate(average=Avg('value'), sample_count=Count('id'))`.
**Los lotes sin lecturas simplemente están ausentes** — el frontend ya tiene la lista completa
de lotes vía `useFarmPlotsQuery` y pinta "sin datos" en el hueco. Mantiene el endpoint en 1 query.

### 1.4 Paginación — **solo a nivel de vista**

No tocar `DEFAULT_PAGINATION_CLASS`: envolvería `FarmListAPIView` y `FarmPlotListAPIView`,
rompiendo `farm/tests.py` (que hace `response.json()[0]`) y los tipos `Farm[]`/`Plot[]` del frontend.

```python
class SensorHistoryPagination(pagination.PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({'count': self.page.paginator.count, 'page': self.page.number,
                         'page_size': self.get_page_size(self.request), 'results': data})
```

`next`/`previous` se descartan a propósito: DRF los construye como URLs absolutas desde el
request, que bajo docker resuelven al host interno `backend:8000`; y `UPagination` necesita
`total` + `page` + `itemsPerPage`, nunca una URL.

**El orden estable es crítico: `.order_by('-recorded_at', '-id')`.** El seeder escribe todas las
variables de un sensor en el *mismo* instante; sin el desempate por `-id`, Postgres puede
reordenar los empates entre la query de página 1 y la de página 2 y las filas se repiten o
desaparecen. `Meta.ordering = ['-recorded_at']` por sí solo no basta.

Queryset con `.select_related('sensor_variable__env_variable', 'sensor_variable__sensor__plot')`;
serializer plano con `source=` y `value = serializers.FloatField()`.

### 1.5 Export

`StreamingHttpResponse` + el writer `Echo` canónico sobre `.values_list(...).iterator(chunk_size=2000)`
— sin instanciar modelos, un cursor de servidor, memoria constante.

- **Tope `HISTORY_EXPORT_ROW_CAP = 50_000`.** Contar primero; al exceder, **400** con
  `{"detail": ..., "code": "export_too_large", "count": n, "limit": 50000}`. Rechazar antes que
  truncar: un CSV truncado en silencio es un bug de integridad que el usuario no puede ver.
- **CSV:** BOM UTF-8 (`﻿`) al inicio para que Excel en Windows renderice `°C` y `Radiación`.
  Cabecera: `recorded_at,plot,sensor,variable,semantic_key,value,unit`.
- **JSON:** stream `'['` + `json.dumps(row, cls=DjangoJSONEncoder)` unidos por `','` + `']'`.
  Nunca `JsonResponse` (bufferea).
- **Filename:** `historial-sensores-<slug-finca>-<YYYYMMDD>_<YYYYMMDD>.csv`, en `filename=` y `filename*=UTF-8''…`.
- **La descarga NO puede ser un `<a href>` plano** — el JWT vive en `localStorage` y solo el
  fetcher inyecta `Authorization`. El frontend hace fetch con auth → `Blob` → `createObjectURL`
  → click sintético → `revokeObjectURL`. El *cliente* materializa el archivo (~5–7 MB en el tope,
  aceptable) aunque el *servidor* nunca bufferee.

### 1.6 Índices — **sin migración nueva**

`SensorMeasurement.Meta` ya tiene `Index(fields=['sensor_variable', 'recorded_at'])`. Toda query
se acota primero por ownership, así que el plan siempre es: filtrar `field_sensor` por lote/finca
→ join a `fieldsensorvariable` (conjunto pequeño: ≤8 por lote) → index-scan sobre
`sensormeasurement` por `sensor_variable_id` con rango de `recorded_at`. Ese índice compuesto
tiene exactamente la forma correcta. Añadir una migración solo si `EXPLAIN ANALYZE` con volumen
sembrado (~150k filas) muestra un bitmap heap scan dominando — paso de medición, no migración especulativa.

### 1.7 `seed_sensor_readings`

Modelado sobre [seed_weather_readings.py](backend/sensors/management/commands/seed_weather_readings.py).
Flags: `--days` (30), `--interval-minutes` (15), `--farm`, `--plot`, `--seed`, `--keep`.

**Idempotencia:** `SensorMeasurement.sensor_variable` es `PROTECT` y **no** hay unique constraint
en `(sensor_variable, recorded_at)` — sin un delete explícito, re-ejecutar duplica todo. Dentro de
`@transaction.atomic`: `SensorMeasurement.objects.filter(sensor_variable__in=...).delete()` y luego
`bulk_create(batch_size=5000)`. Mismo idioma "borrar y recrear" del seeder existente.

**El realismo importa** — ruido uniforme (lo que hace el seeder de clima) se ve como estática y
hace que la feature demuestre mal:

| clave | curva |
|---|---|
| `air_temperature` | `24 + 5·sin(2π(h−9)/24)` → 19–29 °C, pico ~14:00 |
| `relative_humidity` | anti-fase con temperatura → 50–90 % |
| `solar_radiation` | `max(0, 900·sin(π(h−6)/12))` → 0 de noche, ~900 al mediodía |
| `soil_moisture` | decaimiento lento 55 → 25 con "riego" escalón cada ~3 días |
| `other` (barométrica) | `1010 + 3·sin(...)` |

Más `random.gauss(0, jitter)`, clamp al rango, `Decimal(f'{value:.4f}')`.
Siguiendo la filosofía del seed existente ("la semilla debe exponer los caminos infelices"),
sembrar además: **un `sensor_variable` sin sus últimas 6 horas** (hueco en el gráfico) y
**unas pocas filas `value=None`** (ejercita `value__isnull=False`).

**Volumen:** ~51 `FieldSensorVariable` activos × 30 días × 15 min ≈ **147 000 filas** (~30–60 s).
Finca 1 en 30 días ≈ 23 040 filas → cómodamente bajo el tope de export; un rango personalizado
de 90 días sobre la misma finca ≈ 69 000 → **ejercita el error de tope en desarrollo**, que es
justo lo que se quiere.

**Makefiles:** añadir `seed_sensor_readings` al target `loaddata` (raíz y `backend/`) después de
`seed_weather_readings`, y un target `seed-sensors:` espejo de `seed-weather:`.

### 1.8 Tests Django — `sensors/tests.py`

Estilo de la casa: `TestCase`/`APITestCase`, `setUpTestData` con `objects.create()` directo,
`force_authenticate`, `reverse("sensors:...")`, nombres de método en frase completa, y cada
`assertNumQueries` con el comentario que nombra cada query + *"If this number changes, a query
was added — do not just bump it."*

**`SensorHistoryVariablesTests`** — lista solo variables de sensores activos de la finca; filtrar
por lote acota; variable medida solo por sensor inactivo ausente; `assertNumQueries(2)`; 404 ajeno; 401.

**`SensorHistoryReadingsTests`** — 20 filas + `count`; página 2 continúa; **filas con el mismo
timestamp paginan determinísticamente** (fija el desempate `-id`); página fuera de rango 404;
fila con lote/sensor/variable/unidad y `value` **numérico** (no string); fila `value=None` omitida;
filtro por lote y por variable; lecturas fuera del rango excluidas; rango ausente → últimos 7 días;
rango sobre el tope → 400; fecha ilegible → 400 nombrando el campo; **lote de otra finca del mismo
dueño → 404**; finca ajena → 404 sin filtrar nada; `assertNumQueries(3)` y que no crezca con `page_size`; 401.

**`SensorHistorySeriesTests`** — una serie por variable; serie con nombre/unidad/semantic_key/bucket_size;
puntos son promedios de bucket, no crudos; 24h→15min, 7d→1h, 30d→6h; bucket vacío omitido (no `0`);
una variable → una serie; **dos variables con el mismo `semantic_key` siguen siendo series distintas**
(fija §0.2); sensor inactivo nunca entra; `assertNumQueries(2)` sin importar el nº de variables; 404 ajeno.

**`SensorHistoryPlotAveragesTests`** — un promedio por variable por lote; ignora fuera de rango;
lote sin lecturas ausente; sensor inactivo no contribuye; **el nº de queries no crece con el nº de
lotes** (`assertNumQueries(2)` contra finca de 2 y de 12 lotes); 404 ajeno.

**`SensorHistoryExportTests`** — cabecera + una fila por lectura; respeta los filtros;
**exporta todo el set filtrado, no solo la primera página** (sembrar 25 → 25 filas de datos);
empieza con BOM; el filename nombra finca y rango; el JSON es un array con las mismas filas;
set sobre el tope → 400 nombrando `count` y `limit`; `assertTrue(response.streaming)`; 404 ajeno; 401.

**`SeedSensorReadingsCommandTests`** — espejo del de clima: una serie por `sensor_variable` activo;
variables de sensor inactivo omitidas; correr dos veces reemplaza, no duplica; los flags controlan
span y resolución; valores dentro del rango plausible; radiación solar 0 de noche y pico a mediodía;
la lectura más nueva es lo bastante reciente para el preset de 24h; deja el hueco y el `null`;
`--seed` hace la serie reproducible.

**`SensorSeedDataContractTests`** — las 4 fixtures + `call_command('seed_sensor_readings', days=2, …)`.
**Va en `sensors/tests.py`, no en `farm/tests.py::SeedDataContractTests`**, para no ralentizar esa
clase ya pesada. Fija que los lotes de las fincas del dueño sembrado miden las 4 variables reales,
que el lote 29 (`Lote Sin Mapear`) reporta historial vacío, y que la finca por defecto cubre las 4.

**Tests existentes a actualizar: ninguno.** Ese es el punto del enfoque de §0.1.

---

## 2. Frontend

### 2.1 Nueva layer `sensors`

[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md):71 y ADR 0001 §3 dicen literalmente *"New domains
(`farm`, `sensors`, `predictions`) are born as layers"*. La línea 122 del mismo archivo lo
contradice (*"built as new pages in the `dashboard` layer"*) — **es anterior a la regla
generalizada y se corrige en este cambio**.

Además del argumento normativo: la feature es una rebanada vertical real (módulo api, enum de
query keys, 4 queries, tipos, constantes, 3 utils puros, 7 componentes); meterla en `dashboard`
lo convierte en el vertedero que el ADR existe para evitar. La ruta es ortogonal — Nuxt fusiona
los `app/pages` de las layers, así que `layers/sensors/app/pages/dashboard/history.vue` da
`/dashboard/history` y `/en/dashboard/history` sin configuración. El link del nav vive en el
layout de `dashboard` y es solo un string `localePath(...)`: **`dashboard` no gana ninguna
dependencia sobre `sensors`**.

**Nuevo borde sancionado: `sensors → farm`** (auto-imports `useSelectedFarm`, `useFarmPlotsQuery`;
tipo `Plot`). Idéntico en forma y dirección al `dashboard → farm` existente. **Debe registrarse**
en [frontend/CLAUDE.md](frontend/CLAUDE.md) ("Sole sanctioned exceptions") y en la lista
"Dependency direction" de ARCHITECTURE.md, o el próximo reviewer lo marcará (con razón) como violación.

### 2.2 Archivos

**Nuevos — `frontend/layers/sensors/`**

```
nuxt.config.ts                              $meta {name:'sensors'} + imports.dirs (absoluto, fileURLToPath) + i18n.locales
i18n/locales/{es,en}.json                   namespace `sensors`
app/pages/dashboard/history.vue             dueña de todas las queries; pasa data+isPending+isError hacia abajo
app/types/sensors.ts                        SensorReading, ReadingsPage, HistorySeries, SeriesPoint,
                                            PlotAverage, HistoryVariable, SensorSemanticKey
app/constants/query-keys.ts                 enum SensorsQueryKey
app/constants/history.ts                    HISTORY_PAGE_SIZE=20, CHART_HEIGHT_CLASS, CHART_MARGIN,
                                            VARIABLE_ICONS/COLORS, HISTORY_MAX_RANGE_DAYS, EXPORT_ROW_CAP
app/utils/api/sensors.ts                    sensorsApi
app/utils/history-filters.ts                tipos + VIEWS/PRESETS + parse*/getStored*/setStored*/resolveRange
app/utils/history-chart.ts                  fillBuckets(), summariseSeries()  (puros)
app/utils/history-export.ts                 buildExportFilename(), parseExportError()
app/composables/useHistoryFilters.ts        URL <-> estado de filtros
app/composables/useHistory{Variables,Readings,Series,PlotAverages}Query.ts
app/composables/useHistoryExport.ts
app/components/sensors/HistoryFilters.vue
app/components/sensors/HistoryDateRange.vue
app/components/sensors/HistoryExportMenu.vue
app/components/sensors/HistoryTable.vue
app/components/sensors/HistoryChartGrid.vue
app/components/sensors/HistoryLineChart.client.vue
app/components/sensors/HistoryPlotAveragesChart.client.vue
```

Los componentes bajo `app/components/sensors/` auto-importan con prefijo `Sensors` →
`<SensorsHistoryFilters>`, `<LazySensorsHistoryLineChart>` (misma convención que `dashboard/` → `Dashboard*`).

**Nuevo — [layers/common/app/utils/download.ts](frontend/layers/common/app/utils/download.ts)**
(transversal por naturaleza; `predictions` lo va a querer).

**Modificados:** [fetcher.ts](frontend/layers/common/app/utils/api/fetcher.ts),
[dashboard.vue](frontend/layers/dashboard/app/layouts/dashboard.vue) (entrada de nav + borrar el
comentario ya falso *"History/Predictions stay hidden until those pages exist"*),
`layers/dashboard/i18n/locales/{es,en}.json` (`dashboard.nav.history`),
`frontend/CLAUDE.md`, `docs/ARCHITECTURE.md`.

### 2.3 Cambio en `fetcher` — firma exacta

Hoy `get: <T>(url: string) => request<T>(url)`: sin opciones, sin camino para blobs. El `request`
privado ya acepta `NitroFetchOptions`, así que solo cambia la superficie pública:

```ts
type QueryParams = Record<string, string | number | boolean | undefined>

export const fetcher = {
  get: <T>(url: string, query?: QueryParams) => request<T>(url, { query }),
  // `responseType: 'blob'` skips ofetch's JSON parsing. Going through `request`
  // rather than a bare fetch is what keeps the 401 → refresh → retry path.
  getBlob: (url: string, query?: QueryParams) =>
    request<Blob>(url, { query, responseType: 'blob' }),
  // ...post/put/patch/patchFormData/delete sin cambios
}
```

Elegido sobre construir query strings en cada módulo api porque `query` de ofetch ya omite
`undefined` y codifica correctamente — es exactamente la función de librería a la que apunta la
regla build-vs-reuse. Un tipo `QueryParams` estrecho (en vez de exponer todo `NitroFetchOptions`)
mantiene el fetcher como contrato deliberado: nadie puede colar `baseURL`/`method` y saltarse el stack.
Todos los llamadores actuales quedan intactos — el parámetro es opcional.

**Gotcha:** con `responseType: 'blob'`, ofetch entrega el cuerpo de *error* también como Blob.
El 400 del tope se lee con `JSON.parse(await (error.data as Blob).text())` — eso vive en
`history-export.ts::parseExportError()`.

### 2.4 Barra de filtros y round-trip por URL

`app/utils/history-filters.ts` es espejo exacto de
[view-mode.ts](frontend/layers/dashboard/app/utils/view-mode.ts):

```ts
export type HistoryView = 'chart' | 'table'
export const HISTORY_VIEWS: HistoryView[] = ['chart', 'table']
export const DEFAULT_HISTORY_VIEW: HistoryView = 'chart'
export type HistoryRangePreset = '24h' | '7d' | '30d' | 'custom'
export const DEFAULT_RANGE_PRESET: HistoryRangePreset = '7d'
export const parseHistoryView / parseRangePreset / parsePlotId / parseVariableKey / parseCalendarDate
export const resolveRange = (preset, from, to, anchorMs) => ({ date_from: string, date_to: string })
export const getStoredHistoryView / setStoredHistoryView   // guardados con import.meta.client
```

`useHistoryFilters.ts` es espejo de `useDashboardViewMode.ts` y posee
`?plot=&variable=&range=&from=&to=&view=&page=`:

- `plot` ausente = **Todos los lotes**; `variable` ausente = **Todas las variables**. Limpiar
  escribe `undefined` (la clave desaparece), nunca `plot=null`.
- `range=custom` requiere `from`/`to`; si falta o es ilegible, cae en silencio a `7d` — nunca
  devolver 400 al usuario por una URL editada a mano.
- `onMounted`: si falta `?view`, leer `localStorage` y `router.replace` el valor resuelto (sin
  entrada de historial) — misma razón de mismatch de hidratación que documenta `useDashboardViewMode`.
  **Solo se persiste `view`**; un `plot`/`variable` guardado podría ser de una finca que ya no está seleccionada.
- Cambios del usuario → `router.push` (Back recorre el historial de filtros).
- **Cambiar de finca resetea `plot`** (un id de la finca A da 404 bajo la finca B):
  `watch(farmId, () => clearPlot())` con `router.replace`.
- Cualquier cambio de filtro resetea `page` a 1.

**Zona horaria:** el backend es `USE_TZ=True`, `TIME_ZONE='UTC'`. Las fechas personalizadas se
eligen como días de calendario locales, así que `resolveRange` debe convertir *inicio del día local*
→ UTC ISO y *fin del día local* → UTC ISO. Si no, "22 de agosto" significa en silencio las 24 horas
equivocadas en Bogotá (UTC−5). Es el bug clásico aquí — nombrarlo en el comentario del código.

**`now` debe estar anclado.** Si `date_to` fuera `Date.now()` dentro de un computed, cada re-render
produciría un valor nuevo, re-clavearía cada query key y refetchearía sin fin. Mantener
`const rangeAnchor = shallowRef(Date.now())`, actualizado solo al cambiar un filtro o al pulsar
"Actualizar". Keys deterministas, e2e estable.

**Controles** (`HistoryFilters.vue`, tonto + `defineEmits`, en un `UDashboardToolbar` bajo el navbar):

| control | componente |
|---|---|
| Finca | texto de solo lectura con `selectedFarm.name` — el selector ya vive en el sidebar (`FarmsMenu`); duplicarlo daría dos fuentes de verdad |
| Lote | `<USelectMenu>` con ítem "Todos los lotes", opciones de `useFarmPlotsQuery` |
| Variable ambiental | `<USelectMenu>` con ítem "Todas las variables", opciones de `useHistoryVariablesQuery` |
| Rango | `<USelect>` con los 3 presets + "Personalizado" |
| Rango personalizado | `HistoryDateRange.vue`: `<UPopover>` con trigger `<UButton>` mostrando el rango formateado, conteniendo **`<UCalendar range />`**, más `<UInputDate range />` para entrada tecleada. Solo se renderiza si `range === 'custom'` |
| Limpiar filtros | `<UButton variant="link">` |

Cada control envuelto en `<UFormField :label>` (asociación programática, 3.3.2). Toda la barra en
`<section :aria-label="t('sensors.history.filters.label')">`.

### 2.5 Máquina de estados de visualización

```ts
type HistoryDisplayMode = 'plotAverages' | 'allVariables' | 'singleVariable'
```

| condición | modo |
|---|---|
| `farmId === null` | `t('sensors.history.noFarm')` (espejo de `farm.plots.noFarm`) |
| `plotId === null` | `plotAverages` — un promedio por variable por lote |
| `plotId !== null && variable === null` | `allVariables` — grilla de un gráfico lineal por variable |
| `plotId !== null && variable !== null` | `singleVariable` — un gráfico lineal |

El **toggle gráfico/tabla es ortogonal**:
- gráfico + `plotAverages` → `<SensorsHistoryPlotAveragesChart>` (**`VisGroupedBar`**, un gráfico por
  variable en la misma grilla — el eje X es categórico, una línea sobre 3 lotes sugeriría una
  continuidad inexistente)
- gráfico + `allVariables`/`singleVariable` → `<SensorsHistoryChartGrid>`
- **tabla (cualquier modo)** → `<SensorsHistoryTable>`, con la columna `Lote` visible solo cuando
  no hay lote seleccionado

Simplificación deliberada: **no hay tabla separada de promedios**. El requisito pide "una tabla
paginada de los históricos de los sensores", que el endpoint de readings ya sirve también en modo
solo-finca. Un componente de tabla en vez de dos.

Markup del toggle — copiar verbatim del dashboard index, incluido el fix de foco. El wrapper
`<section :aria-label>` es obligatorio: Reka renderiza la raíz de `UTabs` como un `<div>` plano,
donde `aria-label` está prohibido.

### 2.6 Vue Query

```ts
export enum SensorsQueryKey {
  ROOT = 'sensors', HISTORY = 'history', VARIABLES = 'variables',
  READINGS = 'readings', SERIES = 'series', PLOT_AVERAGES = 'plotAverages',
}
```

Cada composable sigue [useFarmWeatherQuery.ts](frontend/layers/farm/app/composables/useFarmWeatherQuery.ts)
al pie de la letra — factory `<x>QueryOptions()` que devuelve objeto plano con key `as const`
(nunca el helper `queryOptions()`), refs en la key, `enabled: () => hasTokens() && ...`:

```ts
export const historyReadingsQueryOptions = (
  farmId: Ref<number | null>, filters: Ref<HistoryQueryFilters>, page: Ref<number>,
) => ({
  queryKey: [SensorsQueryKey.ROOT, SensorsQueryKey.HISTORY,
             SensorsQueryKey.READINGS, farmId, filters, page] as const,
  queryFn: () => sensorsApi.getHistoryReadings(farmId.value!, filters.value, page.value),
})
```

Un objeto plano en la key es seguro — `hashKey` de TanStack ordena las claves — y se lee mucho
mejor que cuatro refs posicionales.

| query | `enabled` |
|---|---|
| variables | `hasTokens() && farmId !== null` |
| readings | `... && view === 'table'` |
| series | `... && view === 'chart' && plotId !== null` |
| plot averages | `... && view === 'chart' && plotId === null` |

**Primer uso de `placeholderData: keepPreviousData` en el repo**, en la query de readings, para que
paginar no parpadee un skeleton; atenuar la tabla con `isPlaceholderData`. Además, acotar `page`
en cliente contra `count` (una página más allá de la última es 404 del backend) y mantener el
predicado `retry` estilo `usePlotQuery` como cinturón y tirantes.

`app/utils/api/sensors.ts` — rutas relativas a `/api`, con slash final, sin host, sin prefijo `/api`:

```ts
export const sensorsApi = {
  getHistoryVariables:    (farmId, query) => fetcher.get<HistoryVariable[]>(`sensors/farms/${farmId}/history/variables/`, query),
  getHistoryReadings:     (farmId, query) => fetcher.get<ReadingsPage>(`sensors/farms/${farmId}/history/readings/`, query),
  getHistorySeries:       (farmId, query) => fetcher.get<HistorySeries[]>(`sensors/farms/${farmId}/history/series/`, query),
  getHistoryPlotAverages: (farmId, query) => fetcher.get<PlotAverage[]>(`sensors/farms/${farmId}/history/plot-averages/`, query),
  getHistoryExport: (farmId, fileFormat, query) =>
    fetcher.getBlob(`sensors/farms/${farmId}/history/export/${fileFormat}/`, query),
}
```

### 2.7 El gráfico Unovis

`HistoryLineChart.client.vue` — `.client.vue`, montado vía `<ClientOnly>` +
`<LazySensorsHistoryLineChart>` con `#fallback` skeleton fijado a `CHART_HEIGHT_CLASS` (la misma
constante que usa el gráfico, así no hay layout shift) — patrón de
[PlotsMap.client.vue](frontend/layers/dashboard/app/components/dashboard/PlotsMap.client.vue).

**Diferencia con `PlotsMap`: no hay import de CSS.** `@unovis/ts` no trae stylesheet para los
componentes XY (el único `.css` del paquete es una copia anidada de leaflet); los estilos se
inyectan en runtime.

```vue
<VisXYContainer :data="points" :height="CHART_HEIGHT" :margin="CHART_MARGIN">
  <VisLine :x="xAccessor" :y="yAccessor" :curve-type="CurveType.MonotoneX" :color="color" />
  <VisScatter v-if="points.length < 3" :x="xAccessor" :y="yAccessor" :size="4" />
  <VisAxis type="x" :tick-format="formatTick" :num-ticks="4" :grid-line="false" />
  <VisAxis type="y" :label="unit" :tick-format="formatValue" :num-ticks="4" />
  <VisCrosshair :template="tooltipTemplate" />
  <VisTooltip />
</VisXYContainer>
```

`SeriesPoint = { t: number; value: number | null }` (`t` en epoch ms para que `x` sea numérico).
Colores de un `VARIABLE_COLORS: Record<SensorSemanticKey, string>` usando las custom properties del
tema Nuxt UI — decorativos, ya que cada gráfico lleva su propio título y unidad (sin violación de color-solo).

**Vacío / escaso**
- 0 puntos → no montar el gráfico; `<UEmpty icon="i-lucide-chart-line" :description="t('sensors.history.table.empty')" />`.
- 1–2 puntos → una `VisLine` con un solo dato no dibuja nada; de ahí el `VisScatter`.
- **Huecos** → el backend omite los buckets vacíos; `history-chart.ts::fillBuckets(points, from, to, bucketSeconds)`
  inserta `null` en los faltantes. `interpolateMissingData` es `false` por defecto, así que la línea
  se corta en un hueco real en vez de dibujar una recta mentirosa. Por eso `bucket_seconds` va en el cable.

**Accesibilidad (1.1.1)** — un SVG de 200 puntos no sirve a un lector de pantalla, y esta app ya
tiene la alternativa textual perfecta: la vista de tabla.

```vue
<figure>
  <figcaption>{{ name }} ({{ unit }})</figcaption>
  <div aria-hidden="true"><VisXYContainer …/></div>
  <p class="sr-only">{{ t('sensors.history.charts.summary', { name, count, from, to, min, max, average, unit }) }}</p>
</figure>
```

Más un `<p class="text-sm text-muted">{{ t('sensors.history.charts.alternative') }}</p>` visible por
grilla, espejo de `dashboard.map.alternative`. `summariseSeries()` calcula min/max/promedio como
función pura (testeable, y la costura estable para los e2e — ver §3.4).

Grilla: `<section :aria-label><div class="grid gap-4 sm:grid-cols-2">` — un `div` plano, no
`UPageGrid`, por la regla del div-plano de Reka.

### 2.8 `UTable` + `UPagination`

**Primer uso de ambos en el repo.** `UTable` envuelve TanStack Table; `UPagination` envuelve
`PaginationRoot` de Reka, que renderiza un `<nav>` — así que aquí `aria-label` **sí** va directo
en `<UPagination>`, a diferencia de `UTabs`.

Columnas como `computed<TableColumn<SensorReading>[]>` para que las cabeceras se re-traduzcan al
cambiar de idioma:

| accessorKey | header | celda |
|---|---|---|
| `recorded_at` | `table.recordedAt` | `Intl.DateTimeFormat(locale, {dateStyle:'short', timeStyle:'short'})` |
| `plot_name` | `table.plot` | solo si `showPlotColumn` |
| `sensor_name` | `table.sensor` | — |
| `variable_name` | `table.variable` | — |
| `value` | `table.value` | `Intl.NumberFormat(locale, {maximumFractionDigits:2})`, `meta.class.td: 'text-right tabular-nums'` |
| `unit` | `table.unit` | — |

`:caption="t('sensors.history.table.caption', { farm, count }, count)"` da un `<caption>` real (1.3.1).
Carga con el prop `loading` de `UTable` + `aria-busy="true"` en el wrapper.

**El ordenamiento es server-side-only y por tanto está apagado en v1** — activar el sorting de
TanStack ordenaría solo las 20 filas visibles, lo que es una mentira sobre un dataset de 23 000.
Se envía ordenado por `recorded_at desc`; un query param `ordering` es el follow-up. Dejarlo dicho
en un comentario para que nadie lo "arregle".

Vacío: `<UEmpty icon="i-lucide-table" :description="t('sensors.history.table.empty')" />` cuando
`count === 0 && !pending`.

```vue
<UPagination :page="page" :items-per-page="HISTORY_PAGE_SIZE" :total="count"
             :sibling-count="1" show-edges
             :aria-label="t('sensors.history.pagination.label')"
             @update:page="emit('update:page', $event)" />
```

`page` también vive en la URL, así que un link compartido reproduce la vista exacta.

Estado de error — patrón de tres estados de la casa: texto + Retry etiquetado, nunca color solo.
Los handlers de template envuelven `refetch` para devolver `void`.

### 2.9 UX de exportación

`HistoryExportMenu.vue`: `<UDropdownMenu>` sobre
`<UButton icon="i-lucide-download" :label="t('sensors.history.export.label')" :loading="isExporting" :disabled="count === 0">`
con ítems "Descargar CSV" / "Descargar JSON".

`useHistoryExport.ts` (todas las funciones flecha, por la regla):

```ts
export const useHistoryExport = () => {
  const isExporting = shallowRef(false)
  const exportError = shallowRef<string | null>(null)
  const toast = useToast()
  const exportHistory = async (fileFormat, farmId, farmName, filters) => { … }
  return { exportHistory, isExporting, exportError }
}
```

`layers/common/app/utils/download.ts`:

```ts
export const downloadBlob = (blob: Blob, filename: string): void => {
  if (!import.meta.client) return
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.rel = 'noopener'
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  // Revoking synchronously cancels the download in Safari; one tick is enough.
  setTimeout(() => URL.revokeObjectURL(url), 0)
}
```

El filename se construye **en cliente** (`buildExportFilename()`), así el flujo nunca depende de
leer `Content-Disposition` — que exigiría `Access-Control-Expose-Headers` en la topología
cross-origin de desarrollo.

Errores: el 400 del tope llega como Blob (§2.3) → `parseExportError()` → un `useToast()` **y** un
`role="alert"` inline junto al botón (solo-toast fallaría 4.1.3 para quien no lo vea), nombrando
el número de filas y el límite para que el mensaje sea accionable ("Reduce el rango o filtra por lote").

### 2.10 Claves i18n (namespace `sensors`, en `es.json` y `en.json`)

```
sensors.history.title | subtitle | noFarm | noVariables | error | retry
sensors.history.filters.label | farm | plot | allPlots | variable | allVariables | range | reset
sensors.history.range.last24h | last7d | last30d | custom | from | to | apply | invalid | tooLong
sensors.history.view.label | chart | table
sensors.history.charts.label | loading | alternative | summary | axisTime
sensors.history.averages.label | title | summary | noData
sensors.history.table.caption | recordedAt | plot | sensor | variable | value | unit | empty
sensors.history.pagination.label | status
sensors.history.export.label | csv | json | pending | done | tooLarge | error
```

Plurales con `|` en `table.caption` y `pagination.status`. Fechas y números vía `Intl` con
`locale.value`. Sin `@` literal en ningún mensaje.
Además en `layers/dashboard/i18n/locales/`: `dashboard.nav.history` = `"Historial"` / `"History"`,
y la entrada en el computed `links` de `dashboard.vue` (`icon: 'i-lucide-history'`,
`to: localePath('/dashboard/history')`), borrando el comentario ya falso.

### 2.11 Accesibilidad (WCAG 2.2 AA)

| Superficie | Requisito |
|---|---|
| Gráficos | SVG `aria-hidden` dentro de `<figure>` + `<figcaption>` + resumen numérico sr-only (1.1.1); la tabla es la alternativa textual completa, anunciada con una nota visible |
| Tabla | `<caption>` real, `<th scope>` del `<table>` nativo de `UTable`, sin cabeceras ordenables en v1 (mentirían), columna numérica `tabular-nums` alineada a la derecha |
| Paginación | `aria-label` directo en `UPagination` (su raíz es `<nav>`); el foco se queda en el control pulsado |
| Región viva | un `<p aria-live="polite" class="sr-only">` en la página anunciando `pagination.status` al cambiar filtros y páginas (4.1.3) |
| Filtros | cada control en `<UFormField :label>`; la barra en `<section :aria-label>`; sin mover el foco al cambiar filtro (2.4.3) |
| Tabs | wrapper `<section :aria-label>` + el override `:ui` de `focus-visible:ring` (2.4.7), copiado del dashboard index |
| Calendario | `UPopover` gestiona trampa de foco / retorno / Escape; además `UInputDate` para entrada tecleada, que el calendario no sea el único camino |
| Errores | `role="alert"` + texto + Retry etiquetado — nunca color ni ícono solos (1.4.1) |
| Targets | controles de export/paginación ≥ 24×24 px (2.5.8) |

---

## 3. E2E

### 3.1 Ubicación

**Nuevo `e2e/frontend/sensors.spec.ts`** — el `CLAUDE.md` raíz pide *"`e2e/frontend/<module>.spec.ts`
matching the frontend layer name"*, y la layer es `sensors`. `dashboard.spec.ts` gana exactamente
**un** test (el link de nav), porque el layout es un cambio de la layer `dashboard`.

Nota de drift documentada: **no existe `e2e/CLAUDE.md`** (las reglas viven en `e2e/README.md` +
`CLAUDE.md` raíz) y **`make e2e-test` / `make all-test` no existen** (decisión #7: fuera de alcance).
Se corre con `cd e2e && npx playwright test`. Baseline actual: 46 tests.

### 3.2 Tests (nombres en español, locators por rol, todo string desde `T`)

`test.describe('Historial de sensores')`
1. `'la vista abre con los últimos 7 días y un gráfico por variable del lote seleccionado'`
2. `'seleccionar "Todos los lotes" muestra el promedio de cada variable por lote'`
3. `'elegir una sola variable deja un único gráfico'`
4. `'los filtros viajan en la URL y sobreviven a una recarga'`
5. `'cambiar de finca reinicia el lote seleccionado'` — reutilizar el idiom `selectFarm` de
   `farm.spec.ts` (incluido el `Escape` tras el dropdown); asertar que `plot` desapareció de la URL
6. `'el conmutador Tabla muestra una tabla paginada de máximo 20 filas'` —
   `await expect(page.getByRole('row')).toHaveCount(21)` (20 + cabecera)
7. `'avanzar de página trae lecturas distintas sin repetir la primera fila'` — la cara e2e del
   desempate `-id`
8. `'un rango personalizado filtra las lecturas'`
9. `'si la carga del historial falla, aparece el fallback de error y Reintentar recupera'` —
   `page.route('**/sensors/farms/*/history/**', r => r.abort())`, asertar el `role="alert"`,
   `unroute`, click en Retry **dentro de la alerta** (nunca por nombre solo: "Reintentar" se reutiliza)
10. `'sin lecturas en el rango, la tabla muestra el estado vacío'`
11. *(en `dashboard.spec.ts`)* `'el enlace Historial del menú lateral abre el historial de sensores'`

`test.describe('Exportación del historial')`
12. `'exportar a CSV descarga un archivo con las lecturas filtradas'`
13. `'exportar a JSON descarga un archivo .json'`

### 3.3 Asertar la descarga — **la aserción más riesgosa de la suite**

```ts
const downloadPromise = page.waitForEvent('download')
await page.getByRole('button', { name: T.exportLabel }).click()
await page.getByRole('menuitem', { name: T.exportCsv }).click()
const download = await downloadPromise
expect(download.suggestedFilename()).toMatch(/^historial-sensores-.*\.csv$/)
const stream = await download.createReadStream()   // asertar la fila de cabecera
```

El archivo llega por una URL `blob:` + click sintético, no por navegación del servidor. Chromium
**sí** dispara `download` para eso, pero **verificarlo el día uno**. Fallback si no:

```ts
const response = await page.waitForResponse(r => r.url().includes('/history/export/csv/') && r.status() === 200)
expect(response.headers()['content-type']).toContain('text/csv')
```

### 3.4 Asertar los gráficos sin flake

Nunca tocar el atributo `d` de un path ni geometría en píxeles. En su lugar:
1. `await page.waitForResponse('**/history/series/**')`
2. `await expect(page.locator('figure')).toHaveCount(4)`
3. asertar que cada `<figcaption>` nombra su variable (`T.varAirTemperature`, …)
4. asertar que el resumen sr-only contiene el conteo de lecturas — **para esto existe el resumen**:
   prueba que llegaron datos y que el componente montó con puntos, con cero dependencia del render.

### 3.5 Entradas nuevas en `T` ([e2e/frontend/helpers.ts](e2e/frontend/helpers.ts))

```ts
navHistory: 'Historial',            historyTitle: 'Historial de sensores',
filterPlot: 'Lote',                 filterAllPlots: 'Todos los lotes',
filterVariable: 'Variable ambiental', filterAllVariables: 'Todas las variables',
filterRange: 'Rango de fechas',
range24h: 'Últimas 24 horas',       range7d: 'Últimos 7 días',
range30d: 'Últimos 30 días',        rangeCustom: 'Personalizado',
viewChart: 'Gráficos',              viewTable: 'Tabla',
exportLabel: 'Exportar',            exportCsv: 'Descargar CSV',   exportJson: 'Descargar JSON',
historyLoadError: 'No se pudo cargar el historial.',
historyEmpty: 'No hay lecturas para estos filtros.',
plotFirst: 'Lote El Abrevadero',    plotSecond: 'Lote La Colina',
varAirTemperature: 'Temperatura del aire', varSoilMoisture: 'Humedad del suelo',
```

### 3.6 `a11y.spec.ts`

`test('historial de sensores sin violaciones serias/críticas (gráficos y tabla)')`: login →
`/dashboard/history` → esperar la respuesta de series → `severeViolations(page)` → click en la
pestaña "Tabla" → escanear otra vez. El SVG de Unovis es el objetivo probable de axe
(`svg-img-alt`); el wrapper `aria-hidden="true"` es la respuesta prevista. **No agregar una
exclusión** — el archivo tiene hoy exactamente una documentada (`LOGIN_SUBMIT_KNOWN_CONTRAST`) y
debe seguir así; se arregla el markup.

### 3.7 Spec de API — `e2e/backend/api_sensors_history.spec.ts`

El único backend spec de hoy (`api_cms.spec.ts`) pega a un endpoint público, así que hace falta un
helper de auth nuevo en `e2e/backend/`:
`request.post('/api/accounts/login/', { data: { email, password } })`.

Aserciones: 401 sin token; el sobre es exactamente `{count, page, page_size, results}`;
`results.length <= 20`; finca ajena → **404, no 403**; `date_from > date_to` → 400; el export CSV
devuelve `text/csv` con `Content-Disposition: attachment`. Los tipos de respuesta van en el
`e2e/backend/types.ts` existente.

---

## 4. Verificación

| Qué | Cómo |
|---|---|
| Datos sembrados | desde `backend/`: `make loaddata` (ahora incluye `seed_sensor_readings`); contraseña una vez con `make shell` → `User.objects.get(email='juan.perez@email.com').set_password('E2eSmoke_2026!')` |
| Suite backend | desde `backend/`: `make test` — **primero antes de tocar nada** (§0.1 afirma que ningún test existente rompe; confirmarlo empíricamente) |
| Lint backend | `make lint-backend` (ruff, line-length 100, `E,W,F,I,UP,B,DJ`) |
| Spike `date_bin` | `make shell` — ejecutar la query de §1.3 antes de construir sobre ella (§5, riesgo 3) |
| Frontend | `cd frontend && npm run dev`; **reiniciar el dev server** tras crear la layer (agregar archivos bajo `app/{composables,utils}` invalida el grafo de módulos) |
| Lint / types frontend | `npm run lint`, `npm run typecheck` |
| E2E | calentar el dev server cargando una página, luego `cd e2e && npx playwright test`; baseline 46 → debe subir a ~59 sin regresiones |
| Manual | `/dashboard/history` — los 3 modos, el toggle tabla/gráfico, paginar, rango personalizado, exportar CSV y JSON, cambiar de idioma a `/en/dashboard/history`, cambiar de finca desde el sidebar |

---

## 5. Riesgos y desconocidos a resolver temprano

1. **`download` de Playwright sobre un click de URL `blob:`** (§3.3) — verificar el día uno;
   fallback listo. Construir el test 12 **primero** para de-riesgar.
2. **Tipado de `fetcher.getBlob`** — ofetch deriva el tipo de retorno de `responseType`, así que
   `request<Blob>` puede necesitar un cast. Pequeño, pero saldrá en `npm run typecheck`.
3. **`date_bin` vía `Func` de Django** con un primer argumento `Value(timedelta, output_field=DurationField())`
   — psycopg3 debería adaptarlo a `interval`; verificar con una query antes de construir encima.
   Fallback: `TruncHour`/`TruncDay` para todos los buckets, perdiendo solo los tiers de 15 min y 6 h.
4. **Sin Vitest en `frontend/`** — `history-filters.ts`, `history-chart.ts` (`fillBuckets`,
   `summariseSeries`) y `history-export.ts` son puros, unit-testeables, y se envían sin tests.
   Es el estado documentado del repo (Playwright es la única puerta), pero es deuda que se acumula
   justo sobre el código que más se beneficiaría.
5. **Volumen del seeder** — ~147 000 filas, +30–60 s a `make loaddata`. `--interval-minutes 30`
   lo reduce a la mitad, pero deja un gráfico de 24h medio vacío con buckets de 15 min.

### Docs que deben actualizarse con el mismo cambio

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md):122 contradice a :71 y al ADR 0001 §3 sobre dónde
  viven las páginas de historial — **corregir la línea 122**.
- `frontend/CLAUDE.md` y `docs/ARCHITECTURE.md` deben registrar el borde sancionado **`sensors → farm`**.
- [dashboard.vue](frontend/layers/dashboard/app/layouts/dashboard.vue) — el comentario
  *"History/Predictions stay hidden until those pages exist"* queda falso: borrarlo.
- `docs/ARCHITECTURE.md` — mover "Dashboard pages for history" de "Planned" a "Working today", y
  agregar `sensors` a la lista de layers del frontend.

---

## 6. Orden de construcción

**Paso 1 — fundamento de datos (bloquea todo).**
1a. Fixture: +9/10 filas `FieldSensorVariable` (pks 43–52).
1b. `seed_sensor_readings` + `SeedSensorReadingsCommandTests`.
1c. `Makefile` + `backend/makefile`: línea en `loaddata` + target `seed-sensors`.
1d. `make test` desde `backend/` para confirmar empíricamente que nada existente rompe.
1e. Spike de `date_bin` en `make shell` antes de escribir `aggregation.py`.

**Paso 2 — API backend.**
2a. `sensors/serializers.py` + `sensors/aggregation.py` (`DateBin`, `bucket_size_for`).
2b. `sensors/api.py` — `resolve_history_scope`, luego variables → readings (+ clase de paginación)
    → series → plot-averages → las dos vistas de export.
2c. `sensors/urls.py` + montaje en `backend/backend/urls.py`.
2d. Las cinco clases de test + `SensorSeedDataContractTests`.
2e. `make lint-backend`.

**Paso 3 — andamiaje frontend** *(puede arrancar en paralelo con el paso 2 una vez congelados los
contratos de §1.1/§1.4).*
3a. `fetcher.ts` (query + `getBlob`) y `common/app/utils/download.ts` — pequeños, independientes,
    desbloquean todo lo demás.
3b. `layers/sensors/nuxt.config.ts`, ambos locales, `types/`, `constants/`, `utils/api/sensors.ts`.
    **Reiniciar el dev server.**
3c. `utils/history-filters.ts` + `composables/useHistoryFilters.ts`.

**Paso 4 — shell de la página.** `pages/dashboard/history.vue` + `HistoryFilters.vue` +
`HistoryDateRange.vue`, el toggle `UTabs`, los cuatro composables de query, la entrada de nav.
En este punto la página carga y la URL hace round-trip sin visualización.

**Pasos 5 y 6 — independientes entre sí, pueden ir en paralelo:**
- **5 tabla:** `HistoryTable.vue` + `UPagination` + región viva + `keepPreviousData`.
- **6 gráficos:** `utils/history-chart.ts` → `HistoryLineChart.client.vue` → `HistoryChartGrid.vue`
  → `HistoryPlotAveragesChart.client.vue`.

**Paso 7 — export.** `HistoryExportMenu.vue`, `useHistoryExport.ts`, `utils/history-export.ts`.
Depende de 3a y de las vistas de export del backend.

**Paso 8 — e2e** (calentar Vite cargando una página primero).
8a. Entradas `T` en `helpers.ts`.
8b. `sensors.spec.ts` — **el test 12 (descarga CSV) primero** para de-riesgar §5.1.
8c. El test de nav en `dashboard.spec.ts`.
8d. `e2e/backend/api_sensors_history.spec.ts` + helper de auth (independiente, paralelizable).
8e. La adición a `a11y.spec.ts` **al final**, con el markup ya congelado.

**Paso 9 — docs.** Las cuatro actualizaciones de §5, más la retrospectiva que pide el `CLAUDE.md`
raíz. Candidatas a regla: la trampa del param reservado `format` de DRF, el desempate `-id` en
paginación, "anclar `now` o Vue Query entra en bucle", y el cuerpo de error como Blob.

---

## Archivos críticos

- [backend/sensors/models.py](backend/sensors/models.py) — la cadena `SensorMeasurement`
- [backend/farm/api.py](backend/farm/api.py) — `get_owned_or_404`, patrón de scoping
- [backend/sensors/fixtures/initial_sensors.json](backend/sensors/fixtures/initial_sensors.json)
- [backend/sensors/management/commands/seed_weather_readings.py](backend/sensors/management/commands/seed_weather_readings.py) — molde del seeder
- [frontend/layers/common/app/utils/api/fetcher.ts](frontend/layers/common/app/utils/api/fetcher.ts)
- [frontend/layers/farm/app/composables/useFarmWeatherQuery.ts](frontend/layers/farm/app/composables/useFarmWeatherQuery.ts) — molde de composable de query
- [frontend/layers/dashboard/app/pages/dashboard/index.vue](frontend/layers/dashboard/app/pages/dashboard/index.vue) — molde de página + toggle de vista
- [frontend/layers/dashboard/app/utils/view-mode.ts](frontend/layers/dashboard/app/utils/view-mode.ts) — molde de parse/persist de estado de URL
- [e2e/frontend/helpers.ts](e2e/frontend/helpers.ts) — `loginAs`, `gotoHydrated`, mapa `T`
