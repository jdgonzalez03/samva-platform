---
name: feature
description: Orchestrate a full-stack feature through the backend -> frontend -> qa pipeline, each stage implemented by a senior engineer and reviewed by a principal reviewer (with one fix pass). Use ONLY when explicitly invoked as `/feature <description>`. Do not auto-trigger on ordinary questions, edits, or debugging.
---

# Feature pipeline (orchestrator)

You (the main session) are the orchestrator. You hold the Agent tool; the sub-agents do
not. Before planning, a **discovery phase** (business-analyst + ux-designer) interrogates
the feature and you resolve its open questions with the user into a `spec.md` plus an
`acceptance-criteria.md` — the numbered, testable behaviours every role verifies its work
against and QA signs off at the end. Then a **software-architect** turns the spec into an
authoritative API contract (`contract.md`) so backend and frontend can be built **in
parallel** against one source of truth. There is
**exactly one mandatory stop — after planning**: present the plan and wait for the user's
approval before any implementation begins. After approval, a **baseline health check**
runs the existing test suites and **aborts** if any are already failing.
Once the plan is approved and the baseline is green, run the build stages — backend and
frontend **in parallel**, then qa — **autonomously** without further stops. The per-area
reviewers (each with one fix pass) are the safety net during the autonomous part. At the
very end, if any agent proposed a continuous-improvement rule, ask the user per item before
writing it — agents only propose, you apply approved ones.

See `docs/superpowers/specs/2026-06-30-feature-pipeline-orchestration-design.md` for the
design rationale.

## Steps

1. **Slug & setup.** Turn the feature description into a kebab-case slug, then prefix it
   with today's date (`YYYY-MM-DD`) to form `<slug>` — e.g. `2026-07-01-post-settings`.
   This date prefix is **mandatory**: every handoff folder carries it (match the existing
   `docs/handoffs/` entries), so handoffs sort chronologically. All artifacts live in
   `docs/handoffs/<slug>/`. (Write auto-creates the folder — do not `mkdir`.)

2. **Discovery (business + UX), then resolve into `spec.md`.** Dispatch `business-analyst`
   and `ux-designer` **in parallel** (one message, two Agent calls — neither depends on the
   other), each with the `<slug>` and feature description. They write `discovery-ba.md` and
   `discovery-ux.md`. Read both. Collect every `Open questions` item, plus any
   `Recommendation` that is not "proceed". **Discuss these with the user interactively**
   until each is resolved — this is the questioning step the pipeline previously skipped;
   the sub-agents cannot ask the user, so you do. Then write `docs/handoffs/<slug>/spec.md`
   capturing the agreed requirements (Goal / In scope / Out of scope / UX notes / Resolved
   decisions), and — as a separate authoritative artifact — write
   `docs/handoffs/<slug>/acceptance-criteria.md` from the BA's proposed criteria plus the
   resolved decisions: a numbered Gherkin (Given/When/Then) checklist with stable IDs
   (`AC1`, `AC2`, …) and unchecked boxes. **When the feature has UI, include the
   `ux-designer`'s accessibility criteria (`AC-A11Y-*`, WCAG 2.2 AA) as an `Accessibility`
   section of the same doc** — they are first-class ACs the engineer builds to and the
   reviewer + QA verify (QA runs an `@axe-core/playwright` backstop plus keyboard/focus
   assertions). Backend-only features get none. It is the behaviour source of truth every
   downstream role verifies against (the `contract.md` of behaviour); `spec.md` points to
   it rather than embedding the list, so there is one copy and no drift. If the BA
   recommended against building or scoping down and the user agrees, stop or narrow
   accordingly before planning.

3. **API contract (software-architect).** Dispatch `software-architect` with the `<slug>`.
   It reads `spec.md` + the discovery docs and writes the authoritative HTTP API contract
   to `docs/handoffs/<slug>/contract.md` — the single source of truth backend and frontend
   both build against. Read it back. If its final message reports `Open questions`, resolve
   them with the user (same as discovery) and have the architect update `contract.md`, or
   fold the resolution in yourself, before planning. The contract must be settled before the
   plan, because the plan assumes it.

4. **Plan, then STOP for approval (mandatory gate).** Dispatch the built-in `Plan` agent
   with `spec.md`, `contract.md`, and `acceptance-criteria.md` (not the raw description) and
   instruct it to write the implementation plan to `docs/handoffs/<slug>/plan.md` (covering
   all three areas: backend, frontend, e2e). The plan must honor the contract and cover
   every acceptance criterion, not redefine either. Read it back, present
   a concise summary to the user, and **wait for explicit approval**. Do NOT dispatch the
   engineers until the user agrees to proceed.
   - If the user requests changes, revise `plan.md` (re-dispatch `Plan` or edit directly)
     and ask again. Only continue once the user approves.

5. **Baseline health check (green-before-build gate).** Before any engineer starts,
   confirm the existing suite is green so a later failure is unambiguously the new
   change's fault, not pre-existing breakage. Run the single deterministic gate:

   ```
   make all-test
   ```

   This runs all three suites (backend -> frontend -> e2e) and aborts on the first
   failure (non-zero exit). If `make all-test` fails, **STOP immediately**: report which
   suite failed (with the relevant failing output) and tell the user to fix the failing
   tests before running `/feature` again. Do NOT start the backend stage on a red baseline.

6. **Backend + frontend stages, in parallel (each: engineer + reviewer, one fix loop).**
   Both build against `contract.md`, not against each other — dispatch them concurrently.
   - **Kick off both engineers in one message** (two Agent calls): `backend-engineer` with
     "implement the backend slice per the plan and contract" and `frontend-engineer` with
     "implement the frontend slice per the plan and contract". Pass the `<slug>` to each.
   - When both return, **dispatch both reviewers** (`backend-reviewer`, `frontend-reviewer`)
     in one message. Read `review-backend.md` and `review-frontend.md`.
   - For each area whose verdict is CHANGES REQUESTED, dispatch that engineer **once more**
     to "address the blocking findings" in its review doc; run the two fix passes
     concurrently too. Do not loop further — if blocking issues remain, record and carry on.
   - **Contract-deviation reconciliation.** A handoff may flag that it could not honor the
     contract (`Contract deviations` in the doc). The contract is authoritative: if any side
     deviated, update `contract.md` to the agreed shape and re-dispatch the *other* side to
     conform, before QA. Do not let backend and frontend ship divergent interfaces.

7. **QA stage.** Same pattern with `qa-engineer` then `qa-reviewer` (`review-qa.md`), one
   fix pass max. The QA engineer reads `contract.md` + `backend.md` + `frontend.md` for the
   flow.

8. **Report.** Summarize what shipped and link every handoff/review doc in
   `docs/handoffs/<slug>/`. The feature is **complete only when every acceptance criterion
   is ✓** in the QA handoff's `AC checklist`. Surface any ✗ (unmet AC) and any unresolved
   blocking findings prominently — a feature with an unmet AC is not done, say so plainly.

9. **Continuous-improvement review (human gate).** Gather every `## Proposed improvements`
   entry the agents wrote into their handoff/review docs this run. If there are none, skip
   this step silently. Otherwise present each proposed rule to the user (what it is + where
   it would go) and **ask per item: add as-is / edit then add / skip**. Apply ONLY the
   approved rules — you (the orchestrator) make the edit to the named `CLAUDE.md` or agent
   spec, applying any wording change the user asked for. Before writing, check the rule
   isn't already present; refine/merge rather than duplicate, and keep the file concise.
   The agents only propose — nothing reaches a rule file without the user's yes.

## Rules

- Order: discovery -> contract -> plan -> (backend ‖ frontend) -> qa. Discovery, contract,
  and plan are sequential (each consumes the prior). Backend and frontend run **in parallel**
  against `contract.md` — that is the point of the contract. QA waits for both.
- Each sub-agent reads only what it needs (ARCHITECTURE + its area CLAUDE.md + the version
  pins + the upstream handoff docs incl. `contract.md` and `acceptance-criteria.md`) — that
  small context is the point. Engineers self-check the AC their slice owns; reviewers verify
  those self-checks are honest; QA verifies the full list end-to-end.
- Never run `git` (project rule). Use `make` targets for backend, npm scripts for frontend,
  `make e2e-test` for e2e — the agents already know this.
- If a stage reports a hard blocker it cannot resolve, finish the current stage's report
  and stop rather than building the next stage on a broken base.
