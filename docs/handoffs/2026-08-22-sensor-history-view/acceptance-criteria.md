# Acceptance criteria — Historial de sensores

Slug: `2026-08-22-sensor-history-view`

Esta es la **fuente de verdad del comportamiento** de esta feature. Cada rol verifica su trabajo
contra ella: los ingenieros auto-verifican los criterios que su rebanada posee, los reviewers
comprueban que esa auto-verificación es honesta, y QA firma la lista completa de punta a punta
en `qa.md`.

La feature está **completa solo cuando todos los criterios están ✓**.

Contexto: [`spec.md`](spec.md) · [`contract.md`](contract.md) · [`plan.md`](plan.md)

---

## Functional

### Datos y semilla

- [ ] **AC1** — Given las fixtures cargadas y `seed_sensor_readings` ejecutado, When se consulta
  el historial de cualquier lote de `Finca El Tesoro` o `Finca San Vicente`, Then hay lecturas
  para las cuatro variables reales (temperatura del aire, radiación solar, humedad relativa,
  humedad del suelo) cubriendo al menos 30 días, y `Lote Sin Mapear` (sin sensores) devuelve
  un historial vacío sin error.

### Gráficos

- [ ] **AC2** — Given una finca y un lote seleccionados con la variable en "Todas las variables",
  When el usuario está en la vista de Gráficos, Then se muestra una grilla con **un gráfico
  lineal por cada variable que ese lote mide**, cada uno rotulado con su nombre y su unidad y
  con su propio eje Y.
- [ ] **AC3** — Given un lote y **una sola** variable seleccionada, When el usuario está en la
  vista de Gráficos, Then se muestra exactamente un gráfico lineal, el de esa variable.
- [ ] **AC4** — Given una finca seleccionada y **ningún** lote ("Todos los lotes"), When el
  usuario está en la vista de Gráficos, Then se muestra, por cada variable, un gráfico de barras
  agrupadas con el **promedio de esa variable en cada lote** de la finca sobre el rango elegido.

### Filtros

- [ ] **AC5** — Given una finca seleccionada, When se abre el selector de variable ambiental,
  Then solo lista las variables que los sensores **activos** de esa finca (o del lote, si hay
  uno seleccionado) realmente miden, más la opción "Todas las variables".
- [ ] **AC6** — Given un lote seleccionado, When se cambia de finca desde el sidebar, Then el
  lote seleccionado se reinicia a "Todos los lotes" y la vista se recarga con los datos de la
  nueva finca, sin errores 404.
- [ ] **AC7** — Given cualquier combinación de filtros, When el usuario la aplica, Then el
  estado completo (`plot`, `variable`, `range`, `from`, `to`, `view`, `page`) viaja en la URL,
  y recargar la página o compartir el enlace reproduce exactamente la misma vista.
- [ ] **AC8** — Given el rango en "Personalizado", When el usuario elige fechas de inicio y fin
  con el date-picker, Then los datos mostrados corresponden a ese rango en **hora local**
  (el día de calendario elegido, no un rango desplazado por la zona horaria).

### Tabla

- [ ] **AC9** — Given cualquier filtro con resultados, When el usuario cambia al modo Tabla,
  Then se muestra una tabla con **máximo 20 filas**, con las columnas fecha/hora, lote, sensor,
  variable, valor y unidad, ordenada de la lectura más reciente a la más antigua.
- [ ] **AC10** — Given una tabla con más de 20 resultados, When el usuario avanza a la página
  siguiente, Then se muestran lecturas **distintas** a las de la página anterior — ninguna fila
  se repite ni desaparece entre páginas, incluso cuando varias lecturas comparten el mismo
  instante.
- [ ] **AC11** — Given un lote seleccionado, When se ve la tabla, Then la columna "Lote" se
  oculta (es redundante); Given "Todos los lotes", Then la columna "Lote" se muestra.
- [ ] **AC12** — Given un rango sin lecturas, When el usuario ve la tabla o los gráficos, Then
  se muestra un estado vacío explícito con texto, no una tabla en blanco ni un gráfico vacío.

### Exportación

- [ ] **AC13** — Given cualquier combinación de filtros con resultados, When el usuario elige
  "Descargar CSV", Then se descarga un archivo `.csv` cuyo nombre incluye la finca y el rango,
  con una fila de cabecera y **todas las lecturas que cumplen los filtros** — no solo las 20
  visibles.
- [ ] **AC14** — Given las mismas condiciones, When el usuario elige "Descargar JSON", Then se
  descarga un archivo `.json` que es un array de objetos con las mismas filas y el mismo orden
  que el CSV.
- [ ] **AC15** — Given un CSV exportado con variables acentuadas (`Radiación solar`, `°C`),
  When se abre en Excel, Then los acentos y símbolos se muestran correctamente.
- [ ] **AC16** — Given un rango cuyo resultado supera las 50 000 filas, When el usuario intenta
  exportar, Then **no** se descarga un archivo truncado: se muestra un mensaje de error legible
  que nombra el número de filas y el límite, y sugiere reducir el rango o filtrar por lote.

### API

- [ ] **AC17** — Given un usuario autenticado, When pide el historial de una finca que **no le
  pertenece**, Then recibe **404** con el cuerpo genérico `{"detail": "Not found."}` — nunca
  403, y sin filtrar ningún dato de esa finca. Lo mismo para un lote que posee pero que
  pertenece a otra finca que la de la ruta.
- [ ] **AC18** — Given una petición sin token, When llega a cualquier endpoint del historial,
  Then recibe **401**.
- [ ] **AC19** — Given un rango inválido (`date_from > date_to`, fecha ilegible, o span mayor
  a 90 días), When se pide cualquier endpoint del historial, Then recibe **400** nombrando el
  campo problemático.
- [ ] **AC20** — Given cualquier endpoint de lectura del historial, When se mide su coste,
  Then el número de queries SQL es **constante**: no crece con el número de lotes, de variables,
  ni con el tamaño de página.
- [ ] **AC21** — Given lecturas de un sensor **inactivo** o con `value` nulo, When se pide
  cualquier endpoint del historial, Then esas lecturas **no aparecen** en tablas, series,
  promedios ni exportaciones.

### Navegación e i18n

- [ ] **AC22** — Given un usuario autenticado en el dashboard, When mira el menú lateral, Then
  hay una entrada "Historial" que lleva a `/dashboard/history`.
- [ ] **AC23** — Given la página del historial, When el usuario cambia el idioma a inglés,
  Then toda la interfaz (títulos, filtros, cabeceras de tabla, botones de exportación, estados
  vacíos y de error) se muestra en inglés en `/en/dashboard/history`, y las fechas y números se
  formatean según el locale activo.
- [ ] **AC24** — Given una petición del historial que falla, When el usuario ve la página, Then
  aparece un mensaje de error **en texto** (no solo color ni ícono) junto a un control
  "Reintentar" etiquetado, y pulsarlo recupera la vista sin recargar la página.

---

## Accessibility

WCAG 2.2 AA. Verificado con `@axe-core/playwright` más aserciones explícitas de teclado y foco.
Provienen de la fase de descubrimiento de UX y de las decisiones resueltas en [`spec.md`](spec.md).

- [ ] **AC-A11Y-1** — Given la página del historial en cualquiera de sus dos vistas, When
  `@axe-core/playwright` corre con `['wcag2a','wcag2aa','wcag21aa','wcag22aa']` sobre
  `/dashboard/history` y `/en/dashboard/history`, Then hay **cero** violaciones serias o
  críticas, sin añadir exclusiones nuevas al spec. *(backstop)*
- [ ] **AC-A11Y-2** — Given un gráfico renderizado, When lo recorre un lector de pantalla, Then
  el SVG está marcado `aria-hidden`, y en su lugar se anuncia un `<figcaption>` con el nombre y
  la unidad de la variable más un resumen numérico (número de lecturas, rango de fechas, mínimo,
  máximo y promedio). *(1.1.1)*
- [ ] **AC-A11Y-3** — Given la vista de Gráficos, When se recorre la página, Then existe una
  nota **visible** que indica que la vista de Tabla ofrece los mismos datos en forma textual.
  *(1.1.1)*
- [ ] **AC-A11Y-4** — Given la tabla de lecturas, When la recorre un lector de pantalla, Then
  tiene un `<caption>` real que nombra la finca y el total de resultados, y cada columna tiene
  su cabecera `<th>` asociada. *(1.3.1)*
- [ ] **AC-A11Y-5** — Given el control de paginación, When lo alcanza un lector de pantalla,
  Then está expuesto como navegación con un nombre accesible, y al cambiar de página el foco
  **permanece** en el control pulsado. *(2.4.3, 4.1.2)*
- [ ] **AC-A11Y-6** — Given un cambio de filtro o de página, When se completa la carga, Then una
  región `aria-live="polite"` anuncia el número de resultados, y el foco **no** se mueve solo.
  *(2.4.3, 4.1.3)*
- [ ] **AC-A11Y-7** — Given la barra de filtros, When se navega con Tab, Then cada control
  (lote, variable, rango, fechas personalizadas) tiene una etiqueta asociada programáticamente
  y un anillo de foco visible. *(1.3.1, 2.4.7, 3.3.2)*
- [ ] **AC-A11Y-8** — Given el conmutador Gráficos/Tabla, When se opera solo con teclado, Then
  se puede cambiar de vista con las flechas y el panel activo muestra un anillo de foco visible.
  *(2.1.1, 2.4.7)*
- [ ] **AC-A11Y-9** — Given el date-picker de rango personalizado, When se abre, Then el foco
  queda contenido en el popover, Escape lo cierra devolviendo el foco al disparador, y existe
  además un campo de entrada tecleada para no depender del calendario. *(2.1.1, 2.1.2)*
- [ ] **AC-A11Y-10** — Given cualquier estado de error o de tope de exportación excedido, When
  se muestra, Then va en un `role="alert"` con **texto** — nunca comunicado solo por color o
  ícono — y el aviso de exportación es visible en la página, no únicamente en un toast efímero.
  *(1.4.1, 4.1.3)*
- [ ] **AC-A11Y-11** — Given los controles de exportación y de paginación, When se miden, Then
  su área de activación es de al menos 24×24 px. *(2.5.8)*
- [ ] **AC-A11Y-12** — Given la vista de Gráficos, When se distinguen las series, Then el color
  **no** es el único medio: cada gráfico lleva su propio título y unidad. *(1.4.1)*
