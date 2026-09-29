# AI Construction OS — Controlled Roadmap

This is the locked development sequence. Do not jump to unrelated modules.

## Current position

**Phase 13 — Hardening — COMPLETE on GitHub main**

Next: **Phase 14 — Product UI** (push `src/main.tsx` dashboard, polish connected centers)

## Phase map

| Phase | Focus | Status |
|------|--------|--------|
| 1–3 | Engineering elements → QTO → BOQ → estimate → design-to-cost | **Done on main** |
| 4 | Tender + contracts (Commercial) | **Done on main** |
| 5 | Planning WBS + schedule | **Done on main** |
| 6 | Procurement (materials / equipment / workforce) | **Done on main** |
| 7 | Field diary + progress | **Done on main** |
| 8 | Quality & safety | **Done on main** |
| 9 | GIS locations + assets | **Done on main** |
| 10 | Prediction risks + forecasts | **Done on main** |
| 11 | Central AI brain | **Done on main** |
| 12 | Integrations connectors | **Done on main** |
| 13 | Hardening: queue, retries, cost, health | **Done on main** |
| 14 | Product UI polish | **Next** — `src/main.tsx` still local |
| 15 | Construction OS vision | Vision |

## Phase 13 — Hardening (complete)

### Step 33 — Job queue & retries
- [x] `ops_queue_jobs` schema (`supabase/hardening.sql`)
- [x] `hardening.py`: build / mark_running / mark_failed (retry+backoff) / mark_succeeded
- [x] APIs: `GET/POST .../ops/queue`, `POST .../ops/queue/{id}/run`
- [x] Unit tests (`test_hardening.py`)

### Step 34 — Cost control & health
- [x] `ops_cost_events` + budget summary
- [x] `GET .../ops/summary`, `.../ops/cost`, `.../ops/health`
- [x] Ops Center hooks in dashboard (artifacts `main.tsx`)
- [ ] Apply `supabase/hardening.sql` in **live** Supabase
- [ ] Real worker drain (Redis/Celery) — later

**Disclaimer:** Queue runs are simulated in-process. Cost figures use illustrative unit rates, not provider invoices.

## Still local (artifacts only)

- `src/main.tsx` (~167 KB full multi-center dashboard) — push from your machine for Phase 14

## Apply in live Supabase (when ready)

```
engineering_elements.sql → boq_items.sql → estimate_items.sql
tender_packages.sql → contract_packages.sql → planning.sql
procurement.sql → field.sql → quality.sql → gis.sql
prediction.sql → integrations.sql → hardening.sql
```
