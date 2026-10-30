# Fitzy frontend

React 18 + Vite + TypeScript PWA. Mobile-first, installable to the home screen, dark by default.

## Setup

Requires Node 20+ (CI and local dev use Node 22).

```bash
cd frontend
npm ci
cp .env.example .env.local   # optional; defaults already point at /api
```

## Develop

```bash
npm run dev        # http://localhost:5173
```

Requests to `/api/*` are proxied to the FastAPI backend on `http://localhost:8000` with the `/api`
prefix stripped, so `/api/health` hits `/health`. Start the backend first
(`cd backend && uv run uvicorn app.main:app --reload`); the Today tab shows "API ok" or
"API unreachable".

To test on a phone on the same network: `npm run dev -- --host`, then open the printed LAN URL.

## Check

```bash
npm run lint           # ESLint (flat config) + Prettier compatibility
npm run format:check   # Prettier
npm run typecheck      # tsc --noEmit for app and vite.config.ts
npm test -- --run      # Vitest + React Testing Library, single run (omit --run to watch)
```

## Build

```bash
npm run build      # type-checks, then writes the static site + service worker to dist/
npm run preview    # serve dist/ locally to try the installed PWA
```

`dist/` is plain static files and can be served from any static host. Set `VITE_API_URL` at build
time to the deployed API base URL (it is baked into the bundle; never put secrets in `VITE_*` vars).

## Layout

| Path                    | What                                                               |
| ----------------------- | ------------------------------------------------------------------ |
| `src/api/`              | Typed API client (`client.ts`) and TanStack Query hooks            |
| `src/components/`       | App shell pieces: tab bar, page frame, API status                  |
| `src/pages/`            | One component per tab: Today, Calendar, Progress, Coach            |
| `src/styles/tokens.css` | Design tokens (colours, type scale, spacing, touch sizes)          |
| `public/icons/`         | PWA icons (SVG source plus 192/512, maskable and Apple touch PNGs) |

## Design notes

- Each tab owns one competition bumper-plate colour (red, blue, yellow, green). That colour marks the
  active tab and the page heading, and is the only accent used.
- Touch targets are at least 48px; the tab bar is 68px tall plus the safe-area inset, sitting under
  the thumb for one-handed use.
- Numbers use Barlow Condensed (self-hosted via `@fontsource`, so it works offline) at large sizes so
  they read at arm's length mid-set.
