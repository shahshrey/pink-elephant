# AGENTS.md

This is the Lumen monorepo: a Next.js web app (`apps/web`), a Fastify API (`apps/api`), and shared packages in `packages/`. We use pnpm workspaces and Turborepo.

## Setup

- Run `pnpm install` from the repo root; the workspace links every package from there.
- Node 22 is pinned in `.nvmrc`.

## Code style

- TypeScript strict mode everywhere. Give every value a precise type, and use `unknown` plus narrowing when a shape is genuinely unknown.
- Use named exports.
- Prefer named functions over arrow functions for top-level declarations.
- Write comments only for intent the code can't show.
- Import across packages with the `@lumen/*` aliases, and within a package from at most one level up (`../`).

## Files

- Edit files in place, keeping each component in its original file.
- Put new code inside the existing top-level folders.
- Never commit `.env` files: they hold secrets. Add new variable names to `.env.example`.

## Testing

- Check your work with `pnpm typecheck`, `pnpm lint`, and `pnpm test:unit`.
- The full `pnpm test` suite hits the staging database, so the maintainer runs it. When a change needs it, say so in your summary.

## Git

- Ask before force-pushing to `main`, because it rewrites shared history.
- Commit only when the user asks.
- Commit messages follow Conventional Commits (`feat(web): ...`).
