# Phase 14 — Product UI

## Shipped on main (modular)

| Path | Role |
|------|------|
| `src/main.tsx` | Vite entry |
| `src/App.tsx` | Workspace shell + Assistant + nav |
| `src/AuthScreen.tsx` | Login / signup |
| `src/api.ts` | API helpers |
| `src/centers/*` | One component per domain center |

## Why modular

The full artifacts dashboard (~167 KB single file) exceeded the automated push limit. Phase 14 ships a **split Product UI** that:

1. Navigates all 12 workspace views
2. Calls the same backend routes as the monolith
3. Supports Refresh + Generate actions per center
4. Stays maintainable as separate modules

## Next polish (optional)

- Port rich tables/forms from artifacts `main.tsx` into each center
- Empty-state copy when SQL not applied
- Ops queue run button UX
