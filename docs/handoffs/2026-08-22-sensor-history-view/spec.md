# Spec — Historial de sensores

Slug: `2026-08-22-sensor-history-view`
Contexto: [`acceptance-criteria.md`](acceptance-criteria.md) · [`contract.md`](contract.md) · [`plan.md`](plan.md)

## Goal

Dar al agrónomo una vista `/dashboard/history` donde pueda **ver cómo evolucionaron** las
lecturas de sus sensores —no solo el estado actual que ya muestra `/dashboard`— filtrando por
**finca, lote y variable ambiental**, alternando entre **gráficos** y **tabla paginada**, y
**extrayendo los datos** en `.csv` y `.json`.

## In scope

- Página `/dashboard/history` (y `/en/dashboard/history`) en una **layer `sensors` nueva**.
- Filtros: finca (de `useSelectedFarm`, sidebar), lote (con "Todos los lotes"), variable
  ambiental (con "Todas las variables"), rango de fechas (presets 24h / 7d / 30d + rango
  personalizado con date-picker). Todo el estado viaja en la URL.
- Tres modos de visualización, derivados de los filtros:
  1. **Solo finca** (sin lote) → promedio de cada variable por cada lote.
  2. **Lote + "Todas las variables"** → grilla con un gráfico lineal por variable.
  3. **Lote + una variable** → un solo gráfico lineal.
- Conmutador **Gráficos / Tabla**, ortogonal a los filtros.
- Tabla paginada de **20 filas por página** con las lecturas históricas.
- Exportación del **set filtrado completo** a `.csv` y `.json`.
- Backend: primera paginación DRF, primer filtrado por query-params, primera exportación en
  streaming del repo. Todos los endpoints acotados por propietario.
- Datos: ampliar `initial_sensors.json` y un comando `seed_sensor_readings` nuevo — hoy
  **nada crea `SensorMeasurement`**, así que sin esto la feature no tiene datos.

## Out of scope

- Ordenar la tabla por columna (sería server-side; en v1 se envía ordenada por
  `recorded_at desc` y las cabeceras **no** son ordenables — un sort de cliente ordenaría
  solo las 20 filas visibles y mentiría sobre el dataset completo).
- Tabla separada de promedios por lote (la tabla de lecturas ya sirve el modo solo-finca).
- Ingesta real de sensores de campo (`x-api-key`) — sigue siendo "Planned" en ARCHITECTURE.
- Tests unitarios / Vitest en `frontend/` (no existe setup; Playwright es la única puerta).
- Targets `make all-test` / `make e2e-test` (decisión explícita del usuario: fuera de alcance).
- Predicciones, alertas, comparación entre fincas.

## UX notes

- **Estado en la URL, no en el componente.** `?plot=&variable=&range=&from=&to=&view=&page=`
  se parsea con el mismo patrón que `layers/dashboard/app/utils/view-mode.ts` +
  `useDashboardViewMode.ts`: `router.replace` para la resolución inicial, `router.push` en
  cambios del usuario, `localStorage` leído solo en `onMounted`. **Solo `view` se persiste**
  en `localStorage`; un `plot`/`variable` guardado podría pertenecer a una finca ya no seleccionada.
- **Cambiar de finca resetea el lote.** Un id de lote de la finca A da 404 bajo la finca B.
- **La finca no se duplica en la barra de filtros** — el selector ya vive en el sidebar
  (`FarmsMenu`); la barra solo muestra su nombre en texto.
- **Tres estados en cada superficie**: `isPending` → `USkeleton` con `aria-busy="true"`;
  error → `role="alert"` con texto + Retry etiquetado (nunca color solo); si no, contenido.
- **Los gráficos son decorativos para el lector de pantalla**: SVG en `aria-hidden`, dentro de
  `<figure>` con `<figcaption>` y un resumen numérico `sr-only`; la vista de tabla es la
  alternativa textual completa y se anuncia con una nota visible.
- **Vacíos honestos**: 0 puntos → `UEmpty`, nunca un gráfico en blanco. Huecos en la serie →
  la línea se corta, nunca se interpola una recta sobre datos ausentes.
- Fechas y números siempre por `Intl` con `locale.value`.

## Resolved decisions

1. **Fuente de datos = sensores de campo** (`SensorMeasurement` → `FieldSensorVariable` →
   `FieldSensor` → `Plot`). Es la única cadena que llega al lote; `WeatherMeasurement` cuelga
   de la finca y no puede responder "promedio por lote". Implica seeder + fixtures.
2. **Rango de fechas** = presets 24h / 7d / 30d **más** un date-picker de rango personalizado
   (`UCalendar range` en un `UPopover`, más `UInputDate range` para entrada tecleada).
   Default: últimos 7 días. Tope duro: 90 días → 400.
3. **Export = todo el set filtrado**, generado en el servidor, en streaming, con tope de
   **50 000 filas**. Al excederlo se devuelve **400**, nunca un archivo truncado en silencio.
4. **Gráficos = uno por variable, en grilla**, cada uno con su eje Y y su unidad. Sin
   normalizar a 0–100: un eje sin unidad real se presta a malinterpretación.
5. **Modo solo-finca usa barras agrupadas** (`VisGroupedBar`), no líneas: el eje X son lotes,
   una categoría — una línea sobre tres lotes sugeriría una continuidad que no existe.
6. **Fixtures: solo los lotes de `juan.perez`** (lotes 1–4). Los lotes 5–28 quedan con
   cobertura desigual a propósito: preserva el caso límite "finca con una sola variable
   disponible" y evita triplicar el volumen de la semilla para datos que nadie ve.
7. **`make all-test` / `make e2e-test` fuera de alcance.** Las suites se corren a mano:
   `make test` desde `backend/`, `npx playwright test` desde `e2e/`.
8. **Identidad de variable en el cable = `variable_id` (pk)**, con `semantic_key` al lado como
   clave de presentación. `semantic_key` **no es único** en `EnvironmentalVariable`, así que no
   puede identificar una serie. El filtro `?variable=` sí toma un `semantic_key` (mantiene el
   precedente de `FarmWeatherAPIView`).
9. **`other` (presión barométrica) SÍ aparece en el historial**, a diferencia del endpoint de
   clima que lo excluye. El historial muestra lo que los sensores realmente miden. Es la única
   divergencia deliberada entre ambos endpoints.
10. **Nueva layer `sensors`** (no páginas en `dashboard`), per ADR 0001 §3 y ARCHITECTURE:71.
    Nuevo borde sancionado **`sensors → farm`**, idéntico en forma y dirección al `dashboard → farm`
    existente. `dashboard` **no** gana dependencia sobre `sensors` (el link de nav es solo un string).

## Docs que deben actualizarse con este cambio

- `docs/ARCHITECTURE.md:122` contradice a `:71` y al ADR 0001 §3 sobre dónde viven las páginas
  de historial — corregir la línea 122.
- `frontend/CLAUDE.md` y `docs/ARCHITECTURE.md`: registrar el borde sancionado `sensors → farm`.
- `frontend/layers/dashboard/app/layouts/dashboard.vue`: borrar el comentario
  *"History/Predictions stay hidden until those pages exist"*, ya falso.
- `docs/ARCHITECTURE.md`: mover "Dashboard pages for history" de "Planned" a "Working today"
  y agregar `sensors` a la lista de layers.
