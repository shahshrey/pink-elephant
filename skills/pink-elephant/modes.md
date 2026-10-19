# Lite and scan modes

Both modes reuse the patterns, classification rules, and rewrite rules in [SKILL.md](SKILL.md). This file covers what each mode changes.

## Lite

```
/pink-elephant lite <file or pasted text>
```

Lite is one pass in the current session. It costs a fraction of the full audit and finishes in a single turn. The trade-off is reliability: the self-check runs in the same context that wrote the rewrite, and that context reads its own phrasing as clean, so disguised negations and paraphrased leftovers get through more often. Recommend the full audit for prompts that matter, such as production system prompts, always-loaded rule files, and published skills.

```
Lite progress:
- [ ] 1. Hunt all four categories in one pass
- [ ] 2. Classify
- [ ] 3. Rewrite and list removed concepts
- [ ] 4. Self-check once for leaks
- [ ] 5. Report
```

### 1. Hunt

Number the lines and write one sentence on what the text is for. Then read the text once per category, using the "Look for" lists of the four hunters in [hunters.md](hunters.md): Exclusions, Emphasis, Framing, Irrelevance. Record each finding as line, quote, pattern, and suggested action, the same shape the hunters return.

### 2. Classify and 3. Rewrite

Follow steps 2 and 3 of the full audit exactly: Delete, Reframe, Move to a verifier, or Keep for each finding, then rewrite in place and write down the removed-concepts list.

### 4. Self-check

Read the rewrite once against the removed-concepts list, checking each of the leak hunter's five kinds in [hunters.md](hunters.md): literal, semantic, rationale, attention, and structural. Redraft each leaking section from the brief. This is the only check; lite skips the blind reader and the loop.

### 5. Report

Use the full audit's report template with two changes. The heading reads `## Pink Elephant (lite): <file or "pasted text">`, and the verification sentence reads `Verification: one self-check, <n> leaks fixed.` End with this line:

> Lite runs in one context, so it catches fewer disguised negations. For a blind check by fresh readers, run `/pink-elephant <file>`.

## Scan

```
/pink-elephant scan [path]
```

Scan triages every agent instruction file under `path` (default: the workspace root) and ranks them so the user knows which to fix first. It is read-only: the scan reports, and every file stays as it was until the user picks files for the full audit.

```
Scan progress:
- [ ] 1. Find instruction files and tag how each loads
- [ ] 2. Hunt each file with the scan hunter
- [ ] 3. Score severity and rank
- [ ] 4. Report and offer the full audit
```

### 1. Find files

Glob for these, case-insensitively:

| Tool | Paths |
|---|---|
| Shared | `**/AGENTS.md`, `**/CLAUDE.md`, `**/GEMINI.md` |
| Cursor | `.cursor/rules/**`, `.cursorrules`, `.cursor/commands/**` |
| Claude Code | `.claude/commands/**`, `.claude/agents/**` |
| Skills | `**/SKILL.md` |
| Windsurf, Cline, Kiro | `.windsurf/rules/**`, `.windsurfrules`, `.clinerules` (file or folder), `.kiro/steering/**` |
| Copilot | `.github/copilot-instructions.md`, `.github/instructions/**`, `.github/prompts/**` |

Add any system prompt files the user names in the request. Search only the project's own files: leave out `node_modules`, `.git`, `vendor`, and build output, because those hold third-party copies the user can't edit.

Tag each file with how often it reaches the model:

- **always**: loads into every session. `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.cursorrules`, `.windsurfrules`, `.clinerules`, `.github/copilot-instructions.md`, Cursor rules with `alwaysApply: true`, Windsurf rules with `trigger: always_on`, and Kiro steering files with `inclusion: always` or no `inclusion` field.
- **on demand**: loads when invoked or matched. Skills, commands, agents, prompt files, and glob-scoped or agent-requested rules. The `description` of a skill or agent loads every session, so a finding inside a description counts as **always**.

### 2. Hunt

Use the scan hunter from [hunters.md](hunters.md). It covers all four categories in one prompt, takes several files at once, and returns one line per finding.

Group files into batches of about 300 numbered lines, and give any file longer than that a batch of its own. When a subagent tool exists, launch one scan hunter per batch, up to eight in a single message so they run in parallel, and launch further waves of eight until every batch is covered. Otherwise run the scan hunter prompt over each batch in turn.

### 3. Score and rank

Count each file's findings by category. Well-formed Keep constraints (stated once, calmly, with a reason) count as clean.

Give each file the severity of its worst finding:

| Severity | When |
|---|---|
| 🔴 High | A leftover or change narration naming something the project dropped, or an escalated prohibition (capitals, urgency words, the rule repeated), in an **always** file |
| 🟠 Medium | Any other finding in an **always** file, or a leftover or escalation in an **on demand** file |
| 🟡 Low | Any other finding in an **on demand** file |
| 🟢 Clean | Zero findings |

Always-loaded files rank highest because their patterns reach the model in every session, whatever the task. Rank by severity, then **always** before **on demand**, then by finding count.

For each file, quote its worst finding as the worst line, trimmed to about 60 characters. Order of badness: leftover or change narration, escalation, non-relationship or disguised negation, banned list, plain prohibition or corrective framing, repetition, everything else.

Verdicts: the top three files with findings get **Fix first**. Remaining High and Medium files get `Next`, Low files get `Later`.

### 4. Report

The report is often shared as a screenshot, so keep it to one heading, one stats line, one table, and a short fix list. Show up to 15 rows; summarize the rest in one line. List clean files in the footer.

```markdown
## Pink Elephant scan: <repo or path>

**<F> instruction files · <N> findings · <A> files load every session**

| # | File | Loads | Excl | Emph | Frame | Irrel | Worst line | Severity | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `<path>` | always | 3 | 2 | 1 | 1 | L14 "<worst quote>" | 🔴 High | **Fix first** |

<sub>Excl: exclusions · Emph: emphasis · Frame: framing · Irrel: irrelevance</sub>

**Fix first**
1. `<path>`: <one sentence naming the worst pattern and why its load tier makes it urgent>
2. `<path>`: <...>
3. `<path>`: <...>

<+M more files: x low · y clean> · Clean: `<path>`, `<path>`

Next: run `/pink-elephant <top file>` for the full audit with rewrites, or reply "audit the top 3".
```

A filled-in example:

```markdown
## Pink Elephant scan: acme-web

**7 instruction files · 23 findings · 4 files load every session**

| # | File | Loads | Excl | Emph | Frame | Irrel | Worst line | Severity | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `AGENTS.md` | always | 4 | 3 | 1 | 2 | L9 "NEVER use npm. NEVER EVER. Seriously." | 🔴 High | **Fix first** |
| 2 | `.cursor/rules/state.mdc` | always | 2 | 0 | 0 | 1 | L3 "We dropped Redux, so don't import it" | 🔴 High | **Fix first** |
| 3 | `CLAUDE.md` | always | 3 | 0 | 2 | 0 | L22 "Be a reviewer, not a rewriter" | 🟠 Medium | **Fix first** |
| 4 | `skills/deploy/SKILL.md` | on demand | 2 | 1 | 0 | 0 | L41 "IMPORTANT: do not skip the canary" | 🟠 Medium | Next |
| 5 | `.claude/commands/review.md` | on demand | 1 | 0 | 1 | 0 | L6 "Don't nitpick" | 🟡 Low | Later |

<sub>Excl: exclusions · Emph: emphasis · Frame: framing · Irrel: irrelevance</sub>

**Fix first**
1. `AGENTS.md`: the npm rule is shouted three times in a file every session reads, which keeps npm in focus.
2. `.cursor/rules/state.mdc`: an always-apply rule still names Redux, a library the project removed.
3. `CLAUDE.md`: five "X, not Y" contrasts and bans load on every task.

Clean: `.github/copilot-instructions.md`, `.claude/agents/triage.md`

Next: run `/pink-elephant AGENTS.md` for the full audit with rewrites, or reply "audit the top 3".
```

When the user picks files, run the full audit on each one in turn.
