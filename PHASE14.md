# Phase 14 — Product UI

## Why this phase

Phases 1–13 delivered the engineering → commercial → field → intelligence → ops **backend** on GitHub. Phase 14 connects operators to that stack through one workspace UI.

## Current gap

| Location | `src/main.tsx` |
|----------|----------------|
| GitHub `main` | Early shell: auth, projects, documents, design assets, RAG chat |
| Workspace artifacts | Full Product UI: 12 workspace views + Design Center tabs |

## Product UI surface (full dashboard)

| View | Primary APIs |
|------|----------------|
| Assistant | `/ai/chat`, conversations |
| Design Center | `/engineering/elements`, `quantities`, `boq`, `estimate`, `design-to-cost` |
| Commercial | `/commercial/summary`, `/tender/packages`, `/contracts` |
| Planning | `/planning/wbs`, `/planning/schedule` |
| Procurement | `/procurement/summary`, generate |
| Field | `/field/summary`, diary, progress |
| Quality | `/quality/summary`, inspections, NCRs, incidents |
| GIS | `/gis/summary`, assets from elements |
| Prediction | `/prediction/summary`, generate |
| Brain | `/brain/insights` |
| Integrations | `/integrations/summary` |
| Ops | `/ops/summary`, queue, cost, health |

## Acceptance criteria

1. Full dashboard committed to `src/main.tsx` on main
2. Sidebar navigates all centers without dead ends
3. Generate/load actions match route modules on backend
4. Empty states explain missing Supabase tables when SQL not applied
5. Ops Center reflects queue + cost + health from Phase 13

## Next actions

1. Push artifacts `main.tsx` → `src/main.tsx` (local git recommended; file ~167 KB)
2. Apply SQL pack in Supabase
3. Smoke-test one project through Design → Commercial → Planning → Field → Ops
4. Optional: split `main.tsx` into `src/centers/*` components for maintainability
