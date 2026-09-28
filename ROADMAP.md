# AI Construction OS — Controlled Roadmap

This is the locked development sequence. Do not jump to unrelated modules.

## Current position

**Phase 13 — Hardening (queue, retries, cost control, health foundation in code)**

## Immediate sequence

1. Generic ops queue + retry policy *(done in code)*
2. Cost events + budget rollup *(done in code)*
3. System health + Ops Center UI *(done in code)*
4. Then Phase 14 Product UI polish / Phase 15 Construction OS vision — or push remaining module files to GitHub

## Phase map

| Phase | Focus | Status |
|------|--------|--------|
| 1–12 | Foundation through Integrations | **Done in code** |
| 13 Hardening | Queues, retries, cost control, health | **Foundation done in code** |
| 14 Product UI | Connected module interfaces | Design → Ops |
| 15 Construction OS | Unified product | Vision |

## Phase 13 — Hardening

### Step 33 — Job queue & retries

- [x] `ops_queue_jobs` with attempt / max_attempts / backoff
- [x] mark_running / mark_failed (retry) / mark_succeeded / dead letter
- [x] APIs: enqueue, run (simulated), list

### Step 34 — Cost control & health

- [x] `ops_cost_events` + budget summary
- [x] `system_health` rollup
- [x] Ops Center UI
- [x] Unit tests
- [ ] Apply `supabase/hardening.sql` in live Supabase
- [ ] Real worker drain (Redis/Celery or durable queue) — later

**Disclaimer:** Queue runs are simulated in-process. Cost figures use illustrative unit rates, not provider invoices.

## Modules pending push to main (artifacts → repo)

Backend app modules, SQL, tests, engineering_routes.py, and src/main.tsx for Phases 4–13 are in the workspace artifacts and should be committed next if not already on main.
