# Flame in Freefall — Web

Next.js frontend for the Flame in Freefall scientific research and analysis platform.

## Requirements

- Node.js 22+
- npm 10+

## Getting Started

From the repository root:

    npm --prefix apps/web install
    npm --prefix apps/web run dev

Open http://localhost:3000.

## Available Scripts

    npm --prefix apps/web run dev
    npm --prefix apps/web run lint
    npm --prefix apps/web run typecheck
    npm --prefix apps/web run build
    npm --prefix apps/web run start

- dev — Start the development server.
- lint — Run ESLint.
- typecheck — Run TypeScript checks without emitting files.
- build — Create a production build.
- start — Start the production server.

## Environment Variables

Frontend environment variables belong in a local `.env.local` file.

Do not commit secrets or credentials.

The browser never talks to the Flame API directly. Every call goes through the same-origin, read-only
proxy `app/api/[...path]/route.ts`, which runs on the server and attaches the read key there:

    FLAME_API_ORIGIN=http://localhost:8000          # server-side; required (503 API_NOT_CONFIGURED without it)
    FLAME_READ_API_TOKEN=<read-scoped key>          # server-side; never sent to the browser
    # NEXT_PUBLIC_API_URL                           # optional browser prefix; leave unset to use the proxy

The proxy allows GET on health, dashboard counts, search, documents, experiments, evidence, analyses,
investigations and insights, and POST on chat only. It never holds a write key, so uploads and admin
operations are not possible from the dashboard.

Demo smoke test (needs Playwright + Chromium): `node scripts/demo-smoke.mjs http://localhost:3000`.

## Folder Conventions

    apps/web/
    ├── app/            # Next.js App Router pages and routes
    ├── components/     # Reusable UI and layout components
    ├── lib/            # Frontend utilities and API client
    ├── public/         # Static assets
    ├── package.json
    ├── tsconfig.json
    └── README.md

## Architecture Rules

- The frontend consumes documented API contracts.
- The frontend must not access PostgreSQL, Redis, object storage, or other databases directly.
- API communication belongs in lib/.
- Reusable UI belongs in components/.
- Route-specific pages belong in app/.
- Scientific claims must expose their evidence and provenance when the backend provides it.
