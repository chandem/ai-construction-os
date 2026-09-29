# AI Construction OS — Controlled Roadmap

## Current position

**Phases 1–15 foundation complete on `main`.**

## Phase map

| Phase | Focus | Status |
|------|--------|--------|
| 1–13 | Engineering → Ops hardening | **Done** |
| 14 | Product UI (modular centers) | **Done** |
| **15** | Construction OS vision + kernel | **Foundation done** |

## Phase 15 — Construction OS

- [x] `construction_os.py` — module registry, readiness, recommended actions
- [x] `GET /api/v1/projects/{id}/os/snapshot`
- [x] `GET /api/v1/os/modules`
- [x] `OsHome` workspace panel
- [x] Unit tests
- [ ] Default landing = OS home (optional UX)
- [ ] Role-based homes / work queues (later)

## Operational checklist

1. Apply all `supabase/*.sql` in live Supabase
2. Smoke-test OS snapshot + Design → Ops chain
3. Optional: richer center tables from artifacts monolith
4. Optional: production queue workers
