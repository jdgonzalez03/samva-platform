---
name: accessibility
description: WCAG 2.2 AA accessibility requirements for this app's UI (Vue 3 + Nuxt UI). Load when writing accessibility acceptance criteria, building or reviewing any frontend surface, or verifying a11y in tests. Defines what must be true; pair with modern-web-guidance for the current implementation technique and @axe-core/playwright for the automated backstop.
---

# Accessibility (WCAG 2.2 AA)

The bar for every UI surface in this project is **WCAG 2.2 Level AA**. This skill is a
stack-tailored, testable checklist — not a copy of the spec. It maps the AA success criteria to
concrete patterns for this app (Vue 3 `<script setup>` + Nuxt UI components + our conventions).
For the *current best way* to implement a given control, invoke `modern-web-guidance`. For the
authoritative wording, see <https://www.w3.org/TR/WCAG22/> and
<https://www.w3.org/WAI/WCAG22/quickref/?levels=aa>.

Prefer **native semantics and Nuxt UI components** over hand-rolled ARIA — the right element
(`<button>`, `<a>`, `<nav>`, `<ul>`) carries role, focusability, and keyboard behaviour for free.
The first rule of ARIA is: don't use ARIA if a native element does the job.

## Keyboard & focus (2.1.1, 2.1.2, 2.4.3, 2.4.7, 2.4.11, 2.4.13)

- Every interactive control is reachable and operable by keyboard alone (Tab/Shift-Tab, Enter/Space
  on buttons). Never bind an action only to a mouse/pointer event.
- Visible focus indicator on every focusable element — never `outline: none` without an equally
  visible replacement (Nuxt UI's focus-visible rings satisfy this; don't strip them).
- No keyboard trap: focus can always move away from a component.
- Logical focus order matching visual order; don't reorder with positive `tabindex`.
- **Dialogs/modals** (our `LikersModal`, `CommentLikersModal`): move focus into the dialog on open,
  trap focus within while open, return focus to the trigger on close, and close on `Escape`. Nuxt
  UI's `UModal`/overlay primitives handle this — use them rather than a bare floating `<div>`.
- 2.2 *Focus not obscured (2.4.11)*: an opened overlay/sticky bar must not hide the focused element.

## Semantics, names & roles (1.3.1, 4.1.2, 4.1.3)

- Icon-only buttons MUST have an accessible name — `aria-label` (our like heart: `aria-label="Like"`
  + `aria-pressed`). A control's visible label and accessible name must agree.
- Toggle buttons expose state with `aria-pressed`; expanded/collapsed with `aria-expanded`;
  disabled with the `disabled` attribute (not just styling).
- Status/async updates announced via a live region — `role="alert"` / `aria-live` for toasts and
  inline errors (our toast pattern already renders an `role="alert"` region; keep it).
- Custom widgets carry correct role/name/value; verify against the ARIA Authoring Practices pattern
  for that widget before hand-rolling.

## Forms (1.3.1, 3.3.1, 3.3.2, 3.3.3, 4.1.2)

- Every input has a programmatically associated `<label>` (or `aria-label`/`aria-labelledby`).
- Errors: set `aria-invalid`, link the message with `aria-describedby`, and make it announced (a
  live region or focus move) — never signal an error by colour alone.
- Provide labels/instructions before the field, not only as a placeholder.

## Perceivable (1.4.3, 1.4.11, 1.4.4, 1.4.10, 1.4.12, 1.4.13, 2.5.8)

- Text contrast ≥ 4.5:1 (≥ 3:1 for large text ≥ 24px/18.66px-bold). Non-text UI (icons, borders,
  focus rings, control boundaries) ≥ 3:1. Verify custom colours against the app theme.
- Never convey information by colour alone — pair with text, icon, or shape.
- Target size ≥ 24×24 px (2.5.8), or adequate spacing. Watch dense rows (the comment metadata line).
- Content reflows and stays usable at 200% zoom / 320px width; no loss of content or function.
- Honour `prefers-reduced-motion` for non-essential animation/transitions.

## WCAG 2.2 additions to watch (2.5.7, 3.2.6, 3.3.7)

- Dragging (2.5.7): any drag interaction has a single-pointer alternative (tap/click).
- Consistent help (3.2.6): help/support affordances appear in a consistent location across pages.
- Redundant entry (3.3.7): don't force re-entering info already provided in the same flow.

## Writing accessibility acceptance criteria

When a feature has UI, produce numbered Given/When/Then a11y ACs (stable IDs, same format as the
functional ACs) phrased around **keyboard and screen-reader behaviour**, e.g.:

> **AC-A11Y-1** — Given the comment like control, When I Tab to it, Then it receives a visible
> focus ring and activates on Enter/Space; the button exposes `aria-label="Like"` and
> `aria-pressed` reflecting liked state.
> **AC-A11Y-2** — Given the likers modal, When it opens, Then focus moves into it, is trapped,
> `Escape` closes it, and focus returns to the count button that opened it.

Only include criteria the feature's surfaces actually touch — don't pad. Backend-only features get
none.

## Verifying accessibility

- **Automated backstop:** `@axe-core/playwright` — scan each feature UI surface for AA violations
  (`await new AxeBuilder({ page }).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze()`
  and assert zero violations). Axe catches contrast, roles, labels, and ARIA misuse (~40% of AA);
  it does NOT catch keyboard order, focus management, or meaningful names — cover those by hand.
- **Keyboard/focus e2e (Playwright):** `page.keyboard.press('Tab')`, assert `toBeFocused()`, drive
  controls via Enter/Space and `Escape`, assert focus return after modal close.
- **Semantic locators:** query by role/name (`getByRole('button', { name: 'Like' })`). If a locator
  by role/name is hard to write, that is usually an accessibility smell, not a test problem — fix
  the markup. Accessible markup makes e2e simpler and more robust.
