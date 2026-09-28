# AI Construction OS — Controlled Roadmap

This is the locked development sequence. Do not jump to unrelated modules.

## Current position

**Phase 3 — Design & Engineering, Step 14 complete in code: QTO + BOQ + Estimate + Design-to-cost**

Already in place: foundation, documents, RAG, AI extraction, design assets, AI design review, visual drawing analysis, engineering elements, deterministic quantity takeoff, proposed BOQ, provisional estimate, design-to-cost intelligence (drivers, concentration, scenarios).

## Immediate sequence

1. Engineering elements *(done in code)*
2. Quantity extraction *(done in code)*
3. BOQ linkage *(done in code — apply SQL next)*
4. Estimate linkage *(done in code — apply SQL next)*
5. Design-to-cost intelligence *(done in code)*
6. Background AI processing
7. Design Center UI
8. Then Tender / Commercial (Phase 4)

## Why this order

Drawing → element → quantity → BOQ → estimate → design-to-cost creates an engineering-to-commercial chain. Isolated screens without that chain are not the OS.

## Phase map

| Phase | Focus | Status |
|------|--------|--------|
| 1 Foundation | Architecture, orgs, users, security | Core done |
| 2 Documents & AI | Upload, extract, embed, RAG | Core done |
| 3 Design & Engineering | Assets, review, vision, elements, QTO, BOQ, estimate, **D2C** | In progress |
| 4 Tender & Commercial | Tender, estimate, contract, cost | Not started |
| 5 Planning | WBS, schedule, delay intelligence | Not started |
| 6 Procurement & resources | Materials, equipment, workforce | Not started |
| 7 Field | Site diary, progress, field AI | Not started |
| 8 Quality & safety | Inspections, NCRs, incidents | Not started |
| 9 GIS | Locations, infrastructure assets | Not started |
| 10 Prediction | Risk and forecasts | Not started |
| 11 Central AI brain | Cross-domain reasoning | Partial (RAG only) |
| 12 Integrations | P6, BIM, Drive, ERP | Not started |
| 13 Hardening | Queues, retries, tests, cost control | Partial tests |
| 14 Product UI | Connected module interfaces | Early workspace |
| 15 Construction OS | Unified product | Vision |

## Step 13 — Engineering elements

- [x] Canonical element types
- [x] Normalize AI / vision output into structured rows
- [x] Persist `engineering_elements` linked to project + design asset + document
- [x] List APIs by project and by design asset
- [x] Unit tests for classification and de-duplication
- [ ] Apply `supabase/engineering_elements.sql` in the live Supabase project
- [ ] Design Center UI listing elements

## Step 14 — Quantity extraction

- [x] Deterministic quantity rules by element type (area, volume, length, count)
- [x] Enrich elements at normalize time (`quantity_method`, confidence, notes)
- [x] Aggregate takeoff summary API
- [x] Unit tests for QTO rules

## Step 14b — BOQ linkage

- [x] Map element type + unit → work section, item code, description template
- [x] Aggregate takeoff into proposed BOQ lines with source element traceability
- [x] APIs: preview BOQ, generate+persist, list stored items
- [x] Unit tests for BOQ build
- [ ] Apply `supabase/boq_items.sql` in the live Supabase project

## Step 14c — Estimate linkage

- [x] Provisional unit rates by element type (design-to-cost exploration only)
- [x] Apply rates to BOQ lines → amount, currency, rate_source
- [x] Estimate summary totals by work section
- [x] APIs: preview estimate, generate+persist, list stored items
- [x] Unit tests for rate application and totals
- [ ] Apply `supabase/estimate_items.sql` in the live Supabase project

## Step 14d — Design-to-cost intelligence

- [x] Cost drivers ranked by amount and share of total
- [x] Work-section concentration
- [x] Pareto insight (lines needed for ~80% of cost)
- [x] Design levers (priority attention by share)
- [x] Quantity ±% and rate what-if scenarios on top drivers
- [x] API: `GET /projects/{id}/engineering/design-to-cost`
- [x] Unit tests
- [ ] Background AI processing (next)
- [ ] Design Center UI

Quantities, BOQ lines, estimate amounts, and design-to-cost figures are **proposed values** for professional review. They are not certified tender items or market prices.
