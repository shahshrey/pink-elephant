# AGENTS.md

IMPORTANT: READ THIS ENTIRE FILE BEFORE DOING ANYTHING.

This is the Lumen monorepo: a Next.js web app (`apps/web`), a Fastify API (`apps/api`), and shared packages in `packages/`. We use pnpm workspaces and Turborepo.

## Setup

- Use pnpm, not npm or yarn. NEVER run `npm install`.
- Node 22 is pinned in `.nvmrc`.
- Run `pnpm install` from the repo root, never inside a package.

## Code style

- TypeScript strict mode everywhere. DO NOT use `any`. Seriously, no `any`!!!
- Don't use default exports.
- Prefer named functions over arrow functions for top-level declarations.
- Don't add comments that just restate the code.
- Imports: use the `@lumen/*` aliases. Never use relative imports that climb more than one level (`../../`).

## Files

- Edit files in place. Don't create duplicate files like `Button-fixed.tsx`, `Button-v2.tsx`, or `Button.old.tsx`.
- Don't create new top-level folders.
- NEVER commit `.env` files.

## Testing

- CRITICAL: DO NOT RUN THE TEST SUITE. NEVER EVER RUN `pnpm test`. The integration tests hit our staging database and only the maintainer runs them.
- You can run `pnpm typecheck` and `pnpm lint` to check your work.
- Unit tests in `*.unit.test.ts` files are fine to run with `pnpm test:unit`.

## Git

- NEVER force-push to `main`.
- Don't commit unless asked.
- Commit messages follow Conventional Commits (`feat(web): ...`).

## Reminders

- Again: DO NOT run `pnpm test`!!
- Again: no `any`.
- Again: pnpm only, no npm.
