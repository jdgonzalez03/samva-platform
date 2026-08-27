# frontend review — Historial de sensores

Slug: `2026-08-22-sensor-history-view` · Rebanada: frontend (layer `sensors`, `common/utils/download.ts`,
`common/utils/api/fetcher.ts`, layout + locales de `dashboard`, `frontend/CLAUDE.md`, `docs/ARCHITECTURE.md`)

## Verdict

CHANGES REQUESTED — 4 hallazgos bloqueantes, 10 no bloqueantes.

La rebanada está bien construida: la layer respeta el ADR, el `rangeAnchor` funciona (no hay bucle
de refetch), la conversión de día local → UTC es **exacta** en UTC−5, el export con JWT es correcto
de punta a punta (blob, filename, revoke, tope 400 leído del Blob), la tabla y la paginación cumplen
sus ACs de accesibilidad, y el escaneo de axe en modo oscuro sale limpio en las cinco superficies.
Lo que bloquea es un bug de veracidad del gráfico (los huecos se dibujan como **0**, no como corte),
un control de filtro sin etiqueta accesible, y dos estados de URL que dejan la vista atrapada en un
404 del que "Reintentar" no puede salir.

## How this was verified

Sin `git`. Lectura de los 26 archivos de `layers/sensors/`, `fetcher.ts`, `download.ts`,
`dashboard.vue`, ambos locales de `dashboard`, `frontend/CLAUDE.md` y `docs/ARCHITECTURE.md`,
contrastados con `contract.md` (incl. `## Amendments`), `acceptance-criteria.md`, `plan.md` §2 y
`frontend.md`.

Comandos: `npm run lint` ✅ · `npm run typecheck` ✅ · `npm run build` ✅ (8.56 MB, sin warnings de
la layer).

Verificación dinámica: `npm run dev` + Chromium real (Playwright del repo, `locale: es-CO`,
`timezoneId: America/Bogota`, `colorScheme` light y dark) con **la API mockeada** en
`http://localhost:8000/api/**` (fincas 1 y 2, lotes, variables, readings paginadas, series con
huecos deliberados, plot-averages, export CSV/JSON, 400 `export_too_large`, 500, 404 de lote ajeno).
21 escenarios: carga inicial y detección de bucle en reposo, cambio de finca, enlace compartido con
`plot` de otra finca, `?page=` fuera de rango, rango personalizado elegido en el calendario
(comprobando los ISO en el cable), huecos en series de temperatura y de radiación solar, serie
dispersa (1 punto), tabla + paginación + foco + tamaño de objetivo, tabs por teclado + anillo de
foco, export CSV real (evento `download`, BOM, `createObjectURL`/`revokeObjectURL`), tope de export,
fallo 500 + Reintentar, vacíos, `/en/...`, `ariaSnapshot()` de la barra de filtros y del popover, y
`@axe-core/playwright` con `['wcag2a','wcag2aa','wcag21aa','wcag22aa']` sobre `/dashboard` (línea
base preexistente) y las cinco superficies del historial, en claro y oscuro, con y sin overlays.

Además, `history-filters.ts`, `history-chart.ts` y `history-export.ts` se ejecutaron como funciones
puras bajo `TZ=America/Bogota` (Node con type-stripping) para fijar los bordes de zona horaria y de
`fillBuckets` sin pasar por el DOM.

## Blocking

### B1 — Los huecos se dibujan como **0** y la línea nunca se corta: el gráfico miente

`frontend/layers/sensors/app/components/sensors/HistoryLineChart.client.vue:41-44` (y el `null` que
produce `frontend/layers/sensors/app/utils/history-chart.ts:61-68`).

```ts
// `null` reaches the line as-is, and with `interpolateMissingData` off (the
// default) the line breaks over a real gap instead of drawing a straight
// segment across hours nothing was recorded.
const yAccessor = (point: ChartPoint): number | null => point.value
```

El comentario afirma lo contrario de lo que hace Unovis. En
`node_modules/@unovis/ts/components/line/index.js` (`Line._render`):

```js
const value = (isNumber(rawValue) || (rawValue === null)) && isFinite(rawValue) ? rawValue : config.fallbackValue
const defined = config.interpolateMissingData ? ... : isFinite(value)
...
y: this.yScale(value ?? 0)
```

`isFinite(null) === true` en JS, así que un `null` queda **`defined: true`** y se dibuja en
`yScale(0)`. Solo `undefined`/`NaN` producen `defined: false` (y por tanto el corte). Lo dice la
propia doc del config: *"if you set it to `null`, the values will be treated as numerical `0` values
and the line won't break"*.

Escenario de fallo concreto (reproducido en Chromium): serie `solar_radiation` de 7 días, bucket
1 h, **a la que le faltan las últimas 6 horas** — exactamente el hueco que el seeder del backend
siembra a propósito (`plan.md` §1.7: *"sembrar un `sensor_variable` sin sus últimas 6 horas"*). El
gráfico dibuja una **línea plana en 0 W/m² hasta el borde derecho**, indistinguible de "de noche" o
de "el sensor leyó cero". No hay corte, no hay hueco, no hay ninguna señal de dato ausente; el
resumen `sr-only` sí dice la verdad (`648 lecturas ... hasta 22/8/26, 15:40`), así que la versión
visual y la textual se contradicen. En una variable cuyo dominio no llega a 0 (temperatura) el
efecto es un **desplome vertical fuera del eje y una recuperación** en los bordes del hueco: se lee
como una caída real de la medición.

Esto incumple lo que el contrato pone por escrito como razón de existir de `bucket_seconds`
(*"el frontend rellena los huecos con `null` para que la línea se corte en vez de dibujar una recta
mentirosa"*), y hace falso el ✓ de AC2/AC3 en tanto "gráfico correcto".

**Fix:** que el bucket ausente llegue al acceso como `undefined` (o `NaN`), no `null` — p. ej.
`ChartPoint.value?: number` y `grid.push({ t, value: byBucket.get(slot) })`, o
`const yAccessor = (p) => p.value ?? undefined`. Ajustar también la guarda de `tooltipTemplate`
(`HistoryLineChart.client.vue:76-79`) y el filtro `drawnPoints` (`:46-48`). La aserción que lo fija
(y que QA puede correr sin depender de píxeles): sobre una serie con un hueco real, el `d` del path
de la línea debe contener **≥ 2 comandos `M`**. Hoy contiene 1.

### B2 — El campo de fechas tecleadas no tiene nombre accesible: AC-A11Y-7 no se cumple

`frontend/layers/sensors/app/components/sensors/HistoryDateRange.vue:81-89`.

El `<UFormField :label="t('sensors.history.range.typed')">` renderiza
`<label for="v-0-13">Fechas (inicio y fin)</label>`, pero `#v-0-13` es un
**`<input aria-hidden="true" tabindex="-1">`** interno de Reka. Los seis segmentos que sí reciben el
foco son `div[role="spinbutton"]` con `aria-label` `"day,"`, `"month, "`, `"year, "` — **repetidos
dos veces** (inicio y fin) y **en inglés**, también en `/dashboard/history` (español) y en
`/en/...`. Verificado con `ariaSnapshot()` y leyendo `label[for]` → target en el DOM:

```
- text: Fechas (inicio y fin)
- group:                       ← sin nombre accesible
  - spinbutton "day,": dd      ← ¿inicio o fin? no hay forma de saberlo
  - spinbutton "month,": mm
  - spinbutton "year,": aaaa
  - spinbutton "day,": dd
  ...
```

Escenario de fallo concreto: un usuario de lector de pantalla tabula desde "Limpiar filtros"
(posición 11 del orden de tabulación) y oye *"day, cuadro de número"* seis veces seguidas, sin que
nunca se anuncie "Fechas (inicio y fin)" ni cuál triplete es la fecha inicial. Es exactamente la
misma trampa que el ingeniero documentó y evitó para `USelectMenu`, no aplicada a `UInputDate`.

Esto incumple AC-A11Y-7 (*"cada control (lote, variable, rango, **fechas personalizadas**) tiene una
etiqueta asociada programáticamente"*, 1.3.1 / 3.3.2 / 4.1.2) sobre una superficie que esta rebanada
introduce, y hace falso el ✓ del self-check, que afirma *"el rango personalizado añade el
`UInputDate` etiquetado 'Fechas (inicio y fin)'"*. Además mete inglés en la UI española (AC23).

**Fix:** nombrar el grupo y los segmentos (p. ej. `aria-label` en el `UInputDate` más los
`aria-label` traducidos de los segmentos que expone Reka, o dos campos separados "Desde"/"Hasta"), y
comprobarlo con `ariaSnapshot()` como se hizo con los `USelect`.

### B3 — El `plot` de la URL nunca se reconcilia contra los lotes de la finca activa

`frontend/layers/sensors/app/composables/useHistoryFilters.ts:160-167`.

```ts
watch(farmId, (next, previous) => {
  if (previous === null || next === previous) return   // ← el agujero
  if (route.query.plot === undefined) return
  applyQuery({ plot: undefined }, { replace: true })
})
```

La guarda `previous === null` desactiva el reseteo justo en la primera resolución de la finca, que
es cuando llega un `plot` de la URL. Dos fallos concretos, ambos reproducidos:

1. **Estado atrapado (permanente).** Con `selectedFarmId = 2` en `localStorage` (el usuario cambió
   de finca en otra visita, o abre un enlace compartido con AC7), abrir
   `/dashboard/history?plot=1&view=chart` dispara `2/history/variables/?plot=1` y
   `2/history/series/?plot=1` → **404 × 2**, `role="alert"` "No se pudo cargar el historial." y un
   "Reintentar" que reemite el mismo 404 para siempre. El `?plot=1` nunca se limpia. Y el `USelect`
   de Lote muestra el valor crudo **"1"** como etiqueta visible (no existe entre sus ítems: la
   finca 2 tiene los lotes 11 y 12), así que la barra de filtros miente sobre el filtro aplicado.
   La única salida es "Limpiar filtros" — que ni siquiera se renderiza si el único filtro fuera
   `page` (`hasActiveFilters`, `:83-88`).
2. **404 transitorios en cada cambio de finca (AC6).** Aun cuando el watcher sí dispara, el
   `router.replace` es asíncrono mientras las query keys se re-clavean con el nuevo `farm_id` de
   forma síncrona: al cambiar de El Tesoro a San Vicente con `?plot=1` puesto se observan
   `404 2/history/variables/?plot=1` y `404 2/history/series/?plot=1&...` antes de los 200 buenos.
   AC6 exige literalmente *"la vista se recarga con los datos de la nueva finca, **sin errores
   404**"*, y el self-check afirma "Sin 404". No lo es.

**Fix:** aplicar la regla que ya está escrita en `frontend/CLAUDE.md` ("…es reconciliada contra la
lista que devolvió el backend en vez de confiarse de lo almacenado, así reload, cambio de usuario y
registros borrados caen con una sola regla") también al `plot` que viene de la URL: derivar
`plotId` como `null` cuando no está en `useFarmPlotsQuery(farmId).data` (y limpiar el param), lo que
cierra los dos casos de una vez — el enlace compartido y la carrera del cambio de finca.

### B4 — `?page=` fuera de rango no se acota en el primer render → 404 sin salida

`frontend/layers/sensors/app/pages/dashboard/history.vue:92-96`.

```ts
watch([pageCount, page], () => {
  if (page.value > pageCount.value) setPage(pageCount.value)
})
```

El watcher **no es `immediate`**, así que en la carga inicial no corre: `page` viene de la URL,
`pageCount` vale 1 (aún no hay `count`) y ninguno de los dos cambia después, porque la petición
falla y `readingsPage` se queda en `undefined`. El acotado solo funciona para un `count` que
encoge *después* de montar.

Escenario de fallo concreto (reproducido con un mock que replica el 404 de DRF): abrir
`/dashboard/history?view=table&page=4` cuando el rango solo tiene 3 páginas — un enlace marcado o
compartido (AC7 lo bendice explícitamente) cuya ventana rodante de 7 días hoy tiene menos lecturas.
Resultado: una sola petición `page=4` → 404 → `role="alert"` de error, 0 filas, "Reintentar"
reemitiendo el mismo 404, la paginación no se renderiza (no hay por dónde volver) y la región viva
anuncia el absurdo **"0 lecturas. Página 999 de 1."**. El contrato asigna esta salvaguarda al
frontend (*"el frontend acota `page` contra `count` para no provocarlo"*, §2) y las Gotchas del
handoff la dan por hecha.

**Fix:** acotar en el derivado en vez de en un efecto (`page = min(parsePageNumber(...), pageCount)`)
o `{ immediate: true }` en el watcher — y, ya que el 404 no es reintentable (el `retry` de
`useHistoryReadingsQuery:45-46` ya lo sabe), no ofrecer "Reintentar" para ese caso o resetear a la
página 1.

## Non-blocking

### N1 — Cada cambio de rango dispara una petición de más
`useHistoryFilters.ts:127-141`: `rangeAnchor.value = Date.now()` muta **antes** de que la URL
cambie, así que la key se re-clava una vez con el preset viejo y el ancla nueva, y otra con el
preset nuevo. Medido: pasar de "Últimos 7 días" a "Últimas 24 horas" emite 2 peticiones a
`series/` (la primera, la ventana de 7 días completa — la cara). Entrar en "Personalizado" emite 2
más. No es un bucle y las keys son deterministas, pero es trabajo desperdiciado y basura en la
caché. Mover el ancla al mismo tick que la navegación (o guardarlo también en la URL) lo cierra.

### N2 — El hook de DOM que el handoff le promete a QA no existe
`frontend.md` § "DOM hooks shipped" dice `#sensors-history`; el id real que renderiza
`UDashboardPanel` es **`dashboard-panel-sensors-history`**. Un `page.locator('#sensors-history')`
cuelga 30 s y falla. (El resto de la tabla de hooks sí se verificó correcta, incluido el aviso de
`getByRole('row')` = 22 vs `tbody tr` = 20, que confirmé.)

### N3 — El estado de error tarda ~7 s en aparecer
El `retry` de `useHistoryReadingsQuery:45-46` permite 3 intentos con backoff (1 s + 2 s + 4 s) sobre
un 500; series y plot-averages heredan el `retry: 1` global. Medido: el `role="alert"` de AC24
aparece a los ~7 s, con el esqueleto girando mientras tanto. Funciona, pero para una lectura de
sólo-consulta un presupuesto menor (o un `retryDelay` acotado) haría el fallo mucho menos confuso.

### N4 — El aviso de export nunca se limpia
`useHistoryExport.ts:24-26` expone `clearExportError`, pero nadie lo llama (`history.vue:79` solo
desestructura `exportError`). Tras un 400 de tope, el `role="alert"` inline sigue en pantalla
mientras el usuario reduce el rango, contradiciendo el estado actual de los filtros hasta que
vuelva a exportar.

### N5 — El fin exclusivo suma 86 400 000 ms en vez de avanzar el día local
`history-filters.ts:152` (`localDayStart(to).getTime() + DAY_MS`). En una zona con DST eso cae en
las 23:00 o la 01:00 locales, no en medianoche, y un rango de 90 días puede pasarse del tope por una
hora. Colombia no tiene DST, así que hoy no muerde; `new Date(y, m - 1, d + 1)` lo hace correcto por
construcción. **El comportamiento en UTC−5 sí está verificado y es exacto** (ver §Verified).

### N6 — El "promedio" del resumen sr-only no está ponderado
`history-chart.ts:98-106` promedia los promedios de bucket ignorando `sample_count`, que es
justamente distinto en los buckets parciales de los extremos del rango. La diferencia es pequeña,
pero el texto que anuncia AC-A11Y-2 dice "promedio" a secas.

### N7 — El modo claro es el estado por defecto, no una rareza
Las 3 violaciones `color-contrast` que el self-check declara preexistentes lo son —lo confirmé:
`/dashboard` (página que ya existía) produce **las mismas 3, con los mismos valores** (`#62748e`
sobre `#f1f5f9` 4.34:1 en las iniciales del avatar; blanco sobre `#00c950` 2.21:1 en la pestaña
activa; 4.34:1 en la inactiva) y el mismo `UTabs variant="pill"` ya está en
`dashboard/app/pages/dashboard/index.vue:140-149`. Pero la justificación *"el layout del dashboard
fuerza modo oscuro"* es inexacta: `dashboard.vue:9-11` solo fuerza oscuro cuando la preferencia es
literalmente `'light'`; con la preferencia `'system'` por defecto y un SO en claro, la página
**renderiza en claro** (comprobado con `colorScheme: 'light'`). No bloquea (es deuda del tema, no de
esta rebanada), pero conviene corregir la redacción del caveat.

### N8 — Cero pruebas sobre el código que más las pedía
`history-filters.ts`, `history-chart.ts` y `history-export.ts` son puros y no tienen ninguna prueba;
`frontend/` sigue sin Vitest. La deuda está reconocida en `plan.md` §5.4 y las specs de Playwright
son de QA, así que no lo cuento como bloqueante — pero nótese que **B1 es exactamente el tipo de bug
que ninguna de las dos capas habría atrapado**: `fillBuckets` es correcto en aislamiento y el fallo
vive en el contrato con Unovis. La prueba que hay que escribir es la del `d` del path (≥2 `M`).

### N9 — Tick sin etiqueta en el gráfico de barras
`HistoryBarChart.client.vue:50-56`: con `:num-ticks="bars.length"`, dos lotes producen tres marcas y
la del centro sale sin texto (`formatPlot` devuelve `''`). Cosmético.

### N10 — `fillBuckets` descarta en silencio un punto fuera de la rejilla
`history-chart.ts:54-59`: si `slot >= slots` el punto se guarda en el `Map` y nunca se lee. Hoy no
puede pasar (el mismo rango genera la rejilla en ambos lados), pero es una pérdida silenciosa de
datos si el backend cambiara el origen del `date_bin`.

## Verified — focus areas

| Foco | Resultado |
|---|---|
| **Bucle de refetch** | ✅ No existe. `rangeAnchor` es un `shallowRef` que solo se mueve en `setRangePreset`/`setCustomRange`/`resetFilters`. Carga inicial = 2 peticiones de historial; 8 s en reposo sin interacción = **0 peticiones nuevas**. Ninguna query key contiene un valor que cambie solo (`filters` es un computed de la URL + el ancla; `hashKey` de TanStack lo hashea estructuralmente). Único pero: N1 (dos peticiones por cambio de rango, no infinitas). |
| **Zona horaria (AC8)** | ✅ Exacto en UTC−5, verificado en la unidad **y** en el cable. Un solo día `2026-08-22` → `date_from=2026-08-22T05:00:00.000Z`, `date_to=2026-08-23T05:00:00.000Z`. Elegir 3–7 ago en el calendario real → `date_from=2026-08-03T05:00:00.000Z&date_to=2026-08-08T05:00:00.000Z` (día local completo, fin exclusivo, alineado con el `recorded_at__lt` del backend). Rango invertido → `issue: 'invalid'` y caída a 7 días; 90 días exactos pasan, 91 → `tooLong`; `2026-02-31` se rechaza en `parseCalendarDate`. Ver N5 para el matiz de DST. |
| **Reactividad Vue** | ✅ Sin refs perdidos (todo se desestructura de `useQuery` en `<script setup>`), sin efectos secundarios en `computed`, sin props mutadas. El `draft`/`props` de `HistoryDateRange` no entra en bucle (la guarda `from === props.from` corta el ciclo emit→URL→watch). `shallowRef` para `DateRange` está bien fundado. El único watcher problemático es el de B3 (guarda de más) y el de B4 (falta `immediate`). |
| **Reseteo de lote al cambiar de finca (AC6)** | ⚠️ **Parcial → B3.** El param sí desaparece de la URL y el estado final es correcto, pero por el camino se emiten 2 peticiones 404 con el lote huérfano, y en la primera resolución de la finca (enlace compartido / finca almacenada distinta) el `plot` huérfano **no se limpia nunca**. |
| **Huecos en las series** | ⚠️ `fillBuckets` es **correcto** (rejilla anclada en `date_from`, `null` en los faltantes, `slots = ceil((to-from)/bucket)`, sin fuera-por-uno: comprobado con puntos en el borde inicial, en el final exclusivo y desalineados). El fallo está aguas abajo: Unovis dibuja ese `null` como 0 con la línea continua → **B1**. |
| **Descarga con JWT** | ✅ Evento `download` real desde la URL `blob:` + click sintético, `suggestedFilename()` = `historial-sensores-finca-el-tesoro-20260803_20260807.csv`, BOM preservado, la petición **no lleva `page`**, `createObjectURL`/`revokeObjectURL` = 1/1, cero `<a>` huérfanos en el DOM. El 400 `export_too_large` se lee del **Blob** y sale con `Intl` (`68.320` / `50.000`) en un `role="alert"` inline + toast; un 500 cae al mensaje genérico. Botón deshabilitado con `count: 0` y con 0 gráficos. |
| **Desviación 1 (USelect en vez de USelectMenu)** | ✅ Bien fundada. Los tres controles quedan `combobox "Lote" / "Variable ambiental" / "Rango de fechas"`, con `option`s correctos y el foco intacto tras elegir. El precio (perder el buscador con ≤28 lotes) es razonable. Irónicamente, la misma trampa quedó sin resolver en `UInputDate` → B2. |
| **Desviación 2 (`<figure>` fuera del `.client`)** | ✅ Bien fundada y sin efecto colateral: `figcaption` + resumen `sr-only` existen en SSR y durante la carga, el SVG queda dentro de `div[aria-hidden="true"]` y axe no reporta nada sobre él. |
| **Caveat A11Y-1 nº1 (`aria-hidden-focus`)** | ✅ Preexistente y reproducible: `/dashboard` (página anterior a esta feature) con el desplegable de fincas abierto da `aria-hidden-focus` × 2; el historial con el popover del calendario abierto da × 5. Misma causa (reka marca `aria-hidden` sin `inert`), no introducida aquí. Sin overlays, ambas vistas salen limpias. |
| **Caveat A11Y-1 nº2 (contraste en claro)** | ✅ Preexistente y reproducible: exactamente las mismas 3 violaciones, con los mismos colores y ratios, en `/dashboard`. Ver N7 por la redacción inexacta sobre el modo oscuro. |
| **`frontend/CLAUDE.md`** | ✅ Arrow functions en todos los composables; ni un `fetch`/`$fetch`/`useFetch`; keys desde `SensorsQueryKey` y jerárquicas (`ROOT > HISTORY > <recurso>`); factories `<x>QueryOptions()` como objeto plano con `as const`; `useHead` con título en la página; cero strings sin `t()`; `Intl` siempre con `locale.value`; `import.meta.client` en `download.ts` y en el storage de la vista; handlers de template envueltos para devolver `void`; imports en-layer relativos; el tipo `Plot` cruzado es type-only y el borde `sensors → farm` quedó registrado en `frontend/CLAUDE.md:12` y en `ARCHITECTURE.md:82`; icons solo `i-lucide-*`; componentes `U*`. |
| **Alcance y docs** | ✅ `fetcher.get(url, query?)` + `getBlob` no rompen a ningún llamador (parámetro opcional); `ARCHITECTURE.md` mueve la página a "Working today", añade `sensors` al árbol y corrige la línea 122; la entrada de nav es un `localePath()` (sin dependencia `dashboard → sensors`) y el comentario falso quedó borrado. |

## AC self-check audit

Reproducidos uno a uno contra el código y el navegador. Los que no aparecen (AC1, AC15, AC17–AC21)
son del backend.

| AC | Reclamado | Auditoría |
|---|---|---|
| AC2 / AC3 | ✓ | ⚠️ La grilla, el número de figuras, los ejes Y propios y los `figcaption` son correctos, pero el trazo de la línea no es veraz con datos ausentes (**B1**). |
| AC4 | ✓ | ✅ Un `VisGroupedBar` por variable con el eje X en lotes, más la nota visible "Sin lecturas en este rango para: Lote Sin Mapear." |
| AC5 | ✓ | ✅ Opciones = `history/variables/` (dedup por `semantic_key`) + "Todas las variables"; la key lleva `plot`, así que elegir lote reconsulta (`variables/?plot=1` observado). |
| AC6 | ✓ *"Sin 404"* | ❌ **Falso.** 404 × 2 en cada cambio de finca con `plot` puesto, y estado atrapado en la primera resolución (**B3**). |
| AC7 | ✓ | ⚠️ El round-trip funciona (los 7 params viajan, un filtro limpiado desaparece, recargar reproduce la vista), pero dos URLs válidas de compartir dejan la vista rota: `?plot=` de otra finca (**B3**) y `?page=` fuera de rango (**B4**). |
| AC8 | ✓ | ✅ Reproducido en el cable, exacto (ver §Verified). |
| AC9 / AC10 / AC11 | ✓ | ✅ 20 filas (`tbody tr`), columnas y orden del backend, `?page=2` con filas distintas, columna "Lote" oculta solo con lote elegido (6 vs 5 cabeceras). |
| AC12 | ✓ | ✅ `UEmpty` con texto en tabla y en ambos modos de gráfico; "Exportar" deshabilitado. |
| AC13 / AC14 | ✓ | ✅ Descarga real, nombre `historial-sensores-<slug>-<YYYYMMDD>_<YYYYMMDD>.<ext>` con días **locales**, sin `page` en la petición. |
| AC16 | ✓ | ✅ 400 leído del Blob, mensaje con `count`/`limit` formateados, inline + toast, sin archivo. |
| AC22 / AC23 / AC24 | ✓ | ✅ Link "Historial" navega; `/en/...` traduce título, pestañas, filtros, cabeceras, `<caption>`, paginación y vacíos, con `Intl` por locale (`22/8/26, 9:30` vs `8/22/26, 9:30 AM`); el 500 muestra `role="alert"` + "Reintentar" **dentro** de la alerta y recupera las 20 filas sin recargar (tarda ~7 s, N3). Única fuga de inglés: los segmentos del `UInputDate` (**B2**). |
| AC-A11Y-1 | ✓ + 2 salvedades | ✅ Confirmado: 0 serias/críticas en oscuro en las 5 superficies (y también con `range=custom`); las 2 salvedades son genuinamente preexistentes y las verifiqué contra `/dashboard`. |
| AC-A11Y-2 | ✓ | ✅ SVG en `div[aria-hidden]`, `figcaption` "Nombre (unidad)", resumen con nº de lecturas, rango, mín, máx y promedio (ver N6 por el matiz del promedio). |
| AC-A11Y-3 | ✓ | ✅ Nota visible por grilla, en ambos modos. |
| AC-A11Y-4 | ✓ | ✅ `<caption>` real ("45 lecturas de Finca El Tesoro, de la más reciente a la más antigua.") y 6 `<th scope="col">`. |
| AC-A11Y-5 | ✓ | ✅ `nav` con nombre "Paginación de las lecturas"; tras pulsar "Página 2" el `activeElement` sigue siendo ese botón. |
| AC-A11Y-6 | ✓ | ✅ `aria-live="polite"` anuncia "45 lecturas. Página 1 de 3." / "4 gráficos." y queda vacío mientras hay `isPending`; el foco no se mueve al cambiar de filtro (queda en el combobox). |
| AC-A11Y-7 | ✓ | ❌ **Falso para las fechas personalizadas** (**B2**). Los tres `USelect` sí cumplen. |
| AC-A11Y-8 | ✓ | ✅ `ArrowLeft`/`ArrowRight` cambian de vista y actualizan la URL; el `tabpanel` enfocado muestra `box-shadow ... oklch(0.792 0.209 151.711) 0 0 0 4px`. |
| AC-A11Y-9 | ✓ | ✅ Con el popover abierto el `activeElement` está dentro; `Escape` cierra y devuelve el foco al disparador ("Elegir en el calendario"). El campo tecleado existe — pero sin nombre accesible (**B2**), así que la parte de "no depender del calendario" se cumple solo para quien ve la pantalla. |
| AC-A11Y-10 | ✓ | ✅ Error de carga, aviso de rango y tope de export van en `role="alert"` con texto; iconos `aria-hidden`; el aviso de export es persistente además del toast (ver N4). |
| AC-A11Y-11 | ✓ | ✅ Medido: 7 botones de paginación 32×32, "Exportar" 103×32. |
| AC-A11Y-12 | ✓ | ✅ Ningún gráfico traza dos series en los mismos ejes; título + unidad en cada `figcaption` y etiqueta de eje Y. |

Además, dos afirmaciones de **Gotchas** que no se sostienen: *"`page` acotado en cliente"* (**B4**) y
el hook `#sensors-history` (**N2**). Las de `rangeAnchor`, días locales → UTC, `keepPreviousData`,
`:unmount-on-hide="false"`, `getByRole('row')` = 22 y el cuerpo de error como Blob sí las confirmé.

## Proposed improvements

Solo reglas reusables y de largo plazo; no edito ningún `CLAUDE.md` (lo decide el orquestador con el
usuario). Las propuestas 1, 2, 3, 4, 6 y 7 del handoff me parecen correctas y verificadas —
endorso las seis tal cual, con un matiz en la 7 (el fin exclusivo debe construirse como
`new Date(y, m - 1, d + 1)`, no sumando 86 400 000 ms; ver N5). La 5 también, pero su sitio natural
es `e2e/README.md` junto al resto de las reglas de axe. A eso añado:

1. **Regla:** *En un `VisLine` de Unovis, un dato ausente debe llegar al acceso `y` como `undefined`
   o `NaN`, nunca como `null`: `isFinite(null)` es `true`, así que un `null` se dibuja como un 0
   real con la línea sin cortar (`fallbackValue: null` es literalmente "trátalo como 0"). Fija el
   corte con una aserción sobre el `d` del path (≥ 2 comandos `M` sobre un hueco), no sobre píxeles.*
   **Dónde:** `frontend/CLAUDE.md`, sección nueva "Gráficos (Unovis)".

2. **Regla:** *Todo identificador que venga de la URL o de `localStorage` y termine en una query key
   (lote, finca, sensor…) se reconcilia contra la lista que devolvió el backend antes de usarse: si
   no está, se trata como ausente y se borra el param. Un id huérfano produce un 404 permanente cuyo
   "Reintentar" nunca puede tener éxito.* (Extiende la regla de `useState` ya existente en
   "Composables & state", que hoy solo habla del estado de selección.)
   **Dónde:** `frontend/CLAUDE.md`, sección "Composables & state".

3. **Regla:** *Un índice acotado que vive en la URL (paginación, pestañas, pasos) se acota en el
   valor derivado o con un watcher `{ immediate: true }` — un watcher normal no corre en el primer
   render, que es justo cuando llega el valor fuera de rango de un enlace compartido.*
   **Dónde:** `frontend/CLAUDE.md`, sección "Vue Query (client data)".

4. **Regla:** *No mutes un input de una query key (un ancla temporal, un contador de refresco) fuera
   de la misma navegación que actualiza la URL: la key se re-clava dos veces y dispara una petición
   con el estado viejo antes de la buena.*
   **Dónde:** `frontend/CLAUDE.md`, sección "Vue Query (client data)".

5. **Regla:** *El nombre accesible de cualquier control de Nuxt UI/Reka envuelto en `UFormField` se
   verifica con `ariaSnapshot()` antes de darlo por bueno: `UFormField` apunta su `for` al primer id
   que el componente le ofrezca, que en `UInputDate`/`UCalendar` es un `<input aria-hidden>` interno,
   no el control que recibe el foco.* (Generaliza la propuesta 1 del ingeniero, que solo cubre
   `USelectMenu`/`UInputMenu`.)
   **Dónde:** `frontend/CLAUDE.md`, sección "UI components & icons".

6. **Regla:** *El handoff no publica un selector de DOM para QA sin haberlo ejecutado contra la app:
   los `id` de los componentes de Nuxt UI se prefijan (`UDashboardPanel id="x"` → `#dashboard-panel-x`).*
   **Dónde:** spec del agente `frontend-engineer` (sección del handoff "DOM hooks shipped").
