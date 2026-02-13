# Telemetry Dashboard Redesign: Compact Grid + Pulse Vitality + Timeline

## TL;DR

> **Quick Summary**: Redesign the factory telemetry dashboard (`factory/telemetry.py`) to compact 5 stacked KPI blocks into a CSS grid row, add CSS pulse animations and delta trend arrows to make the dashboard feel alive, and insert a horizontal iteration timeline to visualize progression.
> 
> **Deliverables**:
> - Compacted KPI grid (1-2 rows instead of 5 stacked full-width blocks)
> - CSS keyframe pulse animations on live status and active metrics
> - Delta trend arrows (↑↓→) on metrics comparing latest vs prior iteration
> - Horizontal timeline bar showing iteration markers with pass/fail coloring
> 
> **Estimated Effort**: Short
> **Parallel Execution**: NO — sequential (3 passes within single file)
> **Critical Path**: Task 1 (KPI Grid + Deltas) → Task 2 (Pulse Animations) → Task 3 (Timeline) → Task 4 (Verification)

---

## Context

### Original Request
The telemetry dashboard isn't responding to iterations and updating everything as needed. The user needs confidence that tests are actually running and that outputs are progressing. Additionally, each KPI gets its own full-width div — too much wasted vertical space. Compact them into fewer lines.

### Interview Summary
**Key Discussions**:
- Three creative directions from Muse consultation: Modular Grid, Pulse-Driven Vitality, Narrative Timeline
- User confirmed: combine all three directions into a single cohesive redesign

**Research Findings**:
- Single file to modify: `factory/telemetry.py` (456 lines), specifically `generate_html()` and the `<style>` block
- Current KPI pattern: 5 stacked `.metric` divs, each full-width with `padding: 15px; margin: 10px 0`
- Existing grid pattern at lines 286-292: `display:grid;grid-template-columns:1fr 1fr;gap:10px;` — extend this
- `iteration_log.jsonl` currently has 2 entries with `metrics_summary` containing `identity_similarity`, `ssim`, `blur_score`, `artifact_score`
- `.metric` CSS class is reused in multi-source section (lines 426-429) — must use new class for KPI grid to avoid side effects
- HTML generated via Python f-string concatenation — no template engine

### Metis Review
**Identified Gaps** (addressed):
- New CSS class needed for KPI grid (`.kpi-grid`) since `.metric` is reused in multi-source section — addressed in Task 1
- Delta arrows need minimum threshold to avoid showing ↑ for +0.0004 changes — addressed in Task 1
- Zero-iteration and single-iteration edge cases for deltas and timeline — addressed in Tasks 1, 3
- CSS animation performance: must use `transform`/`opacity` only, animations are stateless due to 5s meta-refresh — addressed in Task 2
- Timeline needs cap on markers for readability — addressed in Task 3
- Multi-source section's `.metric` divs intentionally excluded from scope — acknowledged

---

## Work Objectives

### Core Objective
Transform the factory telemetry dashboard from a static-feeling data dump into a compact, alive-feeling monitoring interface that gives the user immediate confidence that tests are running and metrics are progressing.

### Concrete Deliverables
- Modified `factory/telemetry.py` with redesigned `generate_html()` function
- Regenerated `factory/telemetry.html` reflecting all changes

### Definition of Done
- [x] KPI metrics render in a compact grid (3+ columns, 1-2 rows)
- [x] Delta arrows (↑↓→) appear on metrics when 2+ iterations exist
- [x] CSS pulse animation exists in generated HTML
- [x] Horizontal timeline renders when 2+ iterations exist
- [x] All existing sections preserved (Video Outputs, Swap Output, Iteration History, etc.)
- [x] Dark theme preserved
- [x] Zero-iteration state generates without error

### Must Have
- Compact KPI grid replacing 5 stacked full-width blocks
- Delta trend indicators (↑↓→) computed in Python with minimum thresholds
- At least one CSS `@keyframes` pulse animation
- Horizontal iteration timeline
- Graceful degradation for 0 and 1 iteration states

### Must NOT Have (Guardrails)
- No JavaScript beyond ≤20 lines cosmetic-only (no fetch/XHR/WebSocket/external libs)
- No refactoring of helper functions (`_live_status_section`, `_video_outputs_section`, `_result_images_section`, `_multi_source_section`, `_archive_gallery`)
- No SVG sparklines or interactive chart elements
- No `@media` responsive/mobile queries
- No template engine switch (stay with f-strings)
- No extracting CSS to external files
- No adding new metrics beyond the existing 5 KPIs (Total Iterations, Identity, SSIM, Cost, Status)
- No modifying the existing `.metric` CSS class (it's reused in multi-source section)
- No changing section ordering
- No external dependencies
- No fixing the base64 video bloat issue (acknowledged, out of scope)
- Do NOT animate `background-color`, `box-shadow`, `width`, `height` in `@keyframes` (layout thrash) — use `transform`/`opacity` only

---

## Verification Strategy

> **UNIVERSAL RULE: ZERO HUMAN INTERVENTION**
>
> ALL tasks are verifiable WITHOUT any human action.

### Test Decision
- **Infrastructure exists**: N/A (no test framework for this static HTML generator)
- **Automated tests**: None — verification via CLI commands and Playwright
- **Framework**: N/A

### Agent-Executed QA Scenarios (MANDATORY — ALL tasks)

Every task includes specific CLI and Playwright verification scenarios below.

---

## Execution Strategy

### Sequential Execution

```
Task 1 → Task 2 → Task 3 → Task 4
```

All tasks modify the same function in the same file (`generate_html()` in `factory/telemetry.py`). They must be sequential to avoid merge conflicts. Each pass is independently testable.

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|------|------------|--------|---------------------|
| 1 | None | 2, 3, 4 | None |
| 2 | 1 | 3, 4 | None |
| 3 | 2 | 4 | None |
| 4 | 3 | None | None |

### Agent Dispatch Summary

| Order | Task | Recommended Agent |
|-------|------|-------------------|
| 1 | KPI Grid + Deltas | task(category="visual-engineering", load_skills=["frontend-ui-ux"]) |
| 2 | Pulse Animations | task(category="visual-engineering", load_skills=["frontend-ui-ux"]) |
| 3 | Timeline | task(category="visual-engineering", load_skills=["frontend-ui-ux"]) |
| 4 | Final Verification | task(category="quick", load_skills=["playwright"]) |

---

## TODOs

- [x] 1. Compact KPI Grid Layout + Delta Trend Arrows

  **What to do**:
  - Add a new `.kpi-grid` CSS class to the `<style>` block in `generate_html()` using `display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px;` (or `repeat(3, 1fr)` for a 3+2 layout if 5-across is too cramped)
  - Add a `.kpi-cell` CSS class for individual KPI cards — compact padding (~10px), small label (10px font), prominent value (20px font bold), preserve `.pass`/`.fail`/`.pending` coloring
  - Replace the 5 stacked `.metric` divs (lines 297-331 of `generate_html()`) with a single `.kpi-grid` container holding 5 `.kpi-cell` children
  - Add a Python helper function `_compute_deltas(iterations)` that compares `iterations[-1]` vs `iterations[-2]` metrics and returns delta info with these thresholds:
    - `identity_similarity`: ±0.01 (below → "→" flat)
    - `ssim`: ±0.005 (below → "→" flat)
    - `cost_so_far`: ±$0.01 (below → "→" flat)
  - Render delta arrows (↑ green, ↓ red, → gray) as small text next to each metric value
  - Handle edge cases:
    - 0 iterations: show "Waiting for first iteration..." in a single cell spanning the grid, OR collapse to a message
    - 1 iteration: show KPI values but NO delta arrows (no prior to compare)
    - 2+ iterations: show KPI values WITH delta arrows

  **Must NOT do**:
  - Do NOT modify the existing `.metric` CSS class — it's used by the multi-source section
  - Do NOT add new metrics beyond the 5 existing KPIs
  - Do NOT refactor any helper functions

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: CSS grid layout work, visual styling of compact cards
  - **Skills**: [`frontend-ui-ux`]
    - `frontend-ui-ux`: CSS Grid layout design and visual hierarchy for compact KPI cards

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (first task)
  - **Blocks**: Tasks 2, 3, 4
  - **Blocked By**: None

  **References**:

  **Pattern References** (existing code to follow):
  - `factory/telemetry.py:286-292` — Existing CSS grid pattern for GPU metrics (`display:grid;grid-template-columns:1fr 1fr;gap:10px;`). Extend this same inline-style pattern for the KPI grid, but use a CSS class instead.
  - `factory/telemetry.py:254-270` — CSS class definitions in `<style>` block. Add `.kpi-grid` and `.kpi-cell` here.
  - `factory/telemetry.py:297-331` — The 5 KPI `.metric` divs to REPLACE. These are the exact lines to remove and substitute with the grid.
  - `factory/telemetry.py:392-398` — Zero-iteration fallback ("Waiting for first iteration..."). Must update to work within grid layout.

  **API/Type References**:
  - `factory/iteration_log.jsonl` — Data shape: `{"iteration_number": N, "metrics_summary": {"identity_similarity": 0.5282, "ssim": 0.9404, ...}, "cost_so_far": 0.08, "status": "failed"}`

  **Documentation References**:
  - `factory/README.md` — Available metrics and status types

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: KPI grid renders with 3+ columns
    Tool: Bash
    Preconditions: factory/iteration_log.jsonl exists with 2+ entries
    Steps:
      1. python factory/telemetry.py
      2. Assert: exit code 0
      3. grep 'kpi-grid' factory/telemetry.html
      4. Assert: output contains 'kpi-grid' class
      5. grep 'grid-template-columns' factory/telemetry.html
      6. Assert: output contains a grid definition with 3+ columns
    Expected Result: KPI section uses CSS grid with multiple columns
    Evidence: grep output captured

  Scenario: Delta arrows appear with 2 iterations
    Tool: Bash
    Preconditions: factory/iteration_log.jsonl has 2 entries
    Steps:
      1. python factory/telemetry.py
      2. grep -oE '[↑↓→]' factory/telemetry.html | wc -l
      3. Assert: count ≥ 2 (at least identity and SSIM have arrows)
    Expected Result: Delta trend indicators present in HTML
    Evidence: grep count output

  Scenario: Zero-iteration state generates without error
    Tool: Bash
    Preconditions: None
    Steps:
      1. mv factory/iteration_log.jsonl factory/iteration_log.jsonl.bak
      2. python factory/telemetry.py
      3. Assert: exit code 0
      4. Assert: factory/telemetry.html exists
      5. mv factory/iteration_log.jsonl.bak factory/iteration_log.jsonl
    Expected Result: Dashboard generates without crash when no iterations exist
    Evidence: exit code captured

  Scenario: Existing .metric class unchanged
    Tool: Bash
    Preconditions: None
    Steps:
      1. python factory/telemetry.py
      2. grep '\.metric ' factory/telemetry.html | head -3
      3. Assert: .metric CSS still contains "background: #2d2d2d" and "padding: 15px"
    Expected Result: Original .metric class preserved for multi-source section
    Evidence: grep output
  ```

  **Evidence to Capture:**
  - [x] grep outputs for grid classes and delta arrows
  - [x] Exit code from zero-iteration test

  **Commit**: YES
  - Message: `feat(factory): compact KPI grid layout with delta trend arrows`
  - Files: `factory/telemetry.py`
  - Pre-commit: `python factory/telemetry.py`

---

- [x] 2. CSS Pulse Animations for Live Status

  **What to do**:
  - Add `@keyframes` definitions to the `<style>` block in `generate_html()`:
    - `@keyframes pulse` — gentle opacity oscillation from 1.0 → 0.7 → 1.0 using `opacity` (GPU-composited, no layout thrash)
    - `@keyframes fade-in` — subtle scale + opacity entrance using `transform: scale(0.98)` → `transform: scale(1.0)` and `opacity: 0.8` → `opacity: 1.0`
  - Apply `animation: pulse 2s ease-in-out infinite;` to the Live Status card's phase badge (`.status-badge` in `_live_status_section`) when phase is NOT "done" and NOT "error" — i.e., only pulse when actively running
  - Add a `.recently-changed` CSS class with the `fade-in` animation, applied to KPI cells where the delta is non-zero (↑ or ↓) — visually highlights which metrics changed
  - Add a subtle pulsing dot indicator (●) next to the "Last updated" timestamp using the `pulse` animation — a heartbeat showing the dashboard is refreshing
  - **Critical**: All animations must be stateless — they restart every 5 seconds on meta-refresh and look correct at any point in their cycle. Do NOT rely on animation start state.
  - If `live_status.json` timestamp is >5 minutes old or empty, do NOT apply pulse animation (stale data shouldn't appear alive). Compute staleness in Python using `datetime.now()` vs parsed timestamp.

  **Must NOT do**:
  - Do NOT animate `background-color`, `box-shadow`, `width`, `height` in `@keyframes` (causes layout reflow)
  - Do NOT add JavaScript for animation control
  - Do NOT modify `_live_status_section` function signature — only modify the HTML it generates
  - Do NOT pulse the "No active process" / "DONE" states

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: CSS animation design, visual polish
  - **Skills**: [`frontend-ui-ux`]
    - `frontend-ui-ux`: CSS animation expertise, visual design sensibility

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (second task)
  - **Blocks**: Tasks 3, 4
  - **Blocked By**: Task 1

  **References**:

  **Pattern References**:
  - `factory/telemetry.py:251-269` — CSS class definitions in `<style>` block. Add `@keyframes` and animation classes here.
  - `factory/telemetry.py:83-138` — `_live_status_section()` function. The phase badge HTML is generated at line 130 (`<span class="status-badge" ...>`). Apply pulse animation class conditionally here.
  - `factory/telemetry.py:109-113` — `phase_colors` dict. Use this to determine active vs done/error phases.
  - `factory/telemetry.py:275` — "Last updated" timestamp line. Add pulsing dot indicator here.

  **API/Type References**:
  - `factory/results/live_status.json` — `timestamp` field for staleness detection, `phase` field for animation gating

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: @keyframes pulse animation defined
    Tool: Bash
    Preconditions: Task 1 completed
    Steps:
      1. python factory/telemetry.py
      2. grep '@keyframes pulse' factory/telemetry.html
      3. Assert: output contains the pulse keyframe definition
      4. grep '@keyframes fade-in' factory/telemetry.html
      5. Assert: output contains the fade-in keyframe definition
    Expected Result: Both animation keyframes are defined in CSS
    Evidence: grep output

  Scenario: Pulse animation uses only opacity/transform
    Tool: Bash
    Preconditions: None
    Steps:
      1. python factory/telemetry.py
      2. Extract the @keyframes blocks from factory/telemetry.html
      3. Assert: keyframe blocks contain only 'opacity' and/or 'transform' properties
      4. Assert: keyframe blocks do NOT contain 'background', 'box-shadow', 'width', 'height'
    Expected Result: Animations are GPU-composited only
    Evidence: grep output

  Scenario: Heartbeat dot appears near timestamp
    Tool: Bash
    Preconditions: None
    Steps:
      1. python factory/telemetry.py
      2. grep -c 'pulse' factory/telemetry.html
      3. Assert: count ≥ 2 (keyframe definition + at least one animation application)
    Expected Result: Pulse animation is both defined and applied
    Evidence: grep count
  ```

  **Evidence to Capture:**
  - [x] grep outputs for keyframe definitions
  - [x] grep confirming no layout-thrashing properties in animations

  **Commit**: YES
  - Message: `feat(factory): add CSS pulse animations and heartbeat indicator to dashboard`
  - Files: `factory/telemetry.py`
  - Pre-commit: `python factory/telemetry.py`

---

- [x] 3. Horizontal Iteration Timeline

  **What to do**:
  - Add a `.iteration-timeline` CSS class: horizontal flex/grid container, compact height (~60px), scrollable overflow if needed
  - Add `.timeline-marker` CSS class: small circles (~16px diameter) with pass/fail coloring (green for passed, red for failed, orange for running, purple for plateau)
  - Add `.timeline-track` CSS class: thin horizontal line connecting markers
  - Create a new Python helper function `_iteration_timeline_section(iterations)` that:
    - Returns empty string if `len(iterations) < 2` (not enough data for a meaningful timeline)
    - Takes the last 15 iterations max (cap for readability)
    - Renders each iteration as a colored dot on a horizontal track
    - Labels: iteration number below each dot
    - Tooltip-style info: shows identity_similarity value on hover (via CSS `title` attribute)
    - The latest iteration marker should be slightly larger or have a ring to stand out
  - Insert the timeline section between the Live Status section and the KPI grid in `generate_html()` (after line ~278, before the KPI section)
  - Use the existing status-to-color mapping: `failed` → red, `passed` → green, `running` → orange, `plateau` → purple

  **Must NOT do**:
  - Do NOT add click handlers or JavaScript interactivity to timeline markers
  - Do NOT generate SVG — use pure HTML/CSS (divs with border-radius: 50%)
  - Do NOT show timeline with fewer than 2 iterations
  - Do NOT reorder existing sections — insert timeline as a new section between Live Status and KPI grid

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: CSS layout for timeline visualization
  - **Skills**: [`frontend-ui-ux`]
    - `frontend-ui-ux`: Visual timeline design with CSS

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (third task)
  - **Blocks**: Task 4
  - **Blocked By**: Tasks 1, 2

  **References**:

  **Pattern References**:
  - `factory/telemetry.py:264-268` — CSS class definitions for `.status-badge`, `.status-running`, `.status-passed`, `.status-failed`, `.status-plateau`. Use the same colors for timeline markers.
  - `factory/telemetry.py:109-113` — `phase_colors` dict in `_live_status_section`. Similar color mapping for timeline.
  - `factory/telemetry.py:354-376` — Iteration history table loop. Same data iteration pattern for timeline markers.

  **API/Type References**:
  - `factory/iteration_log.jsonl` — Each entry has `iteration_number`, `status`, `metrics_summary.identity_similarity`

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: Timeline renders with 2+ iterations
    Tool: Bash
    Preconditions: factory/iteration_log.jsonl has 2 entries
    Steps:
      1. python factory/telemetry.py
      2. grep 'timeline' factory/telemetry.html
      3. Assert: output contains timeline-related class or element
      4. grep -c 'timeline-marker' factory/telemetry.html
      5. Assert: count ≥ 2 (one per iteration)
    Expected Result: Timeline section with 2 markers present
    Evidence: grep output

  Scenario: Timeline hidden with 0-1 iterations
    Tool: Bash
    Preconditions: None
    Steps:
      1. mv factory/iteration_log.jsonl factory/iteration_log.jsonl.bak
      2. python factory/telemetry.py
      3. grep -c 'timeline' factory/telemetry.html
      4. Assert: count is 0 or only in CSS definition (no rendered timeline markers)
      5. mv factory/iteration_log.jsonl.bak factory/iteration_log.jsonl
    Expected Result: No timeline rendered when no iterations exist
    Evidence: grep output

  Scenario: All existing sections preserved after timeline addition
    Tool: Bash
    Preconditions: None
    Steps:
      1. python factory/telemetry.py
      2. grep -c '<h2>' factory/telemetry.html
      3. Assert: count ≥ 5 (Video Outputs, Latest Swap Output, Iteration History, Latest Iteration Details, Multi-Source Test, Previous Runs)
    Expected Result: All original section headers intact
    Evidence: grep count
  ```

  **Evidence to Capture:**
  - [x] grep counts for timeline markers
  - [x] grep count for preserved `<h2>` headers

  **Commit**: YES
  - Message: `feat(factory): add horizontal iteration timeline to telemetry dashboard`
  - Files: `factory/telemetry.py`
  - Pre-commit: `python factory/telemetry.py`

---

- [x] 4. Final Verification + Regeneration

  **What to do**:
  - Run `python factory/telemetry.py` to regenerate `factory/telemetry.html`
  - Open the generated HTML in a browser via Playwright and take screenshots
  - Verify all three design elements are visually present: compact KPI grid, pulse animations, iteration timeline
  - Verify the dark theme is intact (background #1a1a1a)
  - Verify the zero-iteration edge case (temporarily rename `iteration_log.jsonl`, regenerate, screenshot, restore)
  - Verify no new imports were added beyond stdlib

  **Must NOT do**:
  - Do NOT modify any code in this task — verification only
  - Do NOT add new features during verification

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Pure verification task, no code changes
  - **Skills**: [`playwright`]
    - `playwright`: Browser verification and screenshot capture

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (final task)
  - **Blocks**: None
  - **Blocked By**: Tasks 1, 2, 3

  **References**:

  **Pattern References**:
  - `factory/telemetry.html` — The generated output file to verify
  - `factory/telemetry.py` — Should still be runnable with `python factory/telemetry.py`

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: Full dashboard renders in browser
    Tool: Playwright (playwright skill)
    Preconditions: factory/telemetry.html exists (regenerated by prior tasks)
    Steps:
      1. Navigate to: file:///Users/kendrick/Documents/dev/watserface/factory/telemetry.html
      2. Wait for: body visible (timeout: 5s)
      3. Assert: page title contains "Factory Quality Iteration Loop"
      4. Assert: h1 text contains "Factory Quality Iteration Loop"
      5. Assert: body background-color is rgb(26, 26, 26) (#1a1a1a)
      6. Assert: element with class "kpi-grid" is visible
      7. Assert: at least one element contains "↑" or "↓" or "→" (delta arrows)
      8. Assert: element with class containing "timeline" is visible
      9. Screenshot: .sisyphus/evidence/task-4-dashboard-full.png
    Expected Result: Dashboard loads with all three design elements visible
    Evidence: .sisyphus/evidence/task-4-dashboard-full.png

  Scenario: Dark theme colors verified
    Tool: Playwright (playwright skill)
    Preconditions: factory/telemetry.html exists
    Steps:
      1. Navigate to: file:///Users/kendrick/Documents/dev/watserface/factory/telemetry.html
      2. Evaluate: getComputedStyle(document.body).backgroundColor
      3. Assert: result is "rgb(26, 26, 26)"
      4. Evaluate: getComputedStyle(document.querySelector('h1')).color
      5. Assert: result contains blue channel (the #4fc3f7 accent)
      6. Screenshot: .sisyphus/evidence/task-4-dark-theme.png
    Expected Result: Dark theme colors are intact
    Evidence: .sisyphus/evidence/task-4-dark-theme.png

  Scenario: No new external dependencies added
    Tool: Bash
    Preconditions: None
    Steps:
      1. head -15 factory/telemetry.py
      2. Assert: imports are only from stdlib (base64, json, os, datetime, pathlib)
      3. Assert: no pip-installable packages imported
    Expected Result: Only stdlib imports
    Evidence: head output

  Scenario: HTML generation succeeds
    Tool: Bash
    Preconditions: None
    Steps:
      1. python factory/telemetry.py
      2. Assert: exit code 0
      3. Assert: "Telemetry dashboard updated" in stdout
      4. ls -la factory/telemetry.html
      5. Assert: file exists and size > 0
    Expected Result: HTML generates without error
    Evidence: stdout + ls output
  ```

  **Evidence to Capture:**
  - [x] Screenshots in .sisyphus/evidence/task-4-dashboard-full.png
  - [x] Screenshots in .sisyphus/evidence/task-4-zero-state.png
  - [x] Terminal output from python and grep commands

  **Commit**: NO (verification only, no code changes)

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 1 | `feat(factory): compact KPI grid layout with delta trend arrows` | factory/telemetry.py | python factory/telemetry.py |
| 2 | `feat(factory): add CSS pulse animations and heartbeat indicator to dashboard` | factory/telemetry.py | python factory/telemetry.py |
| 3 | `feat(factory): add horizontal iteration timeline to telemetry dashboard` | factory/telemetry.py | python factory/telemetry.py |
| 4 | — | — | Playwright screenshots |

---

## Success Criteria

### Verification Commands
```bash
python factory/telemetry.py  # Expected: "Telemetry dashboard updated: ..."
grep 'kpi-grid' factory/telemetry.html  # Expected: class present
grep -oE '[↑↓→]' factory/telemetry.html | wc -l  # Expected: ≥ 2
grep '@keyframes pulse' factory/telemetry.html  # Expected: keyframe defined
grep 'timeline' factory/telemetry.html  # Expected: timeline elements present
grep -c '<h2>' factory/telemetry.html  # Expected: ≥ 5 (all sections preserved)
grep 'background: #1a1a1a' factory/telemetry.html  # Expected: dark theme present
```

### Final Checklist
- [x] All "Must Have" present (grid, deltas, pulse, timeline)
- [x] All "Must NOT Have" absent (no JS frameworks, no SVG, no mobile queries, no template engine, no new deps)
- [x] Zero-iteration edge case works
- [x] Single-iteration edge case works (KPIs shown, no deltas, no timeline)
- [x] Multi-source section `.metric` styling unchanged
- [x] Playwright screenshots captured as evidence
