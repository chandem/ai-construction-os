# AI Construction OS — Controlled Roadmap

This is the locked development sequence. Do not jump to unrelated modules.

## Current position

**Phase 3 — Design & Engineering, Step 14: Quantity extraction**

Already in place: foundation, documents, RAG, AI extraction, design assets, AI design review, visual drawing analysis, engineering elements.

## Immediate sequence

1. Engineering elements *(done in code)*
2. Quantity extraction *(in progress)*
3. BOQ linkage
4. Estimate linkage
5. Design-to-cost intelligence
6. Background AI processing
7. Design Center UI
8. Then Tender / Commercial (Phase 4)

## Why this order

Drawing → element → quantity → BOQ → estimate creates an engineering-to-commercial chain. Isolated screens without that chain are not the OS.

## Phase map

| Phase | Focus | Status |
|------|--------|--------|
| 1 Foundation | Architecture, orgs, users, security | Core done |
| 2 Documents & AI | Upload, extract, embed, RAG | Core done |
| 3 Design & Engineering | Assets, review, vision, elements, **QTO** | In progress |
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
- [ ] BOQ linkage (next)

Quantities are **proposed takeoff values** for professional review. They are not certified BOQ items.
