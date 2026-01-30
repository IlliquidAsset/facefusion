# Add Ralph QA Reference to AGENTS.md

## TL;DR

> **Quick Summary**: Add a reference to the Ralph Visual QA workflow in AGENTS.md
> 
> **Deliverables**:
> - Updated AGENTS.md with new section referencing `.sisyphus/workflows/ralph-visual-qa.md`
> 
> **Estimated Effort**: Quick
> **Parallel Execution**: NO - single task

---

## Context

### Original Request
User wants the Ralph Visual QA workflow documented in AGENTS.md so agents can discover and follow it.

### What Exists
- `.sisyphus/workflows/ralph-visual-qa.md` - Full workflow documentation (already created)
- `AGENTS.md` - Agent coordination document (needs reference added)

---

## Work Objectives

### Core Objective
Add a section to AGENTS.md that references the Ralph Visual QA workflow.

### Definition of Done
- [ ] AGENTS.md contains a "Ralph Visual QA Workflow" section
- [ ] Section includes trigger command `/ralph-qa`
- [ ] Section links to `.sisyphus/workflows/ralph-visual-qa.md`

---

## TODOs

- [ ] 1. Add Ralph QA section to AGENTS.md

  **What to do**:
  - Open `AGENTS.md`
  - Add the following section at the end of the file (after the Phase 2.5 section):

  ```markdown
  ---

  ## 🔍 Ralph Visual QA Workflow

  **Trigger:** `/ralph-qa` or `ralph-qa`

  After running tests that produce visual outputs, agents MUST follow this human-in-the-loop review process.

  ### Rules

  1. **Solve what you can solve** - Technical issues (artifacts, missing files, wrong dimensions) are fixed by the agent without asking
  2. **Ask only what requires human judgment** - Aesthetic quality, contextual fit, identity verification
  3. **One image at a time** - Present and discuss each image sequentially
  4. **One question at a time** - Don't overwhelm with multiple questions per image

  ### What to Ask Humans

  | Ask | Don't Ask |
  |-----|-----------|
  | "Does this skin tone look natural?" | "Should I fix this rectangular artifact?" |
  | "Is the identity preserved here?" | "The file is missing, should I regenerate?" |
  | "Is this blur level acceptable?" | "SSIM is 0.75, should I iterate?" |

  ### Full Workflow Documentation

  See `.sisyphus/workflows/ralph-visual-qa.md` for complete protocol.
  ```

  **Must NOT do**:
  - Do not modify any existing sections
  - Do not remove any content

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **References**:
  - `AGENTS.md` - Target file (append to end)
  - `.sisyphus/workflows/ralph-visual-qa.md` - Source workflow document

  **Acceptance Criteria**:
  - [ ] `grep -q "Ralph Visual QA" AGENTS.md` returns success
  - [ ] `grep -q "/ralph-qa" AGENTS.md` returns success
  - [ ] File still valid markdown (no syntax errors)

  **Commit**: YES
  - Message: `docs(agents): add Ralph Visual QA workflow reference`
  - Files: `AGENTS.md`

---

## Commit Strategy

| After Task | Message | Files |
|------------|---------|-------|
| 1 | `docs(agents): add Ralph Visual QA workflow reference` | AGENTS.md |

---

## Success Criteria

### Verification Commands
```bash
grep "Ralph Visual QA" AGENTS.md  # Should find the section
grep "/ralph-qa" AGENTS.md        # Should find the trigger
```
