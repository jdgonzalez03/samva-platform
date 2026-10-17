# Claude Code

Two top-level sections: **Guidelines** (rules to follow when changing the system) and **Continuous Improvement** (retrospective to run after each task). Architecture (how the system is built — monorepo layout, stack, per-app design) lives in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — read it first; each area (`frontend/`, `backend/`, `e2e/`) also has its own deeper `CLAUDE.md` for area-specific rules.

## Guidelines

### Writing rules
- Each rule must be a single concise bullet point; group related rules under sections.
- Whenever you find a contradiction or new knowledge, save it in the relevant CLAUDE.md file.
- Don't hardcode dependency versions in prose docs (they rot) — name the stack and point to `backend/requirements.txt` / `frontend/package.json` for exact pins.

### Comments
- Comment only the non-obvious *why* a reader can't infer from the code; never restate what the code does, narrate a change, or reference alternatives/decisions absent from the code.
- Litmus test: if a comment would only make sense to someone who watched this change happen — it defends a decision, says what the code used to be, or reassures against an alternative — delete it. Write for a reader who has only ever seen the current code, never the diff.

### Git
- Never run `git` at all — no commit, stage, push/pull, branch, checkout, reset, rebase, merge, or any other git command.

### Tests
- Every change must fix affected tests and add tests for new behaviour (Django + Playwright; the frontend has no Vitest setup, so UI behaviour is covered in `e2e/frontend/`) — never leave tests behind.
- Run the area's suite before touching code, so you hold a baseline: a later failure is then unambiguously the new change's fault rather than pre-existing breakage.

### Django / make commands
- Never run `python manage.py` directly; use `make` targets (route through Docker): `migrations`, `migrate`, `test`, `loaddata`, `createsuperuser`, `shell`, `bash`.
- Commands for backend development are in `backend/makefile` (run from `backend/`); the root `Makefile` has the stack-level targets (`up-dev`, `down`, `logs`, `lint`, …).

### E2E
- Any multi-step user-facing feature (clicks, UI state changes, navigation) needs a Playwright test in `e2e/frontend/<module>.spec.ts` matching the frontend layer name; API-level tests go in `e2e/backend/`. The layout is flat — there is no `e2e/tests/` directory.
- Reuse `e2e/frontend/helpers.ts`: `loginAs` (logs in through the real form as the seeded user) and `gotoHydrated` (navigates and waits for hydration); every UI string a spec selects by lives in the exported `T` map, never inline in the spec.
- A spec's catch-all API stub matches `url.pathname.startsWith('/api/')`, never a `**/api/**` glob: against the dev server the glob also swallows Vite modules under `/_nuxt/@fs/.../utils/api/`, so the app never hydrates and every stubbed spec times out in `gotoHydrated`.
- Stub third-party map tile hosts with `page.route` in any spec that renders the map — specs must never depend on an external tile server.
- `e2e/` has no formatter config and its specs are not Prettier-clean under any single setting — never run Prettier over existing specs (it rewrites unrelated lines); match the surrounding style by hand (single quotes, no semicolons).
- The sensor history specs need seeded readings inside the default 7-day window: when they fail on chart/row counts after the seed has aged, run `make seed-sensors` (from `backend/`) before suspecting code.
- `USkeleton` renders with `role="alert"`, so a spec locating an error alert filters by text (`getByRole('alert').filter({ hasText })`); a `UPageCard` with `to` has a zero-size `<a>` under an overlay, so follow it with `.press('Enter')` instead of `.click()` and assert its visibility on the title text — the link itself always reads as hidden.
- A failure in a full run that passes when rerun in isolation is usually dev-server HMR from concurrent edits (another session): rerun the failing specs alone before debugging.
- An axe scan runs on the loaded page, never on skeletons: wait for `[aria-busy="true"]` to reach count 0 first, or a scrolling panel with nothing focusable yet trips `scrollable-region-focusable`; a full run can also leave the page in light mode, so colour contrast must pass in both themes.
- To axe-scan one page without inheriting shared-layout violations, scope the scan to its panel: `UDashboardPanel` renders `id="<storageKey>-panel-<id>"`, so include `[id$="-panel-<id>"]`.
- A spec never asserts that a planned feature is absent, and never borrows a future route as its 404 fixture — both break on the day that feature ships, turning a green suite red for no defect.
- The login form rejects addresses without a dot in the domain, so `admin@localhost` cannot drive `loginAs`; when the dev DB has no seed users (and real data you must not overwrite with `make loaddata`), stub the auth endpoints in a throwaway spec rather than loading fixtures.
- New demo fixtures go on farms the main e2e user (juan.perez) does not own: his specs assert exact variable counts per plot and farm.
- Run the suite with `npx playwright test` from `e2e/` (there is no make target); specs that push readings into the same sensor must vary their values (e.g. by the current second), since the history table shows minutes and identical rows trip the no-repeat pagination check.

### Build vs. reuse
- Before hand-rolling anything non-trivial (a pattern, an abstraction, infra glue), challenge the instinct to write custom code: check whether a mature, well-maintained library does it better, and weigh that explicitly (standardisation, caching, less code to own vs. an added dependency) rather than defaulting to bespoke.
- When the call is close, surface the trade-off to the user instead of silently deciding for them.
- Agents and skills the team relies on must be project-local (committed in `.claude/`), never global plugins — plugin agents/skills don't travel with the repo, so a contributor's fresh clone won't have them.

### Python packages
- When adding to `requirements.txt`, pin the exact latest stable version from PyPI (`package==x.y.z`).

### Agent pipelines
- Orchestration and user-approval gates live in the main session; sub-agents are one level deep (can't dispatch other sub-agents) and can't prompt the user — they propose, the orchestrator asks. See the `/feature` pipeline (`.claude/skills/feature/`, `docs/superpowers/specs/2026-06-30-feature-pipeline-orchestration-design.md`).

## Continuous Improvement
- After every task, run a short retrospective before finishing: review the whole execution and capture only reusable, long-term improvements.
- Hunt for: slow/inaccurate/inefficient steps; unnecessary permission prompts; redundant file reads or repeated repo exploration; knowledge rediscovered instead of reused; repeated patterns worth making permanent rules; better tool/execution orders that cut tool calls, tokens, or rework.
- Record each finding as a rule in the relevant `CLAUDE.md` (area-specific in `frontend/`·`backend/`·`e2e/`; cross-cutting here) — never task-specific, temporary, or soon-outdated notes.
- Before adding, confirm the rule isn't already present; refine or merge an existing rule rather than duplicating. Keep every `CLAUDE.md` concise and redundancy-free.
