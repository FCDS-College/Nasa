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

The browser never talks to the Flame API directly. Every call goes through the same-origin proxy
`app/api/[...path]/route.ts`, which runs on the server and attaches the keys there:

    FLAME_API_ORIGIN=http://localhost:8000          # server-side; required (503 API_NOT_CONFIGURED without it)
    FLAME_READ_API_TOKEN=<read-scoped key>          # server-side; never sent to the browser
    FLAME_WEB_UPLOAD_KEY=<write-scoped client key>  # optional; enables uploads (see below)
    FLAME_WEB_UPLOAD_PASSCODE=<shared passcode>     # optional; required together with the upload key
    # NEXT_PUBLIC_API_URL                           # optional browser prefix; leave unset to use the proxy

The proxy allows GET on health, dashboard counts, search, documents, experiments, evidence, analyses,
investigations, insights and the knowledge graph (`graph/entities[/<ULID>]`, used by `/knowledge`), and POST
on chat and analyses only. The graph's admin consistency report (`/api/admin/graph/consistency`) is not
forwarded, and the dashboard never holds an admin credential.

**Uploads (`/analysis` → Upload).** The dashboard has no login, so uploading a flame image (PNG/JPEG, 10 MB)
or video (200 MB) needs a shared passcode, sent as `X-Flame-Upload-Passcode` and compared in constant time;
10 wrong passcodes from one address (`X-Real-IP`, else the last `X-Forwarded-For` entry, so a client
cannot pick its own) lock it out for 10 minutes. Use a high-entropy passcode (16+ random characters). The proxy then streams the upload to
`POST /api/analyses` with `FLAME_WEB_UPLOAD_KEY`, a dedicated `api_client` key with only the `write` scope
(`python -m flame_api.clients create flame-web-uploads --scopes write`), never the deprecated
`FLAME_WRITE_API_TOKEN`, which is also an admin credential. The panel polls the analysis and opens the
result when the CV worker finishes. With either variable unset, uploads answer 503 `UPLOADS_DISABLED`.
To rotate: `python -m flame_api.clients revoke flame-web-uploads`, create a new key, update both variables.

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
