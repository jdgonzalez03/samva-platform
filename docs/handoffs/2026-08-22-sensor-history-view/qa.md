# qa handoff — Historial de sensores

Slug: `2026-08-22-sensor-history-view` · Contexto: [`contract.md`](contract.md) ·
[`acceptance-criteria.md`](acceptance-criteria.md) · [`frontend.md`](frontend.md)

**Summary.** Red de regresión **mínima** (5 tests) sobre `/dashboard/history`, por decisión
explícita del usuario, que ya verificó la feature a mano en su navegador. Cubre los tres modos de
visualización, la paginación de la tabla, la descarga CSV, el reinicio del lote al cambiar de finca
y la persistencia de los filtros en la URL. No se escribió suite exhaustiva: el resto de los AC
queda **explícitamente sin verificar por e2e** (ver checklist y `## Deferred coverage`).

## Files changed

**Nuevo**

- `e2e/frontend/sensors.spec.ts` — los cinco tests (`describe`: *Historial de sensores*).

**Modificados**

- `e2e/frontend/helpers.ts` — nuevas claves en `T` (todas usadas por algún spec):
  `navHistory`, `filterPlot`, `filterVariable`, `filterRange`, `filtersReset`, `range30d`,
  `chartsRegion`, `averagesRegion`, `paginationLabel`, `paginationPage`, `exportLabel`,
  `exportCsv`, `plotFirst`, `varAirTemperature`. Además `selectFarm()` se **movió** aquí desde
  `farm.spec.ts` (dos specs lo necesitan; una sola definición).
- `e2e/frontend/farm.spec.ts` — importa `selectFarm` de `helpers` en vez de definirlo (sin cambios
  de comportamiento).
- `e2e/frontend/error.spec.ts` — **arreglo obligado por la feature**: usaba `/dashboard/history`
  como "ruta inexistente"; ahora esa ruta existe y redirigía al login, así que los dos tests del
  404 fallaban. Pasan a `/pagina-inexistente` (const `MISSING_PATH`, fuera de `/dashboard`).
- `e2e/frontend/auth.spec.ts` — **arreglo obligado por la feature**: aseveraba que el sidebar
  *no* tenía enlace de Historial/Predicciones. Ahora aseveraba lo contrario de la realidad; se
  cambia por "el enlace **Historial** apunta a `/dashboard/history`" + predicciones sigue ausente.

Ningún archivo de `frontend/` ni `backend/` fue tocado. Ningún comando `git` ejecutado.

## Covered flows

1. **Tres modos de gráfico en un solo recorrido** — abrir `/dashboard/history`, elegir
   *Lote La Colina* → 4 `<figure>` en la región *Gráficos del historial* (una por variable, con su
   `<figcaption>`); elegir *Temperatura del aire* → queda 1; *Limpiar filtros* → aparece la región
   *Promedios por lote* con 4 `<figure>` de barras y su resumen `sr-only` nombrando el lote.
   Nunca se asevera geometría SVG ni el atributo `d`.
2. **Tabla paginada** — `?view=table` → exactamente 20 filas (`tbody tr`); clic en *Página 2* →
   `?page=2`, 20 filas nuevas y **cero solapamiento** con la página 1.
3. **Exportación CSV** — filtrar por lote, *Exportar → Descargar CSV*: la petición lleva el mismo
   `plot` y **no** lleva `page`; el evento `download` de Chromium entrega un archivo cuyo nombre
   casa `historial-sensores-<finca>-<YYYYMMDD>_<YYYYMMDD>.csv`, con la cabecera del contrato y
   muchas más de 20 filas.
4. **Cambio de finca** — con un lote elegido, cambiar a *Finca San Vicente* desde el sidebar: el
   `plot` desaparece de la URL, se pintan los promedios de la nueva finca, no hay `role="alert"`
   y **ninguna respuesta `/api/` es 404** (medido con `page.on('response')`).
5. **Filtros en la URL** — lote + variable + rango 30 d viajan en la URL; tras `reload()` la URL es
   idéntica y los tres `combobox` y el gráfico único se reproducen igual.

## AC checklist

Solo los ocho AC que estos cinco tests tocan se marcan; el resto se lista abajo como **no
verificado por e2e**.

| AC | Estado | Test que lo cubre |
|---|---|---|
| **AC2** | ✓ | Test 1 — lote + "Todas las variables" → 4 figuras, cada una con `figcaption` `"<Variable> (<unidad>)"`. |
| **AC3** | ✓ | Test 1 — una sola variable → exactamente 1 figura, la de esa variable. |
| **AC4** | ✓ *(parcial)* | Test 1 — sin lote → región *Promedios por lote*, 4 figuras y el resumen textual con el promedio **por lote**. Que las barras dibujadas correspondan a esos números no se asevera (regla: nada de geometría SVG). |
| **AC6** | ✓ | Test 4 — cambio de finca: URL sin `plot`, datos de la nueva finca, **0 respuestas 404**. |
| **AC7** | ✓ *(parcial)* | Test 5 — `plot`, `variable`, `range` y `view` viajan y sobreviven a la recarga; Test 2 añade `page`. **`from`/`to` (rango personalizado) NO se ejercitan** — fuera del alcance acordado. |
| **AC9** | ✓ *(parcial)* | Test 2 — máximo 20 filas por página. **Las columnas y el orden descendente NO se aseveran**; el orden lo garantizan los tests del backend. |
| **AC10** | ✓ | Test 2 — página 2 sin ninguna fila repetida respecto de la 1 (la invariante que protege el desempate `-id`). |
| **AC13** | ✓ | Test 3 — nombre con finca + rango, cabecera del CSV, petición con los filtros y sin `page`, y muchas más filas que las 20 visibles. |

**No verificados por e2e** — *alcance reducido por decisión del usuario; verificados manualmente
por él en su navegador*: **AC1, AC5, AC8, AC11, AC12, AC14, AC15, AC16, AC17, AC18, AC19, AC20,
AC21, AC22, AC23, AC24** y **AC-A11Y-1 … AC-A11Y-12**.

Matices honestos sobre esa lista:

- **AC17–AC21** (ownership 404, 401, 400 de rango, coste de queries, sensores inactivos) son de
  API pura y los cubre `backend/sensors/tests.py`; aquí no se añadió nada en `e2e/backend/`.
- **AC22** queda cubierto **de refilón** por el arreglo de `auth.spec.ts` (el enlace *Historial*
  del sidebar apunta a `/dashboard/history`), no por un test propio.
- **AC-A11Y-1 … 12**: no se tocó `a11y.spec.ts` por instrucción expresa. **No hay backstop
  automatizado de axe para esta página en el repo**; el único registro de que se cumplen es el
  self-check del agente de frontend en `frontend.md`.

## Suite result

Salida real de `cd e2e && npx playwright test` (última corrida completa):

```
  ✓  47 [frontend] › frontend/sensors.spec.ts:36:7 › Historial de sensores › la vista abre con un gráfico por cada variable del lote seleccionado (2.7s)
  ✓  48 [frontend] › frontend/sensors.spec.ts:77:7 › Historial de sensores › la tabla muestra 20 filas y la página siguiente trae lecturas distintas (2.0s)
  ✓  49 [frontend] › frontend/sensors.spec.ts:109:7 › Historial de sensores › exportar a CSV descarga un archivo con las lecturas filtradas (2.4s)
  ✓  50 [frontend] › frontend/sensors.spec.ts:149:7 › Historial de sensores › cambiar de finca reinicia el lote sin provocar errores (2.5s)
  ✓  51 [frontend] › frontend/sensors.spec.ts:177:7 › Historial de sensores › los filtros viajan en la URL y sobreviven a una recarga (3.7s)

  51 passed (1.1m)
```

51 = 46 del baseline + 5 nuevos, con los 3 que la feature había dejado obsoletos (`error.spec.ts`
×2, `auth.spec.ts` ×1) arreglados, no silenciados. Además `npx tsc --noEmit` limpio y
`npx playwright test frontend/sensors.spec.ts --repeat-each=3` → **15 passed** (sin flakes; ningún
`skip` ni timeout inflado).

## Deferred coverage

Lo que queda sin red de regresión y el riesgo concreto de cada hueco:

- **Rango personalizado y zonas horarias (AC8)** — el bug clásico (día local → UTC, fin exclusivo)
  no tiene test. Riesgo: una refactorización de `resolveRange` puede correr la ventana 5 h en
  Bogotá y nadie se entera; el usuario vería datos de otro día.
- **Estado vacío (AC12)** y **columna "Lote" condicional (AC11)** — riesgo: una tabla o un gráfico
  en blanco en vez de un mensaje, o una columna redundante que vuelve.
- **Exportación JSON (AC14)**, **BOM/acentos en Excel (AC15)** y **tope de 50 000 filas (AC16)** —
  riesgo alto en el tope: un cambio en `getBlob` o en `parseExportError` haría que el 400 se lea
  como error genérico y el usuario perdería el mensaje accionable con `count`/`limit`.
- **Errores y "Reintentar" (AC24)** — el `role="alert"` y su botón interior no tienen test; una
  regresión dejaría la página muerta sin salida.
- **i18n de la página (AC23)** — `/en/dashboard/history` no se visita en ningún spec; un texto sin
  traducir pasa sin ruido.
- **Accesibilidad (AC-A11Y-1 … 12)** — sin escaneo axe ni aserciones de teclado/foco para esta
  página. Riesgo principal: los nombres accesibles que reka-ui cablea en inglés vuelven en silencio
  si alguien quita los slots de `UPagination` o el `:calendar-label`, y el `<caption>` / la región
  `aria-live` pueden desaparecer sin que nada falle.
- **Ordenamiento y columnas de la tabla (AC9)** — solo se cuenta el número de filas.

## For reviewer

- **Dos specs preexistentes tuvieron que cambiar** y no es cosmético: `error.spec.ts` usaba
  `/dashboard/history` como ruta 404 y `auth.spec.ts` aseveraba la **ausencia** del enlace
  "Historial". La feature convirtió ambas aserciones en falsas; se corrigieron en vez de borrarse.
- `selectFarm()` vive ahora en `e2e/frontend/helpers.ts` (antes era local de `farm.spec.ts`).
  Mantiene el `Escape` tras el dropdown, obligatorio porque el overlay `aria-hide` el resto de la
  página.
- El test de la tabla usa `expect.poll` sobre el **texto de las filas**, no sobre el conteo:
  `keepPreviousData` deja las 20 filas viejas en pantalla mientras carga la página 2, así que un
  `toHaveCount(20)` pasaría contra datos obsoletos y el test no probaría nada.
- El botón de paginación se localiza con `exact: true`: `"Página 2"` es subcadena de
  `"Página 265"` (la última página del set sembrado) y sin `exact` el locator es ambiguo.
- El test de exportación **lee el archivo descargado** (`download.path()` + `readFileSync`) para
  comprobar cabecera y número de filas. El camino `blob:` + click sintético sí dispara el evento
  `download` en Chromium; no hizo falta el fallback de `waitForResponse`.
- Datos sembrados de los que dependen las cifras: `Finca El Tesoro` → lotes *La Colina*,
  *El Abrevadero*, *Sin Mapear*; 4 variables activas por lote mapeado (de ahí `VARIABLE_COUNT = 4`)
  y > 5 000 lecturas en el rango por defecto de 7 días. Si el seeder cambia de variables, el único
  punto a tocar es esa constante.

## Proposed improvements

1. **Regla:** *Un spec nunca debe aseverar la **ausencia** de una funcionalidad planeada ni usar la
   ruta de una página futura como "ruta que no existe": ambas aserciones se vuelven falsas el día
   que la feature aterriza y el fallo aparece en un spec ajeno. Ancla los tests de 404 en un path
   que ninguna feature vaya a reclamar (`/pagina-inexistente`) y asevera lo que **sí** existe.*
   **Dónde:** `e2e/README.md`.

2. **Regla:** *Con una tabla que use `keepPreviousData`, cambiar de página no vacía el DOM: un
   `toHaveCount(n)` pasa contra las filas viejas. Espera el cambio real con `expect.poll` sobre el
   texto de las filas antes de comparar páginas.*
   **Dónde:** `e2e/README.md`.

3. **Regla:** *`getByRole(..., { name })` casa por subcadena: en controles numerados
   (`"Página 2"` vs `"Página 265"`) usa siempre `exact: true`.*
   **Dónde:** `e2e/README.md`.

> Endorso además la propuesta 4 de `frontend.md` (contar filas de datos con `locator('tbody tr')`
> porque `UTable` inserta una `<tr>` separadora, y acotar los locators al panel visible con
> `UTabs :unmount-on-hide="false"`): confirmada al escribir el test 2 — `getByRole('row')` daba 22.
> No la repito como propuesta propia para no duplicar la regla.
