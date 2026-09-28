# AI Construction OS — Controlled Roadmap

This is the locked development sequence. Do not jump to unrelated modules.

## Current position

**Phase 3 — Design & Engineering: Step 14 chain + background AI processing (in code)**

Already in place: foundation, documents, RAG, AI extraction, design assets, AI design review, visual drawing analysis, engineering elements, QTO, BOQ, estimate, design-to-cost, **background document AI pipeline**.

## Immediate sequence

1. Engineering elements *(done in code)*
2. Quantity extraction *(done in code)*
3. BOQ linkage *(done in code — apply SQL next)*
4. Estimate linkage *(done in code — apply SQL next)*
5. Design-to-cost intelligence *(done in code)*
6. Background AI processing *(done in code)*
7. Design Center UI
8. Then Tender / Commercial (Phase 4)

## Why this order

Drawing → element → quantity → BOQ → estimate → design-to-cost creates an engineering-to-commercial chain. Background jobs keep upload responsive while that chain runs.

## Phase map

| Phase | Focus | Status |
|------|--------|--------|
| 1 Foundation | Architecture, orgs, users, security | Core done |
| 2 Documents & AI | Upload, extract, embed, RAG | Core done |
| 3 Design & Engineering | Assets, review, vision, elements, QTO, BOQ, estimate, D2C, **jobs** | In progress |
| 4 Tender & Commercial | Tender, estimate, contract, cost | Not started |
| 5 Planning | WBS, schedule, delay intelligence | Not started |
| 6 Procurement & resources | Materials, equipment, workforce | Not started |
| 7 Field | Site diary, progress, field AI | Not started |
| 8 Quality & safety | Inspections, NCRs, incidents | Not started |
| 9 GIS | Locations, infrastructure assets | Not started |
| 10 Prediction | Risk and forecasts | Not started |
| 11 Central AI brain | Cross-domain reasoning | Partial (RAG only) |
| 12 Integrations | P6, BIM, Drive, ERP | Not started |
| 13 Hardening | Queues, retries, tests, cost control | Partial (bg jobs + tests) |
| 14 Product UI | Connected module interfaces | Early workspace |
| 15 Construction OS | Unified product | Vision |

## Step 14d — Design-to-cost intelligence

- [x] Cost drivers, concentration, Pareto, levers, scenarios
- [x] API: `GET /projects/{id}/engineering/design-to-cost`

## Step 14e — Background AI processing

- [x] Extract document AI pipeline into `document_pipeline.py`
- [x] Schedule via FastAPI BackgroundTasks (`background_jobs.py`)
- [x] Upload returns `queued` immediately; job progresses to processing/completed/failed
- [x] Status API enriched (`is_terminal`); list project jobs
- [x] Reprocess endpoint (re-download from storage + re-queue)
- [x] Unit tests for job helpers and safe failure path
- [ ] Design Center UI (next)

Quantities, BOQ lines, estimate amounts, and design-to-cost figures remain **proposed** for professional review.
