# Live smoke test — AI Construction OS

**Production**

| Layer | URL |
|-------|-----|
| App | https://ai-costruction-os.vercel.app |
| API | https://ai-construction-os-backend.onrender.com |

Verified programmatically (2026-09-29):

- `GET /health` → `ok` (v0.3.0)
- `GET /health/database` → `connected`
- OpenAPI → **66 routes** (engineering through OS)
- `GET /api/v1/os/modules` without token → **401** (auth gate OK)

---

## A. Auth & project (2 min)

1. Open the app → **Login** or **Create account**
2. **+ New project** (name + optional code)
3. Confirm project appears in the selector

**Pass:** session stays after refresh; project is selected.

---

## B. OS Home (Phase 15)

1. Sidebar → **OS Home** (default after project select)
2. Click **Refresh**
3. Note **Readiness** and module statuses

| Status | Meaning |
|--------|---------|
| `active` | Table has rows |
| `empty` | Schema OK, no data yet |
| `needs_setup` | Apply matching `supabase/*.sql` |
| `error` | API / RLS issue |

**Pass:** snapshot loads; recommended actions list is non-empty.

---

## C. Document → Design chain

1. **Upload document** (PDF drawing or spec preferred)
2. Wait for processing (status / notice)
3. **Design** center → **Refresh**
4. If elements exist → **Generate BOQ** → **Generate estimate**

**Pass:** upload succeeds; elements and/or BOQ preview appear (or clear SQL warning).

---

## D. Commercial & Planning

1. **Commercial** → **Generate tender packages** (needs estimate chain)
2. **Planning** → **Generate WBS** / **Generate schedule**

**Pass:** generate returns data or a clear setup warning — not a blank 500.

---

## E. Field → Prediction → Ops

1. **Field** / **Quality** / **GIS** → Refresh
2. **Prediction** → **Generate risks & forecasts**
3. **Brain** → Refresh insights
4. **Ops** → summary / queue / health

**Pass:** each center responds; OS Home readiness may move toward `forming` / `operational` as data accumulates.

---

## F. Assistant

1. **Assistant** → ask: *"What documents are in this project?"*
2. Confirm answer and any **Sources**

**Pass:** response returns (even if knowledge is thin on a new project).

---

## If something fails

| Symptom | Action |
|---------|--------|
| `needs_setup` everywhere | Run SQL files in [DEPLOY.md](DEPLOY.md) order |
| CORS / network error | Confirm Vercel origin in Render `CORS_ORIGINS` |
| API timeout first request | Render free tier cold start — retry once |
| Auth loop | Supabase Site URL + Redirect URLs include Vercel URL |
| 500 on generate | Check Render logs; often missing table |

---

## Done when

- [ ] Login works
- [ ] OS Home loads
- [ ] At least one document uploaded
- [ ] Design generate path attempted
- [ ] One commercial or planning generate attempted
- [ ] Assistant answers once
