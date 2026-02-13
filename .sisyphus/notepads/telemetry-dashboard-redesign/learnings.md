# Learnings — Telemetry Dashboard Redesign

## 2026-02-12 Task 1-4: Full Redesign

### Conventions
- `factory/telemetry.py` generates static HTML via Python f-string concatenation — no template engine
- The `.metric` CSS class is shared between KPI section and multi-source section — always use new classes for new layouts
- HTML auto-refreshes every 5s via `<meta http-equiv="refresh" content="5">` — CSS animations restart each cycle (must be stateless)

### Decisions
- Used `.kpi-grid` / `.kpi-cell` instead of modifying `.metric` to avoid breaking multi-source section
- Delta thresholds: identity ±0.01, SSIM ±0.005, cost ±$0.01 — below threshold shows → (flat)
- Animations restricted to `opacity` and `transform` only (GPU-composited, no layout thrash)
- Timeline only renders with 2+ iterations, capped at 15 markers
- Heartbeat dot uses stale detection (>5 min = gray, no pulse)

### Issues
- Gemini agent (visual-engineering) went into an infinite self-validation loop on Task 3 — produced correct output but wasted ~7 minutes on nonsensical "attribute validation". The actual code changes were done in the first ~30 seconds.
- Poll timeout on Task 2 (600s) but work was already complete — always verify output independently of task completion status
