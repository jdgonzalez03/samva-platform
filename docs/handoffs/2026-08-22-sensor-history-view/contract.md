# API contract — Historial de sensores

Slug: `2026-08-22-sensor-history-view` · Contexto: [`spec.md`](spec.md) · [`acceptance-criteria.md`](acceptance-criteria.md)

**Summary.** Seis endpoints de solo lectura, acotados por propietario, montados bajo
`api/sensors/`, que alimentan `/dashboard/history`. Backend y frontend se construyen **en
paralelo contra este documento**, no uno contra el otro. Este contrato es la autoridad: si un
lado no puede honrarlo, se actualiza aquí y el otro lado se ajusta — nunca se envían interfaces
divergentes.

Este feature es el **primero del repo** en usar paginación DRF, filtrado por query-params y
exportación en streaming. Las afirmaciones del contrato anterior
(`2026-08-22-dashboard-farm-map-and-plots`) *"No pagination anywhere … No query params on any
endpoint"* dejan de ser ciertas **solo para estos endpoints**; los de `farm/` no cambian.

## Entities

| Entity | Campos que este contrato expone |
|---|---|
| `HistoryVariable` | `variable_id`, `semantic_key`, `name`, `unit` |
| `SensorReading` | `id`, `recorded_at`, `plot_id`, `plot_name`, `sensor_id`, `sensor_name`, `variable_id`, `semantic_key`, `variable_name`, `value`, `unit` |
| `ReadingsPage` | `count`, `page`, `page_size`, `results: SensorReading[]` |
| `HistorySeries` | `variable_id`, `semantic_key`, `name`, `unit`, `bucket_seconds`, `points: SeriesPoint[]` |
| `SeriesPoint` | `t` (ISO 8601 UTC, inicio del bucket), `value` (float), `sample_count` (int) |
| `PlotAverage` | `plot_id`, `plot_name`, `variable_id`, `semantic_key`, `variable_name`, `unit`, `average` (float), `sample_count` (int) |

## Endpoints

**Auth (todos).** `Authorization: Bearer <access>`, `permission_classes = [IsAuthenticated]`.
Sin token → **401**.

**Ownership (todos).** El scope se resuelve por lookup (`owner__user=request.user` /
`farm__owner__user=request.user`), nunca por `request.user.farmer`. Una finca o un lote que
existe pero pertenece a otro dueño devuelve **404** con el cuerpo genérico
`{"detail": "Not found."}` — indistinguible de uno inexistente. **Nunca 403.**
Caso sutil obligatorio: un lote que el usuario **sí posee** pero que pertenece a una finca
**distinta** del `farm_id` de la ruta también da **404**.

**Query params compartidos** (`variables`, `readings`, `series`, `plot-averages`, ambos `export/*`):

| param | tipo | default | notas |
|---|---|---|---|
| `plot` | int | ausente = **todos los lotes de la finca** | debe pertenecer a `farm_id`, si no 404 |
| `variable` | `semantic_key` | ausente = **todas las variables** | uno de `soil_moisture`, `air_temperature`, `solar_radiation`, `relative_humidity`, `other` |
| `date_from` | ISO 8601 datetime | `date_to − 7 días` | |
| `date_to` | ISO 8601 datetime | `timezone.now()` | |

Validación (`SensorHistoryFilterSerializer`): `date_from < date_to`; span ≤ **90 días**
(`HISTORY_MAX_RANGE_DAYS`); fecha ilegible o `variable` fuera de las choices → **400** con el
mapa `{campo: [mensajes]}` estándar de DRF.

**Filtros de datos aplicados en todos los endpoints de lectura:**
`sensor_variable__sensor__is_active=True`, `value__isnull=False`,
`recorded_at__gte=date_from`, `recorded_at__lt=date_to`.

---

### 1. `GET sensors/farms/<farm_id>/history/variables/`

Las variables que los sensores **activos** de la finca (o del lote, si se pasa `plot`)
realmente miden. Alimenta el `<USelectMenu>` de variable. Ordenado por `name`.
Solo `plot` afecta el resultado. Los demás params compartidos **se validan igual** —una fecha
ilegible o un `variable` fuera de las choices devuelve 400— pero no se aplican a la query, para
que AC19 ("cualquier endpoint del historial") se cumpla sin excepciones. Devuelve un **array
plano, sin paginar**.

**200 OK**
```json
[
  { "variable_id": 1, "semantic_key": "air_temperature",   "name": "Temperatura del aire", "unit": "°C" },
  { "variable_id": 4, "semantic_key": "soil_moisture",     "name": "Humedad del suelo",    "unit": "%" }
]
```

- Una variable medida **solo por un sensor inactivo** está **ausente**.
- Una finca sin sensores devuelve `[]` (200, no 404).

**Errores.** 401 sin token. 404 si la finca no es del usuario o el `plot` no pertenece a la finca.

Satisface **AC5**, **AC6**.

---

### 2. `GET sensors/farms/<farm_id>/history/readings/`

La tabla paginada. Params compartidos + `page` (int, 1-based) y `page_size` (int, default 20,
máx 100).

**Orden: `-recorded_at`, `-id`.** El desempate por `-id` **no es opcional**: el seeder escribe
todas las variables de un sensor en el *mismo* instante, y sin él Postgres puede reordenar los
empates entre la query de página 1 y la de página 2, haciendo que filas se repitan o desaparezcan.

**200 OK**
```json
{
  "count": 23040,
  "page": 1,
  "page_size": 20,
  "results": [
    {
      "id": 918273,
      "recorded_at": "2026-08-22T14:30:00Z",
      "plot_id": 1, "plot_name": "Lote La Colina",
      "sensor_id": 3, "sensor_name": "Sensor 3 — Lote 1",
      "variable_id": 1, "semantic_key": "air_temperature", "variable_name": "Temperatura del aire",
      "value": 27.4133,
      "unit": "°C"
    }
  ]
}
```

- **`value` es un número JSON (float), no un string.** Precedente: `FarmWeatherAPIView` hace
  `float(...)`. NO usar el `DecimalField` por defecto de DRF, que renderiza `"27.4133"` como
  hace `Plot.area_hectares`.
- `recorded_at` termina en `Z` (`USE_TZ=True`, `TIME_ZONE='UTC'`).
- **`next` / `previous` se omiten deliberadamente.** DRF los construye como URLs absolutas desde
  el request, que bajo la topología docker resuelven al host interno `backend:8000`; y
  `UPagination` necesita `total` + `page` + `itemsPerPage`, nunca una URL.
- Filas con `value = null` están ausentes.
- La columna `plot_name` viene siempre; el frontend decide si la muestra.

**Errores.** 401 · 404 (finca/lote ajeno) · 400 (rango inválido o sobre el tope) ·
**404 si `page` está más allá de la última página** (comportamiento estándar de DRF; el
frontend acota `page` contra `count` para no provocarlo).

Satisface **AC9**, **AC10**, **AC11**, **AC12**.

---

### 3. `GET sensors/farms/<farm_id>/history/series/`

Las series temporales para los gráficos. **Requiere `plot`.** Una serie por variable que el
lote mide (o una sola si se pasa `variable`).

**Bucketing server-side** — 30 días de puntos crudos no caben en un gráfico. `date_bin` de
PostgreSQL (PG 15 disponible), anclado al inicio del rango pedido:

| Span del rango | `bucket_seconds` | Máx puntos/serie |
|---|---|---|
| ≤ 2 días (preset 24h) | 900 (15 min) | 192 |
| > 2 y ≤ 8 días (preset 7d) | 3600 (1 h) | 192 |
| > 8 y ≤ 40 días (preset 30d) | 21600 (6 h) | 160 |
| > 40 días (personalizado) | 86400 (1 día) | ≤ 90 |

**200 OK**
```json
[
  {
    "variable_id": 1, "semantic_key": "air_temperature",
    "name": "Temperatura del aire", "unit": "°C",
    "bucket_seconds": 3600,
    "points": [
      { "t": "2026-08-15T00:00:00Z", "value": 21.83, "sample_count": 4 },
      { "t": "2026-08-15T01:00:00Z", "value": 21.14, "sample_count": 4 }
    ]
  }
]
```

- `value` es el **promedio del bucket**, no una lectura cruda. Float.
- **Los buckets vacíos se OMITEN** — nunca se envían como `value: 0` ni como `null`.
  Por eso `bucket_seconds` viaja en el cable: el frontend rellena los huecos con `null` para
  que la línea se corte en vez de dibujar una recta mentirosa sobre datos ausentes.
- Series ordenadas por `name`; puntos por `t` ascendente.
- **Dos variables que comparten `semantic_key` siguen siendo dos series distintas** —
  la identidad es `variable_id`.
- Un lote sin lecturas devuelve `[]` (200).

**Errores.** 401 · 404 · 400 (rango inválido) · **400 si falta `plot`**.

Satisface **AC2**, **AC3**, **AC7**, **AC8**.

---

### 4. `GET sensors/farms/<farm_id>/history/plot-averages/`

El modo solo-finca: el promedio de cada variable en cada lote, sobre el rango.
Ignora `plot` si se pasa. Sin paginar.

**200 OK**
```json
[
  {
    "plot_id": 1, "plot_name": "Lote La Colina",
    "variable_id": 4, "semantic_key": "soil_moisture", "variable_name": "Humedad del suelo",
    "unit": "%", "average": 41.27, "sample_count": 2880
  }
]
```

- Ordenado por `plot_name`, luego `variable_name`.
- **Un lote sin lecturas está simplemente ausente** — no se envía con `average: null`. El
  frontend ya tiene la lista completa de lotes (`useFarmPlotsQuery`) y pinta "sin datos" en el
  hueco. Esto mantiene el endpoint en una sola query en vez de forzar un LEFT JOIN.
- `average` es float; `sample_count` es el número de lecturas promediadas.

**Errores.** 401 · 404 · 400 (rango inválido).

Satisface **AC4**.

---

### 5–6. `GET sensors/farms/<farm_id>/history/export/csv/` y `.../export/json/`

Exportan **todo el set filtrado**, no la página visible. Mismos query params compartidos
(sin `page`). Mismo orden que `readings`. Respuesta en **streaming**
(`StreamingHttpResponse`), memoria constante en el servidor.

**Dos rutas separadas, NO `?format=`.** Esto es una trampa, no estilo:
`api_settings.URL_FORMAT_OVERRIDE` es literalmente `'format'`, así que `?format=csv` haría que
DRF busque un renderer llamado `csv` y devuelva **404 "Invalid format"**.

**200 OK — CSV** · `Content-Type: text/csv; charset=utf-8`
Cuerpo: **BOM UTF-8** (`﻿`) + cabecera + filas.
```
recorded_at,plot,sensor,variable,semantic_key,value,unit
2026-08-22T14:30:00Z,Lote La Colina,Sensor 3 — Lote 1,Temperatura del aire,air_temperature,27.4133,°C
```
El BOM es obligatorio: sin él, Excel en Windows renderiza `°C` y `Radiación` como mojibake.

**200 OK — JSON** · `Content-Type: application/json`
Un array de objetos con las **mismas filas y el mismo orden** que el CSV, con las claves de
`SensorReading` (menos `id`). Se emite en streaming (`'['` + `json.dumps` unidos por `','` + `']'`),
**nunca** con `JsonResponse`, que bufferea todo en memoria.

**`Content-Disposition`** (ambos):
`attachment; filename="historial-sensores-<slug-finca>-<YYYYMMDD>_<YYYYMMDD>.csv"` más la
variante `filename*=UTF-8''<quote(...)>`.
El frontend **construye el nombre en cliente** y no depende de leer esta cabecera — hacerlo
exigiría `Access-Control-Expose-Headers` en la topología cross-origin de desarrollo.

**Tope de filas.** `HISTORY_EXPORT_ROW_CAP = 50_000`. Se cuenta primero; al excederlo:

**400 Bad Request**
```json
{ "detail": "El rango seleccionado supera el máximo exportable.",
  "code": "export_too_large", "count": 68320, "limit": 50000 }
```
**Rechazar antes que truncar**: un CSV truncado en silencio es un bug de integridad que el
usuario no puede ver. `count` y `limit` viajan para que el mensaje sea accionable.

**Errores.** 401 · 404 · 400 (rango inválido, o `export_too_large`).

Satisface **AC13**, **AC14**, **AC15**, **AC16**.

## Surfaces

| Surface / ruta | Endpoint(s) |
|---|---|
| `/dashboard/history` — selector de variable | 1 (`variables`) |
| `/dashboard/history?view=table` | 2 (`readings`) |
| `/dashboard/history?view=chart&plot=<id>` | 3 (`series`) |
| `/dashboard/history?view=chart` (sin `plot`) | 4 (`plot-averages`) |
| Botón Exportar → CSV / JSON | 5 / 6 |

## Decisions

1. **Endpoints separados, no un `?mode=`.** Las tres formas de lectura son tipos genuinamente
   distintos (sobre de paginación / lista de series / matriz lote×variable); una unión
   discriminada contaminaría el serializer *y* los tipos TS. Además el caché difiere
   (`readings` quiere `keepPreviousData` por página, `series` no), y solo `readings` pagina.
   `readings` se implementa como un `APIView` que instancia `SensorHistoryPagination` a mano
   (`paginate_queryset` + `get_paginated_response`) en vez de un `generics.ListAPIView`. La forma
   del cable y los códigos de estado son idénticos, incluido el 404 de DRF al pedir una página más
   allá de la última.
2. **Paginación solo a nivel de vista.** NO tocar `DEFAULT_PAGINATION_CLASS`: envolvería
   `FarmListAPIView` y `FarmPlotListAPIView`, rompiendo `farm/tests.py` (que hace
   `response.json()[0]`) y los tipos `Farm[]` / `Plot[]` del frontend.
3. **Filtrado a mano con `serializers.Serializer`, sin `django-filter`.** La superficie son 4
   params y 3 necesitan validación cruzada que un `FilterSet` no hace (el lote debe pertenecer
   a *esta* finca; `from < to`; span ≤ tope). `DEFAULT_FILTER_BACKENDS` es global y tocarlo
   pone en riesgo los endpoints de `farm`. La decisión no está cerca.
4. **`variable_id` identifica; `semantic_key` presenta.** `semantic_key` **no es único** en
   `EnvironmentalVariable`. El filtro `?variable=` sí toma un `semantic_key`, manteniendo el
   precedente del cable de `FarmWeatherAPIView`.
5. **`other` (barométrica) NO se excluye del historial**, a diferencia del endpoint de clima.
   Única divergencia deliberada entre ambos.
6. **Sin migración de índices.** `SensorMeasurement.Meta` ya tiene
   `Index(fields=['sensor_variable', 'recorded_at'])`, que lidera con `sensor_variable_id` —
   exactamente la forma que necesitan estas queries, que siempre se acotan por ownership
   primero. Añadir una migración solo si `EXPLAIN ANALYZE` con ~150k filas muestra un bitmap
   heap scan dominando. Medición, no especulación.
7. **El cliente materializa el archivo, el servidor no.** El JWT vive en `localStorage` y solo
   el fetcher inyecta `Authorization`, así que la descarga no puede ser un `<a href>` plano:
   fetch con auth → `Blob` → `createObjectURL` → click sintético → `revokeObjectURL`. ~5–7 MB
   en el tope, aceptable. Con `responseType: 'blob'`, ofetch entrega el cuerpo de **error**
   también como Blob — el 400 del tope se lee con `JSON.parse(await error.data.text())`.
8. **`now` debe estar anclado en el frontend.** Si `date_to` fuera `Date.now()` dentro de un
   computed, cada re-render produciría un valor nuevo, re-clavearía cada query key de Vue Query
   y refetchearía sin fin. Se mantiene un `rangeAnchor` que solo cambia con un filtro o un
   "Actualizar" explícito.
9. **Zona horaria.** El backend es UTC. Las fechas personalizadas se eligen como días de
   calendario **locales**, así que el frontend convierte *inicio del día local* → UTC ISO y
   *fin del día local* → UTC ISO. Sin esto, "22 de agosto" significa en silencio las 24 horas
   equivocadas en Bogotá (UTC−5). Es el bug clásico aquí.

## Amendments

Enmendado tras la implementación del backend (2026-08-22), porque este documento se declara
autoridad y debe reflejar lo que se construyó:

- **§1 `variables/`** — pasa de "los demás params se ignoran" a "se validan pero no se aplican".
  El contrato original chocaba con **AC19**, que exige 400 ante un rango inválido en *cualquier*
  endpoint del historial. Impacto en el frontend: **cero** si manda `plot` o fechas válidas.
- **§Decisions 1** — `readings` es un `APIView` que pagina a mano, no un `generics.ListAPIView`.
  Decisión interna de implementación; **la forma del cable no cambia**.

Ninguna de las dos altera un payload, un código de estado ni un nombre de campo, así que no
requieren que el frontend se ajuste.

## Open questions

Ninguna. Las diez decisiones abiertas se resolvieron con el usuario antes de este contrato y
están registradas en [`spec.md`](spec.md) §Resolved decisions.
