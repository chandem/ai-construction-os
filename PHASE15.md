# Phase 15 — Construction OS Vision

## Purpose

Phases 1–14 built **domain modules** and a **Product UI**. Phase 15 defines the **Construction OS** layer: one operating view of the project above modules.

```
Documents + Domain modules
        ↓
  Construction OS kernel
        ↓
  Readiness · Actions · Health
        ↓
  Team decisions (human control)
```

## Principles

1. **Project is the unit of operation**
2. **Modules remain independent** — OS composes, does not replace
3. **Readiness over vanity metrics** — empty / needs_setup / active
4. **Recommended actions are advisory**
5. **Evidence stays in modules**

## Shipped foundation

| Artifact | Role |
|----------|------|
| `backend/app/construction_os.py` | Registry, readiness, actions, snapshot |
| `backend/app/routes_construction_os.py` | `GET .../os/snapshot`, `GET /os/modules` |
| `src/centers/OsHome.tsx` | OS home panel |
| `backend/tests/test_construction_os.py` | Unit tests |

## API

- `GET /api/v1/projects/{id}/os/snapshot`
- `GET /api/v1/os/modules`

## Beyond this foundation

- OS home as default landing after project select
- Cross-module work queues (approvals, NCRs, delays)
- Role-based homes (PM / QS / site)
- Org packaging, audit exports
- Production queue workers (Phase 13 follow-on)

## Non-goals

- Replacing domain UIs
- Autonomous decisions without human review
- New commercial pricing engine
