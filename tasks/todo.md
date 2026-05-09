# EKGTrainer Tasks

## Current Sprint

- [ ] **Replace EKG images** — Current images not in correct sections (cases assigned to wrong rhythm categories). New images needed before fixing categorization.
- [ ] **Generalize rhythm classifier (multi-class, all-comers)** — Add slice-aware evaluation, improve features/constraints (patterned irregularity vs AF, VF/ASYS guards), add training script + regression tests/CI to prevent backsliding.

## Backlog

Standby for next prioritization.

## Completed

- [x] **Testing P0–P4** — Vitest data invariants, analyze assembly (`web/src/lib/analyzeAssembly.ts`), rate limit factory + quiz API tests; pytest `server.py` (401/403/413/429); golden snapshot `nsr_01`; Playwright smoke; GitHub Actions CI; Python fix: preserve `HTTPException` from size check (no false 400).
- [x] Removed Claude/Anthropic from app + Python pipeline; interpretation is signal/rule assembly only (`claude_prompt` and `@anthropic-ai/sdk` gone).
- [x] Beginner systematic lesson slug aligned with content validation: `15-systematic-approach.mdx`, route `/learn/beginner/15-systematic-approach`.
- [x] Security hardening: server-side quiz API (opaque IDs, answer not sent to client until after submission)
- [x] Security hardening: removed internal Python service URL from API error responses
- [x] Security hardening: image filenames concealed via opaque image proxy route
- [x] Production build passing (52/52 pages, 0 TypeScript errors; web Vitest 31 tests)

## Review — testing sprint

| Area | Notes |
|------|--------|
| Precompute gap | 11 case IDs documented in `web/tests/data-invariants.test.ts` (`CASE_IDS_PENDING_PRECOMPUTE`); remove entries as `measurements.json` gains rows. |
| E2E | `npm run build` required before `npm run test:e2e` when `.next` missing; CI runs build first. |
| Vitest count | 31 tests in `web` (includes content validation + new suites). |
