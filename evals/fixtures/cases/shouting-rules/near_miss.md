# AGENTS.md

This is the Lumen monorepo: a Next.js web app (`apps/web`), a Fastify API (`apps/api`), and shared packages in `packages/`. We use pnpm workspaces and Turborepo.

## Setup

- Use pnpm rather than npm or yarn.
- Node 22 is pinned in `.nvmrc`.
- Run `pnpm install` from the repo root.

## Code style

- TypeScript strict mode everywhere. Avoid `any`.
- Use named exports.
- Prefer named functions over arrow functions for top-level declarations.
- Skip comments that restate the code.
- Use the `@lumen/*` aliases for imports.

## Files

- Edit files in place instead of creating copies like `Button-v2.tsx`.
- Do not commit `.env` files.

## Testing

- Do not run `pnpm test`; the integration tests hit the staging database and the maintainer runs them.
- Check your work with `pnpm typecheck`, `pnpm lint`, and `pnpm test:unit`.

## Git

- Do not force-push to `main`.
- Commit only when the user asks.
- Commit messages follow Conventional Commits (`feat(web): ...`).
