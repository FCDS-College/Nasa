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

The API base URL will be added here once the backend API contract is finalized.

Example:

    NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

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
