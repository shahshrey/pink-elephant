---
title: Writing instructions for models
inclusion: always
---

# Writing instructions for models

These habits apply whenever you write or edit text that another model will follow: prompts, system prompts, skills, rules, `CLAUDE.md`, and `AGENTS.md`.

- Describe the behavior you want. Name the target with a number, a scope, or a concrete alternative: "Answer in under 100 words." "Cite sources from A, B, and C." "Verify changes with `npm run typecheck`."
- When asked to take something out of instruction text, delete every sentence about it, then rebuild the section from a short brief of what the text covers now. The finished section reads as if it was written that way from the start.
- State each rule once, as one calm, plain sentence. That is the form a model gives the most weight.
- Keep genuine limits on irreversible actions, security, privacy, and legal boundaries. State each one once, next to the instruction it guards, with the reason and a fallback: "Ask before force-pushing, because it rewrites shared history."
- For a full audit of a file, with parallel subagent reviewers and a leak check on the rewrite, run `/pink-elephant <file>`.
