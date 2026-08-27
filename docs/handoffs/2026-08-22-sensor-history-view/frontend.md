# frontend handoff — Historial de sensores

Slug: `2026-08-22-sensor-history-view` · Contexto: [`spec.md`](spec.md) · [`contract.md`](contract.md) · [`acceptance-criteria.md`](acceptance-criteria.md) · [`plan.md`](plan.md)

**Summary.** Nueva layer `sensors` con la página `/dashboard/history` (+ `/en/...`): filtros de
lote / variable / rango que viajan enteros en la URL, conmutador Gráficos ↔ Tabla, grilla de
gráficos Unovis (líneas por variable, barras agrupadas en modo solo-finca), tabla paginada de 20
filas y exportación CSV/JSON del set filtrado completo. `fetcher` gana query params y `getBlob`;
`common` gana `downloadBlob`.

## Files changed

**Nuevos — `frontend/layers/sensors/`**

```
nuxt.config.ts
i18n/locales/{es,en}.json
app/types/sensors.ts
app/constants/{query-keys,history}.ts
app/utils/api/sensors.ts
app/utils/{history-filters,history-chart,history-export}.ts
app/composables/useHistoryFilters.ts
app/composables/useHistory{Variables,Readings,Series,PlotAverages}Query.ts
app/composables/useHistoryExport.ts
app/pages/dashboard/history.vue
app/components/sensors/HistoryFilters.vue
app/components/sensors/HistoryDateRange.vue
app/components/sensors/HistoryExportMenu.vue
app/components/sensors/HistoryTable.vue
app/components/sensors/HistoryChartGrid.vue
app/components/sensors/HistoryAveragesGrid.vue
app/components/sensors/HistoryChartFigure.vue
app/components/sensors/HistoryLineChart.client.vue
app/components/sensors/HistoryBarChart.client.vue
```

**Nuevo — común**

- `frontend/layers/common/app/utils/download.ts`

**Modificados**

- `frontend/layers/common/app/utils/api/fetcher.ts` — `QueryParams`, `get(url, query?)`, `getBlob()`
- `frontend/layers/dashboard/app/layouts/dashboard.vue` — entrada de nav "Historial"; borrado el
  comentario falso *"History/Predictions stay hidden until those pages exist."*
- `frontend/layers/dashboard/i18n/locales/{es,en}.json` — `dashboard.nav.history`
- `frontend/package.json` / `package-lock.json` — `@internationalized/date` (ver Decisions)
- `frontend/CLAUDE.md` — borde sancionado `sensors → farm`
- `docs/ARCHITECTURE.md` — `farm` y `sensors` en el árbol de layers; bordes 3 y 4 en "Dependency
  direction"; `:122` corregida (predicciones nacen como layer, no como páginas del dashboard); la
  página de historial pasa de "Planned" a "Working today"

## Contract

Consumido tal cual lo describe `contract.md`:

| Endpoint | Consumidor |
|---|---|
| `sensors/farms/<id>/history/variables/` | `useHistoryVariablesQuery` → `<USelect>` de variable (solo manda `plot`) |
| `sensors/farms/<id>/history/readings/` | `useHistoryReadingsQuery` (+ `page`, `page_size=20`) → `HistoryTable` |
| `sensors/farms/<id>/history/series/` | `useHistorySeriesQuery` (solo con `plot`) → `HistoryChartGrid` |
| `sensors/farms/<id>/history/plot-averages/` | `useHistoryPlotAveragesQuery` (solo sin `plot`) → `HistoryAveragesGrid` |
| `sensors/farms/<id>/history/export/{csv,json}/` | `useHistoryExport` → `fetcher.getBlob` → `downloadBlob` |

- `plot` / `variable` se **omiten** cuando el filtro es "todos" (nunca `null`).
- `date_from`/`date_to` son ISO UTC; el rango personalizado convierte *inicio del día local* →
  UTC y *inicio del día siguiente al último elegido* → UTC (fin exclusivo, alineado con el
  `recorded_at__lt` del backend).
- `bucket_seconds` se usa para reinsertar los buckets vacíos (`fillBuckets`), marcados `null` en
  `ChartPoint` y convertidos a `NaN` en el acceso `y` — que es lo que corta la línea en Unovis.
- El 400 `export_too_large` se lee del **Blob** de error (`parseExportError`) y se muestra con
  `count` y `limit` formateados por `Intl`.
- El nombre del archivo se construye en cliente; nunca se lee `Content-Disposition`.

## Contract deviations

Ninguna en el cable. Dos desviaciones respecto al **plan §2**, no al contrato:

1. **§2.4 pedía `<USelectMenu>` para lote y variable.** Se usa `<USelect>`. El trigger de
   `USelectMenu` (Reka Combobox) lleva su propio `aria-label="Show popup"`, que **pisa** la
   etiqueta del `UFormField`: el nombre accesible del control quedaba en inglés y sin relación con
   "Lote"/"Variable ambiental" — falla AC-A11Y-7 y mete inglés en la UI española (AC23). Con
   `USelect` los tres controles quedan `combobox "Lote"`, `combobox "Variable ambiental"`,
   `combobox "Rango de fechas"` (verificado con `ariaSnapshot`). Se pierde el buscador; con ≤28
   lotes el typeahead nativo del listbox alcanza.
2. **§2.7 pedía `HistoryLineChart.client.vue` con el `<figure>` adentro.** El `<figure>`,
   `<figcaption>` y el resumen `sr-only` se extrajeron a `HistoryChartFigure.vue` (no `.client`),
   así la alternativa textual se renderiza en SSR y existe también mientras el gráfico carga; solo
   el `VisXYContainer` es client-only. Mismo motivo para `HistoryAveragesGrid` +
   `HistoryBarChart.client.vue`.

3. **§2.4 / §5 pedían `<UInputDate range />` para la entrada tecleada.** Se usan **dos
   `<UInput type="date">`** ("Desde" / "Hasta"). El control de Reka reparte el foco entre seis
   `div[role="spinbutton"]` con `aria-label` fijos en inglés y da el `for` del `UFormField` a un
   `<input aria-hidden>`, así que la etiqueta no nombraba nada enfocable (AC-A11Y-7, AC23). El
   input nativo es un control que la etiqueta sí posee y cuyos segmentos localiza el navegador.
   Cambio hecho al atender **B2** de la revisión; el `<UCalendar>` del popover no se toca.

Añadidos menores sobre el plan: `resolveRange()` devuelve además un `issue`
(`'invalid' | 'tooLong' | null`) para poder explicar en pantalla por qué un rango personalizado
inválido cayó a 7 días; y `groupAveragesByVariable()` en `history-chart.ts`.

## Review fixes

Los cuatro bloqueantes de [`review-frontend.md`](review-frontend.md) más un quinto hallazgo que el
usuario encontró probando la app (**B5**), corregidos y **verificados
manejando la app en Chromium real** (dev server propio en `:3001`, `locale: es-CO`,
`timezoneId: America/Bogota`, claro y oscuro) — con la API mockeada **y** con la app real y el
usuario sembrado (`juan.perez@email.com`, login 200, datos del seeder). Los scripts de verificación
fueron temporales (scratchpad), no se añadió ningún spec al repo.

**B1 — el gráfico dibujaba los huecos como 0 y nunca cortaba la línea.**
`HistoryLineChart.client.vue`: el acceso `y` emite ahora `NaN`, no `null`
(`point.value ?? Number.NaN`). `isFinite(null)` es `true`, así que Unovis daba el bucket ausente por
`defined` y lo pintaba en `yScale(0)`; un valor no finito cae al `fallbackValue` del `VisLine`
(`undefined` por defecto) y deja el punto sin definir, que es lo que parte el path. `null` sigue
siendo el marcador **dentro** de `ChartPoint` (lo leen `drawnPoints` y el tooltip): la conversión
ocurre solo en el borde con Unovis. Corregido además el docstring de `fillBuckets`, que afirmaba lo
contrario de lo que hacía la librería.
**Cómo se verificó:** (a) hueco a mitad de serie → el `d` del path pasa de **1 a 2 comandos `M`**;
(b) `solar_radiation` de 7 días **sin las últimas 6 h** → el trazo termina en `x=402,6` de `417`
(antes llegaba plano en 0 W/m² hasta el borde); (c) **con el dato real del seeder**: `plot=1` +
`variable=soil_moisture` es el `sensor_variable` al que `seed_sensor_readings` le quita 6 h — su
path termina en `x=447,7` mientras la serie continua `air_temperature` llega a `464,4` (16,7 px de
548 = 6 h sobre 168). El dominio Y no se contamina: temperatura sigue escalando 19–29 °C, sin
desplome ni recuperación en los bordes del hueco.

**B2 — el campo de fechas tecleadas no tenía nombre accesible.**
`HistoryDateRange.vue` sustituye el `<UInputDate range>` por **dos `<UInput type="date">`**
etiquetados "Desde" / "Hasta" (`From` / `To` en inglés). Reka partía aquel control en seis
`div[role="spinbutton"]` con `aria-label` fijos en inglés y apuntaba el `for` del `UFormField` a un
`<input aria-hidden tabindex="-1">`; un `<input type="date">` nativo es **un** control que la
etiqueta sí posee, y el navegador anuncia y ordena sus segmentos en el idioma del usuario. Las
claves i18n `range.typed` → `range.from` / `range.to`. `dark:scheme-dark` para que el glifo del
selector nativo invierta con el tema (1.4.11). El calendario (`UPopover` + `UCalendar`) no cambia.
**Cómo se verificó:** `label[for]` → `INPUT[type=date]` (antes: input oculto); **cero**
`role="spinbutton"` en la barra de filtros; `ariaSnapshot()` da `textbox "Desde"` / `textbox
"Hasta"`; navegación con teclado: Tab llega a los campos, `focus-visible` con anillo primario, y
tecleando `15/08/2026` + `20/08/2026` la URL pasa a `from=2026-08-15&to=2026-08-20` sin tocar el
ratón; el par invertido sigue disparando la alerta de rango; `date_from`/`date_to` siguen siendo el
día local completo con fin exclusivo (`2026-08-01T05:00:00.000Z` → `2026-08-06T05:00:00.000Z`, AC8);
elegir en el calendario sincroniza los dos campos; `/en/...` los nombra `From`/`To`; axe limpio en
las cinco superficies en oscuro y sin violaciones nuevas en claro (solo las 3 preexistentes del
tema); objetivo 128×32 px.

**B3 — el `plot` de la URL nunca se reconciliaba contra los lotes de la finca activa.**
`useHistoryFilters.ts` deriva `plotId` de la lista que devolvió `useFarmPlotsQuery(farmId)`: un id
que la finca no reconoce vale `null`, y un watcher `{ immediate: true }` sobre `[plots, plot de la
URL]` borra el param con `replace`. Sustituye a la guarda `previous === null`, que no cubría la
primera resolución de la finca. Se añade `filtersReady` (falso mientras un `?plot=` sigue sin
confirmar) y las cuatro queries del historial lo respetan — `useHistoryVariablesQuery` gana un
parámetro `isReady` — para que ninguna petición salga con el id huérfano ni gaste una consulta
"toda la finca" que el id confirmado repetiría medio segundo después.
**Cómo se verificó:** enlace compartido `?plot=1&view=chart` con `selectedFarmId=2` en
`localStorage` → **0 respuestas 404** (antes 2 permanentes), URL saneada a `?view=chart`, sin
`role="alert"`, el `USelect` muestra "Todos los lotes" (antes el crudo "1") y se dibujan las 4
figuras; cambio de finca desde el sidebar con `?plot=1` puesto → **0 respuestas 404** (antes 2
transitorias), URL sin `plot`; enlace válido `?plot=1&variable=air_temperature` → exactamente
`plots/` + `variables/?plot=1` + `series/?plot=1&…`, sin duplicados ni parpadeo de barras.

**B4 — `?page=` fuera de rango no se acotaba nunca.**
`history.vue` deriva `isPageOutOfRange` (o el `count` ya dice que la página no existe, o DRF
respondió el 404 que reserva para ese caso) y lo acota en un watcher **`{ immediate: true }`**: con
`count` conocido baja a la última página real, y ante el 404 —que no trae `count` y que
`useHistoryReadingsQuery` ya sabe que no se debe reintentar— vuelve a la página 1. Mientras el
rebote ocurre se muestra el esqueleto en vez de una alerta que el usuario no puede accionar, y la
región viva calla en lugar de anunciar "0 lecturas. Página 999 de 1".
**Cómo se verificó:** `?view=table&page=999` con un mock que replica el 404 de DRF → peticiones
`999,1`, URL final `?view=table`, 20 filas, **sin alerta**, región viva "45 lecturas. Página 1 de
3."; `?page=3` con un `count` que encogió a 20 → peticiones `3,1` y "20 lecturas. Página 1 de 1.";
**`?page=2` legítimo no se toca** (una sola petición, "45 lecturas. Página 2 de 3." — el acotado no
se come los enlaces profundos válidos); un 500 real sigue mostrando `role="alert"` con "Reintentar"
dentro.


**B5 — el gráfico de barras no tenía tooltip.** (Hallazgo del usuario, no de la revisión.)
En modo "Todos los lotes" el hover sobre una barra no mostraba nada, mientras que el de líneas sí.
`HistoryBarChart.client.vue` no montaba ningún tooltip. Se añade un **`VisTooltip` con `triggers`
cableado a `GroupedBar.selectors.bar`** — no un `VisCrosshair` como el de líneas: el crosshair se
engancha a la x más cercana de un eje **continuo**, y este eje es una lista de lotes, así que
señalaría la barra equivocada. El contenido lleva **nombre del lote, promedio + unidad y el
`sample_count`** de esa barra (un promedio sobre 12 lecturas y otro sobre 2.880 dibujan la misma
barra; el número dice cuánto fiarse), todo con `Intl` sobre `locale.value` y la pluralización por
`t()`. `BarPoint` gana `sampleCount`, propagado desde `PlotAverage.sample_count` en
`groupAveragesByVariable`; `HistoryAveragesGrid` pasa `unit` al gráfico; nueva clave
`sensors.history.charts.samples`. El tooltip se construye como DOM con `textContent`, no como HTML:
el nombre del lote es texto que escribe el agricultor y no debe interpretarse como marcado.
**Cómo se verificó:** app real en `localhost:3000/dashboard/history?view=chart` con "Todos los
lotes" y el usuario sembrado: hover sobre **las 8 barras** (4 variables × 2 lotes) → las 8 muestran
su tooltip, p. ej. `Lote El Abrevadero | 39,05 % | 666 lecturas` y
`Lote La Colina | 288,92 W/m² | 666 lecturas`, coherentes con el resumen `sr-only`; al salir de la
barra el tooltip se oculta (0 visibles); en `/en/...` el mismo tooltip sale
`Lote El Abrevadero | 39.05 % | 666 readings` (`Intl` cambia el separador decimal); con un mock de
`sample_count` 1 y 2880 → "1 lectura" / "2880 lecturas" (es-CO no agrupa 4 dígitos); axe limpio con
las barras en pantalla; contraste del tooltip: negro y `#64748b` sobre blanco (4,76:1). Captura:
`v14-tooltip-dark.png`.

**Archivos tocados en esta pasada:** `layers/sensors/app/components/sensors/{HistoryLineChart.client,HistoryDateRange,HistoryBarChart.client,HistoryAveragesGrid}.vue`,
`layers/sensors/app/utils/history-chart.ts`,
`layers/sensors/app/composables/{useHistoryFilters,useHistoryVariablesQuery}.ts`,
`layers/sensors/app/pages/dashboard/history.vue`, `layers/sensors/i18n/locales/{es,en}.json`.

Comandos tras los arreglos: `npm run format` ✅ · `npm run lint` ✅ · `npm run typecheck` ✅ ·
`npm run build` ✅ (8.47 MB). `make frontend-test` no existe como target y `frontend/` sigue sin
Vitest (deuda reconocida, `plan.md` §5.4).

## AC self-check

Verificado en Chromium contra el dev server con la API mockeada (`page.route` sobre
`http://localhost:8000/api/**`) y, tras la revisión, también contra la **app real** con el usuario
sembrado; más `@axe-core/playwright` con `['wcag2a','wcag2aa','wcag21aa','wcag22aa']`. Los scripts
fueron temporales (scratchpad), no se añadió ningún spec al repo. Las filas marcadas **↺** son las
que la revisión tumbó y esta pasada rehízo (ver `## Review fixes`); el ✓ anterior de AC2/AC3, AC6,
AC7 y AC-A11Y-7 **era falso**.

| AC | Estado | Cómo se verificó |
|---|---|---|
| **AC2** | ✓ ↺ | **B1.** Lote + "Todas las variables" → 4 `<figure>`, figcaptions `Humedad del suelo (%)`, `Humedad relativa (%)`, `Radiación solar (W/m²)`, `Temperatura del aire (°C)`; cada `VisXYContainer` con su propio `VisAxis type="y"`. Con datos ausentes la línea **se corta** (≥ 2 comandos `M` en el `d`), no dibuja un 0. |
| **AC3** | ✓ ↺ | `?plot=1&variable=air_temperature` → exactamente 1 `<figure>`, caption `Temperatura del aire (°C)`. |
| **AC4** | ✓ ↺ | Sin lote → `HistoryAveragesGrid`, un `VisGroupedBar` por variable con el eje X en lotes; nota visible `Sin lecturas en este rango para: Lote Sin Mapear.` para el hueco. **B5:** cada barra tiene tooltip al hover (lote, promedio + unidad, nº de lecturas), verificado sobre las 8 barras con datos reales. |
| **AC5** | ✓ | El `<USelect>` de variable se llena desde `history/variables/` (que ya excluye sensores inactivos) + "Todas las variables"; la query lleva `plot` en la key, así seleccionar lote reconsulta. Las opciones se deduplican por `semantic_key` porque el filtro `?variable=` toma esa clave. **La exclusión de inactivos la garantiza el backend, no el frontend.** |
| **AC6** | ✓ ↺ | **B3.** El lote de la URL se reconcilia contra `useFarmPlotsQuery(farmId)` y las queries esperan a `filtersReady`. Cambio de finca con `?plot=1` puesto → URL `?view=chart` y **0 respuestas 404** (medidas en el `page.on('response')`, antes eran 2); enlace compartido con la finca 2 almacenada y `?plot=1` → también 0. |
| **AC7** | ✓ ↺ | Los 7 params viajan y un filtro limpiado desaparece; además las dos URLs que dejaban la vista atrapada ya se recuperan solas: `?plot=` de otra finca se limpia (**B3**) y `?page=` fuera de rango rebota a una página que existe (**B4**), ambas sin alerta ni "Reintentar" inútil. |
| **AC8** | ✓ | Elegido 3–7 ago en el calendario (máquina en UTC−5) → petición `date_from=2026-08-03T05:00:00.000Z&date_to=2026-08-08T05:00:00.000Z`: día local completo, fin exclusivo. |
| **AC9** | ✓ | 20 filas, columnas `Fecha y hora / Lote / Sensor / Variable / Valor / Unidad`; el orden lo fija el backend (`-recorded_at, -id`) y el cliente **no** reordena. |
| **AC10** | ✓ | Página 2 devuelve filas distintas y `?page=2` en la URL. El no-solape entre páginas depende del desempate `-id` del backend — **QA debe confirmarlo con datos reales de un mismo instante.** |
| **AC11** | ✓ | Sin lote: 6 cabeceras (incluye "Lote"). Con `plot=1`: 5 cabeceras, sin "Lote". |
| **AC12** | ✓ | Series `[]` → `UEmpty` "No hay lecturas para estos filtros."; `count: 0` → mismo `UEmpty` en la tabla y botón Exportar deshabilitado. Nunca una tabla ni un gráfico en blanco. |
| **AC13** | ✓ | Menú Exportar → "Descargar CSV" dispara el evento `download` de Chromium (URL `blob:` + click sintético). `suggestedFilename()` = `historial-sensores-finca-el-tesoro-20260802_20260806.csv`. La petición no lleva `page`, así que trae todo el set filtrado. |
| **AC14** | ✓ | Mismo flujo a `.../export/json/`, nombre `...json`, mismos query params y por tanto mismo orden que el CSV. **Que las filas coincidan una a una es responsabilidad del backend.** |
| **AC16** | ✓ | 400 `export_too_large` mockeado → `role="alert"` **inline** junto al botón: *"El rango seleccionado supera el máximo exportable: 68.320 filas frente a un límite de 50.000. Reduce el rango o filtra por lote."* + toast. No se descarga ningún archivo. |
| **AC22** | ✓ | Sidebar → link "Historial" (`i-lucide-history`) a `localePath('/dashboard/history')`; navega y abre la página. |
| **AC23** | ✓ | `/en/dashboard/history`: `<title>` "Sensor history", pestañas "Charts"/"Table", filtros, cabeceras, exportación, vacíos y errores en inglés. Fechas/números por `Intl` con `locale.value` (`22/8/26, 21:59` vs `8/22/26, 9:59 PM`; `68.320` vs `68,320`). Los nombres de variable y lote vienen de la API y siguen en español — es dato, no UI. |
| **AC24** | ✓ | 500 mockeado → `role="alert"` con texto "No se pudo cargar el historial." + botón "Reintentar" **dentro** de la alerta; al restablecer la API y pulsarlo, la tabla vuelve con 20 filas sin recargar. |
| **AC-A11Y-1** | ✓ | Axe sin violaciones serias/críticas (ni moderadas) en `/dashboard/history?view=chart`, `?view=table`, `?view=chart&plot=1`, `/en/...?view=chart`, `/en/...?view=table`. **Dos salvedades honestas abajo.** |
| **AC-A11Y-2** | ✓ | Cada gráfico: `<div aria-hidden="true">` sobre el SVG, `<figcaption>` con nombre + unidad y `<p class="sr-only">` con el resumen. Ej.: *"Temperatura del aire en °C: 136 lecturas entre 21/8/26, 6:22 y 22/8/26, 21:22. Mínimo 16, máximo 23,98, promedio 20,57."* (líneas) y *"Promedio de Humedad del suelo por lote, en %. Lote La Colina: 33; Lote El Abrevadero: 34."* (barras). |
| **AC-A11Y-3** | ✓ | Párrafo **visible** por grilla: "La vista de Tabla muestra estos mismos datos en forma de texto." |
| **AC-A11Y-4** | ✓ | `<caption>` real (clase `sr-only` del tema de `UTable`): "45 lecturas de Finca El Tesoro, de la más reciente a la más antigua."; `UTable` emite `<th scope="col">` nativos. |
| **AC-A11Y-5** | ✓ | `UPagination` renderiza `<nav aria-label="Paginación de las lecturas">`. Tras pulsar "Página 2" el `document.activeElement` sigue siendo ese botón. |
| **AC-A11Y-6** | ✓ | `<p aria-live="polite" class="sr-only">` anuncia "45 lecturas. Página 1 de 3." / "4 gráficos."; queda vacío mientras hay `isPending`, así solo se lee el conteo definitivo. Ningún filtro mueve el foco. |
| **AC-A11Y-7** | ✓ ↺ | **B2.** `ariaSnapshot` de la barra: `combobox "Lote"`, `combobox "Variable ambiental"`, `combobox "Rango de fechas"` y, en rango personalizado, `textbox "Desde"` + `textbox "Hasta"` (dos `<input type="date">` nativos que el `<label for>` sí apunta) más el botón "Elegir en el calendario". Cero `role="spinbutton"` y cero inglés en la barra. Anillo de foco: los rings de Nuxt UI, intactos. |
| **AC-A11Y-8** | ✓ | Foco en la pestaña "Gráficos" + `ArrowRight` → activa "Tabla" y actualiza la URL. Tab al panel: `:focus-visible` activo con `box-shadow … oklch(0.792 0.209 151.711) 0 0 0 4px` (ring primario con offset), igual que el dashboard index. |
| **AC-A11Y-9** | ✓ ↺ | `<UPopover modal>`: al abrir, el `activeElement` queda dentro del popover; `Escape` lo cierra y el foco vuelve al disparador. Los dos campos de fecha tecleables (**B2**) hacen que el calendario nunca sea el único camino — y ahora también para quien no ve la pantalla: se llegó a ellos y se cambió el rango **solo con el teclado**. |
| **AC-A11Y-10** | ✓ | Errores de carga, aviso de rango inválido y tope de exportación van en `role="alert"` con **texto** (el icono es `aria-hidden`). El aviso de exportación es inline y persistente, además del toast. |
| **AC-A11Y-11** | ✓ | Medido con `getBoundingClientRect`: los 7 botones de paginación son 32×32 px; "Exportar" 103×32 px. |
| **AC-A11Y-12** | ✓ | Ningún gráfico dibuja dos series en los mismos ejes; cada uno lleva título + unidad en su `figcaption` y su propia etiqueta de eje Y. La paleta se validó con el script de la skill `dataviz` (banda de luminosidad, croma, separación CVD y normal entre slots adyacentes, contraste) — PASS en claro y oscuro. |

**Salvedades de AC-A11Y-1 (reproducibles, no introducidas por esta rebanada):**

1. **Con el popover del calendario abierto**, axe reporta `aria-hidden-focus` (serio): reka-ui marca
   el resto de la página con `aria-hidden` pero **sin `inert`**. Es comportamiento de la librería en
   cualquier overlay modal: el mismo escaneo sobre el `/dashboard` ya existente con el desplegable
   de fincas abierto da `aria-hidden-focus` × 2. La alternativa era quitar `modal`, lo que rompe la
   contención de foco que exige AC-A11Y-9. Se eligió cumplir AC-A11Y-9. **Escanear la página en sus
   dos vistas, sin overlays abiertos** (que es lo que pide el AC).
2. **En modo claro** aparecen 3 `color-contrast` serios, los mismos que ya tiene el dashboard index:
   iniciales del avatar del sidebar (`#62748e` sobre `#f1f5f9`, 4.34:1), la pestaña activa (blanco
   sobre el primario `#00c950`, 2.21:1 — **el mismo defecto ya documentado en `a11y.spec.ts` como
   `LOGIN_SUBMIT_KNOWN_CONTRAST`**) y la pestaña inactiva (4.34:1). Son del tema de Nuxt UI, no de
   esta feature, y el layout del dashboard fuerza modo oscuro, donde el escaneo sale limpio.

AC1, AC15, AC17–AC21 son del backend; QA firma la lista completa.

## Gotchas

- **`rangeAnchor`.** "Ahora" se ancla en un `shallowRef(Date.now())` dentro de `useHistoryFilters`
  y solo se mueve al cambiar el rango. Si `date_to` se calculara con `Date.now()` dentro del
  computed, cada re-render re-clavearía las query keys y Vue Query refetchearía sin fin.
- **Días locales → UTC.** `resolveRange` usa `new Date(y, m-1, d)` (local) para el inicio y
  `+1 día` para el fin exclusivo. `new Date('2026-08-22')` habría parseado UTC y corrido la ventana
  5 horas en Bogotá.
- **`page` = ausencia.** La página 1 se representa quitando `?page` de la URL. Cualquier cambio de
  filtro borra `page`; cambiar de vista **no** (el conmutador es ortogonal).
- **`page` acotado en cliente, con `{ immediate: true }`.** El acotado corre también en el primer
  render (un enlace compartido llega ya fuera de rango) y cubre los dos caminos: con `count`
  conocido baja a la última página; ante el 404 de DRF —que no trae `count`— vuelve a la página 1.
  Mientras rebota se ve el esqueleto, no la alerta, y la región viva calla.
- **El `plot` de la URL se reconcilia contra los lotes de la finca.** `plotId` es `null` mientras la
  lista no confirme el id, el param huérfano se borra con `replace`, y `filtersReady` mantiene las
  cuatro queries en espera hasta entonces: un id de otra finca es 404 en todos los endpoints.
- **Unovis y los huecos.** El acceso `y` debe emitir `NaN`/`undefined`, nunca `null`:
  `isFinite(null)` es `true` y la librería lo pinta como un 0 con la línea entera.
- **Dos tooltips distintos, a propósito.** Las líneas usan `VisCrosshair` + `VisTooltip` (eje x
  continuo: engancha la x más cercana); las barras usan `VisTooltip` con `triggers` sobre
  `GroupedBar.selectors.bar`, porque su eje x es una lista de lotes y el crosshair señalaría la
  barra de al lado. El contenido del de barras se arma como DOM con `textContent` (el nombre del
  lote es texto libre del agricultor).
- **`keepPreviousData`** en la query de readings: al paginar la tabla no se vacía, solo se atenúa
  (`opacity-60` con `aria-busy`). Primer uso en el repo.
- **`:unmount-on-hide="false"` en los `UTabs`**: los dos paneles quedan montados. El panel oculto
  lleva `hidden`, pero un `getByText(...)` global cuenta **las dos** apariciones del estado vacío —
  hay que acotar el locator al panel visible.
- **`getByRole('row')` devuelve 22, no 21**, en una página llena: `UTable` inserta una `<tr>` vacía
  de separador entre `thead` y `tbody`. Usar `page.locator('tbody tr')` para contar 20 filas.
- **Nombres accesibles de la paginación y del calendario**: reka-ui los cablea en inglés
  ("Page 2", "Next Page", "Event Date"). Se traducen con los slots `#item/#first/#prev/#next/#last`
  de `UPagination` y con `:calendar-label` en `UCalendar`. Si alguien quita esos slots, vuelve el
  inglés.
- **`fetcher.getBlob`**: con `responseType: 'blob'` ofetch entrega el **cuerpo de error también
  como Blob**; `parseExportError` hace `JSON.parse(await blob.text())`.
- **Hydration mismatch en consola** en cualquier página del dashboard (viene del `UDropdownMenu`
  del sidebar, layer `dashboard`): preexistente, no introducido aquí.
- **Restart obligatorio del dev server** tras traer esta rama: la layer `sensors` añade
  `app/composables` y `app/utils` nuevos e invalida el grafo de módulos.

## Decisions

- **Layer `sensors` nueva**, no páginas en `dashboard` (ADR 0001 §3). Borde sancionado
  `sensors → farm` (auto-imports `useSelectedFarm`/`useFarmPlotsQuery` + tipo `Plot`), registrado en
  `frontend/CLAUDE.md` y en `docs/ARCHITECTURE.md`. `dashboard` **no** depende de `sensors`: el link
  de nav es un `localePath()`.
- **`@internationalized/date` añadido como dependencia directa** (`^3.12.3`, ya presente y deduped
  vía `@nuxt/ui`). `UCalendar`/`UInputDate` trabajan con `DateValue`, y depender del hoisting de una
  dependencia transitiva es frágil. Es la instrucción de la propia doc de Nuxt UI.
- **`shallowRef`, no `ref`, para el `DateRange` del picker**: `ref` desenvuelve en profundidad y
  convierte las instancias `CalendarDate` en objetos mapeados que los props del calendario ya no
  aceptan (falla `vue-tsc`, no solo estilo).
- **El `<figure>` vive fuera del componente `.client`** para que la alternativa textual exista en
  SSR y durante la carga del gráfico.
- **Sin ordenamiento por columna** (fuera de alcance por spec): un sort de cliente ordenaría solo
  las 20 filas visibles y mentiría sobre el dataset. Queda un comentario en `HistoryTable.vue`.
- **Rango personalizado sin fechas aún elegidas no muestra alerta**: solo se avisa cuando el par
  existe pero es inválido (`invalid`) o supera 90 días (`tooLong`). Un `?range=custom` recién
  seleccionado es el estado normal del picker, no un error.
- **Exportar deshabilitado cuando la vista activa no tiene resultados** (readings en Tabla, nº de
  gráficos en Gráficos).
- **Fuera de alcance**: Vitest (no existe setup en `frontend/`, y el plan §5.4 lo deja como deuda
  reconocida sobre `history-filters`/`history-chart`/`history-export`, que son puros y testeables);
  specs de Playwright (de QA); todo `backend/` y `e2e/`.

## ⚠️ Strings que QA debe poner en `e2e/frontend/helpers.ts` (T / T_EN)

### ADDED

```ts
// T — español (valores exactos que renderiza la app)
navHistory:            'Historial',
historyTitle:          'Historial de sensores',
historySubtitle:       'Revisa cómo evolucionaron las lecturas de tus sensores y descarga los datos.',
historyNoFarm:         'Selecciona una finca para ver su historial.',
historyLoadError:      'No se pudo cargar el historial.',
historyRetry:          'Reintentar',

filtersRegion:         'Filtros del historial',
filterFarm:            'Finca',
filterPlot:            'Lote',
filterAllPlots:        'Todos los lotes',
filterVariable:        'Variable ambiental',
filterAllVariables:    'Todas las variables',
filterRange:           'Rango de fechas',
filtersReset:          'Limpiar filtros',

range24h:              'Últimas 24 horas',
range7d:               'Últimos 7 días',
range30d:              'Últimos 30 días',
rangeCustom:           'Personalizado',
rangeFrom:             'Desde',              // <input type="date">
rangeTo:               'Hasta',              // <input type="date">
rangeCalendar:         'Calendario de rango',
rangePick:             'Elegir en el calendario',   // prefijo estable del disparador del popover
rangeInvalid:          'El rango personalizado no es válido; se muestran los últimos 7 días.',
rangeTooLong:          'El rango no puede superar los 90 días; se muestran los últimos 7 días.',

viewRegion:            'Vista del historial',
viewChart:             'Gráficos',
viewTable:             'Tabla',

chartsRegion:          'Gráficos del historial',
// tooltip de una barra (hover): 3 líneas — lote, valor + unidad, nº de lecturas
barTooltipSamples:     'lecturas',           // singular: 'lectura'
chartsAlternative:     'La vista de Tabla muestra estos mismos datos en forma de texto.',
averagesRegion:        'Promedios por lote',

tableRecordedAt:       'Fecha y hora',
tablePlot:             'Lote',
tableSensor:           'Sensor',
tableVariable:         'Variable',
tableValue:            'Valor',
tableUnit:             'Unidad',
historyEmpty:          'No hay lecturas para estos filtros.',

paginationLabel:       'Paginación de las lecturas',
paginationPage:        'Página',            // nombre accesible completo: `Página 2`
paginationFirst:       'Primera página',
paginationPrev:        'Página anterior',
paginationNext:        'Página siguiente',
paginationLast:        'Última página',

exportLabel:           'Exportar',
exportCsv:             'Descargar CSV',
exportJson:            'Descargar JSON',
exportDoneToast:       'Descarga lista',
exportErrorToast:      'No se pudo exportar',
exportGenericError:    'No se pudo generar el archivo. Inténtalo de nuevo.',
// mensaje del tope: los números se formatean con Intl (es-CO) → 68.320 / 50.000
exportTooLargePrefix:  'El rango seleccionado supera el máximo exportable:',

// datos sembrados que la página muestra (nombres que vienen de la API, no traducidos)
varAirTemperature:     'Temperatura del aire',
varSolarRadiation:     'Radiación solar',
varRelativeHumidity:   'Humedad relativa',
varSoilMoisture:       'Humedad del suelo',
```

```ts
// T_EN — inglés
navHistory:         'History',
historyTitle:       'Sensor history',
historyLoadError:   'The history could not be loaded.',
historyEmpty:       'There are no readings for these filters.',
viewChart:          'Charts',
viewTable:          'Table',
filterPlot:         'Plot',
filterAllPlots:     'All plots',
filterVariable:     'Environmental variable',
filterAllVariables: 'All variables',
filterRange:        'Date range',
range7d:            'Last 7 days',
rangeCustom:        'Custom',
rangeFrom:          'From',
rangeTo:            'To',
exportLabel:        'Export',
exportCsv:          'Download CSV',
exportJson:         'Download JSON',
paginationLabel:    'Readings pagination',
```

### DOM hooks shipped

| Qué | Cómo seleccionarlo |
|---|---|
| Panel de la página | `#dashboard-panel-sensors-history` — `UDashboardPanel` prefija el `id` que se le pasa (verificado en el DOM) |
| Barra de filtros | `getByRole('region', { name: T.filtersRegion })` |
| Lote / Variable / Rango | `getByRole('combobox', { name: T.filterPlot \| T.filterVariable \| T.filterRange })` — luego `getByRole('option', { name })` |
| Disparador del calendario | `getByRole('button', { name: /Elegir en el calendario/ })` (el nombre incluye después el rango elegido) |
| Celdas del calendario | `locator('[data-reka-calendar-cell-trigger]:not([data-outside-view]):not([data-disabled])')` |
| Fechas tecleadas | `getByRole('textbox', { name: T.rangeFrom \| T.rangeTo })` — son `<input type="date">`: `fill('2026-08-03')` o teclear `03/08/2026` tras `focus()`; el cambio se emite al `change` |
| Conmutador de vista | `getByRole('tab', { name: T.viewChart \| T.viewTable })`; región `getByRole('region', { name: T.viewRegion })` |
| Gráficos | `page.locator('figure')` (uno por variable) · `page.locator('figcaption')` = `"<Variable> (<unidad>)"` · resumen `page.locator('figure p.sr-only')` |
| Tooltip de barra | hover sobre `figure svg [class*="-bar"]:not([class*="barGroup"])` **con ancho de barra** (el `<g>` del grupo también coincide con ese selector); el texto sale en `div[class*="tooltip"]` con `opacity: 1`. Es hover de ratón: no hay equivalente de teclado porque el SVG va en un contenedor `aria-hidden` y los números viven en el resumen `sr-only` y en la Tabla |
| Tabla | `page.locator('table')`, `<caption>` en `table caption`, cabeceras `getByRole('columnheader')`, **filas de datos `page.locator('tbody tr')`** (no `getByRole('row')`, ver Gotchas) |
| Paginación | `getByRole('navigation', { name: T.paginationLabel })` → `getByRole('button', { name: 'Página 2' })` |
| Exportar | `getByRole('button', { name: T.exportLabel })` → `getByRole('menuitem', { name: T.exportCsv \| T.exportJson })` |
| Errores / avisos | `getByRole('alert')`; el Retry va **dentro** de la alerta: `getByRole('alert').getByRole('button', { name: T.historyRetry })` |
| Región viva | `page.locator('[aria-live="polite"]')` (texto: "45 lecturas. Página 1 de 3." / "4 gráficos.") |
| Estado vacío | `T.historyEmpty` — acotar al panel visible del tab |

Nombre de archivo esperado en la descarga:
`/^historial-sensores-[a-z0-9-]+-\d{8}_\d{8}\.(csv|json)$/`
(ej. `historial-sensores-finca-el-tesoro-20260802_20260806.csv`; los días son **locales**).

## For next agent (QA)

Flujo exacto a ejercitar (`loginAs` + `gotoHydrated`):

1. Sidebar → **"Historial"** → `/dashboard/history`; la URL se vuelve `?view=chart` sola
   (`router.replace`, sin entrada de historial).
2. Con "Todos los lotes": grilla de **barras** (`figure` por variable) + la nota
   `T.chartsAlternative` + la nota de lotes sin datos. Hover sobre una barra → tooltip con el
   nombre del lote, el promedio con unidad y el nº de lecturas.
3. Elegir **Lote** → grilla de **líneas**, un `figure` por variable del lote; `?plot=<id>` en la URL.
4. Elegir **Variable** → un solo `figure`; `?variable=<semantic_key>`.
5. Pestaña **Tabla** → 20 filas (`tbody tr`), `<caption>` con finca y total, sin la columna "Lote"
   si hay lote elegido. Pulsar **"Página 2"** → `?page=2`, filas distintas, el foco se queda en el
   botón.
6. Rango **"Personalizado"** → aparecen los campos **"Desde"** y **"Hasta"**
   (`getByRole('textbox', { name })`, `<input type="date">`) y el botón del calendario. Elegir dos
   días en el calendario (sincroniza los campos) **y** teclear un par en los campos; comprobar en la
   petición que `date_from`/`date_to` son el día local completo con fin exclusivo.
7. **Exportar → Descargar CSV** con `page.waitForEvent('download')`. Llega por URL `blob:` + click
   sintético; **verificarlo el día uno**. Fallback documentado en el plan §3.3:
   `page.waitForResponse(r => r.url().includes('/history/export/csv/') && r.status() === 200)`.
8. Fallo de red: `page.route('**/sensors/farms/*/history/**', r => r.abort())` → `role="alert"` con
   `T.historyLoadError`; `unroute` y click en **Reintentar dentro de la alerta**.
9. Cambiar de finca desde el sidebar con `?plot=` puesto → el lote se reinicia (URL sin `plot`) y
   **ninguna petición del historial responde 404** (`page.on('response')`).
9b. Enlace compartido con un lote de **otra** finca (`?plot=<id ajeno>`) → la URL se limpia sola, el
   `USelect` muestra "Todos los lotes" y no aparece ninguna alerta.
9c. `?view=table&page=999` → la vista rebota a la página 1 (URL sin `page`), 20 filas, sin alerta y
   con la región viva anunciando "N lecturas. Página 1 de M."; un `?page=2` válido **no** se toca.
10. `/en/dashboard/history` en ambas vistas para AC23.
11. Axe: escanear **sin overlays abiertos**; ver las dos salvedades del AC self-check antes de
    añadir cualquier exclusión (la respuesta correcta a la de modo claro es arreglar el tema, no
    excluir).

Nota operativa: la contraseña del usuario sembrado (`juan.perez@email.com` / `E2eSmoke_2026!`) ya
está puesta y verificada (`/api/accounts/login/` → 200, y login por el formulario real). El
`sensor_variable` con el hueco de 6 h que siembra `seed_sensor_readings` es hoy el de
**`plot=1` + `variable=soil_moisture`**: es la serie con la que comprobar que la línea se corta.

## Proposed improvements

> Tras la revisión: endorso las propuestas 1, 2, 3 y 5 de `review-frontend.md` (el `null` de Unovis,
> la reconciliación de todo id que venga de la URL/`localStorage`, el acotado con `{ immediate: true }`
> y el `ariaSnapshot()` sobre cualquier control envuelto en `UFormField`) — las cuatro salieron
> confirmadas al arreglar B1–B4. Las 1–7 de abajo siguen en pie, con la 1 ampliada.

1. **Regla:** *No pongas un control de Nuxt UI cuya raíz sea un combobox de Reka
   (`USelectMenu`, `UInputMenu`) dentro de un `UFormField` esperando que la etiqueta lo nombre: el
   trigger trae su propio `aria-label="Show popup"` y pisa el `<label for>`. Usa `USelect` o pon un
   `aria-label` explícito, y verifica el nombre accesible con `ariaSnapshot()`. Lo mismo con
   `UInputDate`/`UCalendar`, cuyo `for` apunta a un `<input aria-hidden>`: para una fecha que el
   usuario teclea, un `<UInput type="date">` nativo (con `dark:scheme-dark` para el glifo del
   selector) es un solo control que la etiqueta posee y cuyos segmentos localiza el navegador.*
   **Dónde:** `frontend/CLAUDE.md`, sección "UI components & icons".

2. **Regla:** *reka-ui cablea nombres accesibles en inglés en `UPagination` ("Page 2", "Next Page")
   y `UCalendar` ("Event Date"), y el `locale` de `UApp` no los alcanza. Tradúcelos con los slots
   `#item/#first/#prev/#next/#last` y con `:calendar-label`.*
   **Dónde:** `frontend/CLAUDE.md`, sección "i18n".

3. **Regla:** *Un `ref()` que contenga instancias de clase (`CalendarDate`, objetos de librerías
   externas) debe ser `shallowRef()`: el desenvuelto profundo de `ref` las convierte en objetos
   mapeados estructuralmente y los props tipados de la librería dejan de aceptarlas — falla
   `vue-tsc`, no solo el estilo.*
   **Dónde:** `frontend/CLAUDE.md`, sección "Composables & state".

4. **Regla:** *`UTable` inserta una `<tr>` de separador entre `thead` y `tbody`, así que
   `getByRole('row')` cuenta una fila de más; cuenta filas de datos con `locator('tbody tr')`.
   Con `UTabs :unmount-on-hide="false"` los dos paneles quedan en el DOM: acota los locators al
   panel visible.*
   **Dónde:** `e2e/README.md` (o `frontend/CLAUDE.md` si se prefiere junto a las reglas de UI).

5. **Regla:** *Cualquier overlay modal de reka-ui (`UPopover modal`, `UModal`, `UDropdownMenu`)
   marca el resto de la página con `aria-hidden` sin `inert`, lo que axe reporta como
   `aria-hidden-focus` serio. Escanea con axe **sin overlays abiertos**; no lo trates como
   regresión de la feature ni le añadas exclusiones.*
   **Dónde:** `e2e/README.md`.

6. **Regla:** *Cuando un valor "todos / ninguno" viaje por un `USelect`/`USelectMenu`, usa un
   centinela string (`'all'`) y tradúcelo a `null`/ausente en el handler: Reka rechaza `null` como
   valor de ítem. En la URL y en la API la ausencia de la clave sigue siendo la representación
   canónica — nunca `plot=null`.*
   **Dónde:** `frontend/CLAUDE.md`, sección "UI components & icons".

7. **Regla:** *Toda conversión de un día de calendario elegido por el usuario a un instante para la
   API debe construirse con `new Date(y, m-1, d)` (local) y cerrar el rango en el inicio del día
   siguiente (fin exclusivo). `new Date('YYYY-MM-DD')` parsea en UTC y desplaza la ventana en
   cualquier zona con offset.*
   **Dónde:** `frontend/CLAUDE.md`, sección nueva "Fechas y zonas horarias" (o dentro de "i18n").

8. **Regla:** *Un ✓ de self-check sobre algo que se renderiza —trazo de un gráfico, nombre
   accesible, ausencia de 404— sólo vale con una aserción sobre lo que produjo el navegador (el `d`
   del path, el destino real de `label[for]`, los `status` de `page.on('response')`); leer el código
   fuente no basta, porque el fallo suele vivir en el contrato con la librería, no en el código.*
   **Dónde:** spec del agente `frontend-engineer` (sección "Definition of done" / handoff).

9. **Regla:** *En Unovis, el tooltip de un gráfico **categórico** (`VisGroupedBar`, barras) se cablea
   con `VisTooltip :triggers` sobre el selector del propio elemento
   (`GroupedBar.selectors.bar`), no con `VisCrosshair`, que sólo tiene sentido en un eje x continuo.
   Si el contenido incluye texto que escribió un usuario, devuélvelo como `HTMLElement` con
   `textContent` en vez de una cadena de HTML.*
   **Dónde:** `frontend/CLAUDE.md`, sección nueva "Gráficos (Unovis)" (la que propone la revisión).
