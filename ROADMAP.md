# AI Construction OS — Controlled Roadmap

## Current position

**Phase 14 — Product UI — modular dashboard on main**

Backend Phases 1–13 and a modular multi-center Product UI are on GitHub.

## Phase map

| Phase | Focus | Status |
|------|--------|--------|
| 1–13 | Engineering → Ops hardening | **Done on main** |
| **14 Product UI** | Connected module interfaces | **Modular UI on main** |
| 15 Construction OS | Unified product vision | Vision |

## Phase 14 — Product UI (modular)

### Layout on main

```
src/
  main.tsx              # entry
  App.tsx               # shell, nav, assistant, project/docs
  AuthScreen.tsx
  api.ts / types.ts / supabaseClient.ts
  centers/
    CenterPanel.tsx     # shared load/generate panel
    DesignCenter.tsx … OpsCenter.tsx
```

### Centers wired to backend APIs
Assistant · Design · Commercial · Planning · Procurement · Field · Quality · GIS · Prediction · Brain · Integrations · Ops

### Notes
- Center panels show live JSON from APIs (foundation UI). Richer tables/forms from artifacts `main.tsx` can be ported center-by-center.
- Apply Supabase SQL pack before expecting persisted rows.
- Full 167 KB monolith remains in workspace artifacts as reference for richer UX.

## Apply in live Supabase

```
engineering_elements.sql → boq_items.sql → estimate_items.sql
tender_packages.sql → contract_packages.sql → planning.sql
procurement.sql → field.sql → quality.sql → gis.sql
prediction.sql → integrations.sql → hardening.sql
```
