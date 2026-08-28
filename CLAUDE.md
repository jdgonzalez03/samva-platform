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
- Every change must fix affected tests and add tests for new behaviour (Django + Vitest/Playwright) — never leave tests behind.
- Run the area's suite before touching code, so you hold a baseline: a later failure is then unambiguously the new change's fault rather than pre-existing breakage.

### Django / make commands
- Never run `python manage.py` directly; use `make` targets (route through Docker): `migrations`, `migrate`, `test`, `loaddata`, `createsuperuser`, `shell`, `bash`.
- Commands for backend development are in `backend/makefile` (run from `backend/`); the root `Makefile` has the stack-level targets (`up-dev`, `down`, `logs`, `lint`, …).

### E2E
- Any multi-step user-facing feature (clicks, UI state changes, navigation) needs a Playwright test in `e2e/frontend/<module>.spec.ts` matching the frontend layer name; API-level tests go in `e2e/backend/`. The layout is flat — there is no `e2e/tests/` directory.
- Reuse `e2e/frontend/helpers.ts`: `loginAs` (logs in through the real form as the seeded user) and `gotoHydrated` (navigates and waits for hydration); every UI string a spec selects by lives in the exported `T` map, never inline in the spec.
- A spec never asserts that a planned feature is absent, and never borrows a future route as its 404 fixture — both break on the day that feature ships, turning a green suite red for no defect.

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
