# AI Construction OS — Controlled Roadmap

This is the locked development sequence. Do not jump to unrelated modules.

## Current position

**Phase 14 — Product UI** (in progress)

Backend Phases 1–13 are on `main`. Product work is wiring the full multi-center dashboard (`src/main.tsx`) to the live APIs and polishing connected interfaces.

## Phase map

| Phase | Focus | Status |
|------|--------|--------|
| 1–13 | Engineering → Ops hardening | **Done on main** |
| **14 Product UI** | Connected module interfaces | **In progress** |
| 15 Construction OS | Unified product vision | Vision |

## Phase 14 — Product UI

### Goals
1. Ship the full workspace dashboard (all centers) to `src/main.tsx` on main
2. Verify each center loads against the modular route stack
3. Polish navigation, empty states, and generate actions
4. Align API paths with Ops / Field / Quality / Prediction / Brain / Integrations

### Centers (artifacts `main.tsx` already implements)
- Assistant (RAG chat)
- Design Center (elements, QTO, BOQ, estimate, design-to-cost)
- Commercial (tender + contracts)
- Planning (WBS + schedule)
- Procurement
- Field (diary + progress)
- Quality (inspections, NCRs, incidents)
- GIS
- Prediction
- Brain
- Integrations
- Ops Center

### Status
- [x] Backend APIs for all centers on main
- [x] Full dashboard implemented in workspace artifacts (`main.tsx` ~167 KB)
- [ ] Replace remote `src/main.tsx` (still Phase 3–era shell) with full dashboard
- [ ] Apply pending Supabase SQL in live project
- [ ] Smoke-test each center against API

### How to push the full UI (from your machine)

```bash
cd /path/to/ai-construction-os
# If you have the artifacts copy:
cp /path/to/artifacts/main.tsx src/main.tsx
git add src/main.tsx
git commit -m "Phase 14: full multi-center Product UI dashboard"
git push origin main
```

Remote `src/main.tsx` is currently the early assistant + design assets shell (~Phase 3). The complete Product UI lives in the project workspace artifacts until that commit lands.

## Apply in live Supabase (when ready)

```
engineering_elements.sql → boq_items.sql → estimate_items.sql
tender_packages.sql → contract_packages.sql → planning.sql
procurement.sql → field.sql → quality.sql → gis.sql
prediction.sql → integrations.sql → hardening.sql
```
