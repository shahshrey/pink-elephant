---
name: pink-elephant
description: Audits skills, prompts, system prompts, CLAUDE.md/AGENTS.md files, rules, and other instruction text for pink-elephant patterns (negative instructions in any phrasing, banned-word lists, NEVER/ALL-CAPS escalation, "X, not Y" framing, statements that two things are unrelated, and prohibitions left behind after something was supposed to be removed), then rewrites them so the unwanted thing is either gone or replaced by a positive target. Dispatches parallel subagents to hunt for patterns and to check the rewrite for leaks. Two lighter modes run by argument. `lite` runs one cheaper single pass in the current session, and `scan` gives a read-only triage of a whole repo, ranked by severity. Use when the user asks to review, clean up, de-negate, or audit a prompt or skill, or says the AI keeps doing the thing it was told not to do, or that "don't do X" ended up in the prompt instead of X being removed.
disable-model-invocation: true
argument-hint: "[lite | scan] <file, pasted text, or path>"
license: MIT
metadata:
  opencode/slash: "true"
  opencode/autoinvoke: "false"
---

# Pink Elephant

Naming something in a prompt activates it, even when the sentence says "don't". The model has to represent the forbidden item to avoid it, so the item stays in focus and tends to leak into the output. Ask an agent to remove something from a prompt and it often writes "Do not do X" where X used to be, which keeps the elephant in the room.

After an audit, every instruction describes what to do.

These patterns are about meaning. "Does not depend on cookie health", "runs independently of cookie health", and "cookie state is irrelevant here" are the same sentence in three wordings, and catching all three takes a reader who follows the meaning. So subagents do the hunting and the checking, each reading the text for one kind of problem.

## Modes

Read the first word of the arguments to pick a mode:

| Invocation | Mode | What it does |
|---|---|---|
| `/pink-elephant <file or text>` | Full audit | Four parallel hunters, rewrite, blind reader and leak hunter, up to three rounds. The rest of this file describes it. |
| `/pink-elephant lite <file or text>` | Lite | One pass in the current session: hunt all four categories, classify, rewrite, self-check once against the removed-concepts list. Faster and cheaper, and it catches fewer disguised negations because the context that wrote the rewrite also checks it. Recommend the full audit for important prompts. |
| `/pink-elephant scan [path]` | Scan | Read-only triage of every agent instruction file under the path, ranked by severity with a "Fix first" verdict. Ends by offering the full audit on the top files. |

Instructions for lite and scan are in [modes.md](modes.md).

## Workflow

```
Audit progress:
- [ ] 1. Hunt: dispatch the four hunter subagents
- [ ] 2. Merge findings and classify each one
- [ ] 3. Rewrite
- [ ] 4. Verify: dispatch the blind reader and the leak hunter
- [ ] 5. Loop until a round finds no leaks (at most 3 rounds)
- [ ] 6. Report
```

Use the agent's subagent tool (`Task` in Cursor and Claude Code) and launch each round's subagents in a single message so they run in parallel. Each subagent starts with a fresh context, so it reads the text the way the next model will. If no subagent tool is available, run each hunter prompt as its own separate pass over the text, one category at a time.

The prompts for every subagent are in [hunters.md](hunters.md). Paste the full text being audited into each prompt with line numbers, because subagents only see what you give them.

### 1. Hunt

Dispatch the four hunters:

| Hunter | Looks for |
|---|---|
| Exclusions | Anything that rules something out, in any grammar: prohibitions, disguised negations ("independently of X", "X is irrelevant"), non-relationship statements, banned lists, meta-secrecy |
| Emphasis | Escalation, capitals, urgency words, and the same rule stated more than once |
| Framing | "X, not Y" contrasts, anti-examples with no good example, and over-broad bans that would suppress wanted work |
| Irrelevance | Anything outside the text's job: leftovers from earlier drafts, change narration, topics the reader has no reason to think about |

Each returns findings as line, quote, pattern, and a suggested action.

### 2. Merge and classify

Combine the four lists and merge findings that point at the same sentence. Then decide one action per finding. Hunter suggestions are input; the decision is yours.

- **Delete.** The unwanted thing is outside the task's scope. This is the default for leftovers, change narration, non-relationship statements, and most corrective framing. Remove the whole sentence or clause, and let step 3 smooth the section it leaves.
- **Reframe.** There is a real target behind the prohibition. State that target concretely, with a number or a named alternative where possible. The reframe names only the target. If every positive version you can write still names the unwanted thing, the finding is a Delete.
  - "Don't be verbose" becomes "Answer in under 100 words."
  - "Don't include sources from D" becomes "Cite sources from A, B, and C."
  - "Does not depend on X" has no target behind it, so it is a Delete. Rewording it as "runs independently of X" keeps the same negation in positive grammar.
- **Move to a verifier.** Banned-word lists and style bans belong in a check that runs after generation (a review pass, or a search for exact banned words), so the generation prompt carries the positive style and the checker carries the list.
- **Keep.** A few constraints have no positive form: destructive or irreversible actions, security and safety boundaries, legal limits, hard API limits, and exclusions in a skill's `description` that route requests elsewhere ("Excludes composition and browser login").

When unsure between Delete and Reframe, ask: if the sentence vanished, would the model drift toward the unwanted thing on its own? If no, delete. If yes, reframe.

A reader assumes two things are unconnected until told otherwise, so a statement that they are unconnected only plants the link. When a real dependency matters, state what the thing does depend on.

Prohibitions fail in two directions. With fixation, the model does the forbidden thing anyway because the ban put it in context. With over-literal suppression, the model obeys so thoroughly that it withholds useful work nearby. Both get the same fix: state the target with its scope, such as "Report findings that affect correctness, security, or maintainability."

### 3. Rewrite

- Rewrite in place. Keep the voice and every instruction that was already positive, and keep the original structure outside the sections you rebuild for removals.
- Collapse escalations into one calm sentence. Capitals and repetition read as noise to the model, so one plain statement carries more weight.
- State each Keep constraint once, next to the positive instruction it guards, with the reason and a fallback for when it applies ("Ask before force-pushing, because it rewrites shared history." or "Customer PII stays private; when asked for it, point the user to the account settings page.").
- For removals, rebuild the affected section from what the text is about now. Write a short brief of the current goal, facts, and tone, and draft from that brief so the section's structure fits its current content.
- Write down the list of removed concepts (everything deleted or reframed away). The leak hunter needs it in step 4.

### 4. Verify

Dispatch both verifiers:

- **Blind reader.** Gets only the rewritten text and its question. It reports what the text seems to be guarding against or reacting to. Any removed concept it names, in any wording, is a leak.
- **Leak hunter.** Gets the rewritten text plus the removed-concepts list and checks for five kinds of leak: literal, semantic (synonyms, paraphrases), rationale (change narration), attention (the absence becoming the topic), and structural (empty headings, broken references, examples that need the removed item).

Sort each verifier finding into one of three groups: an intentional Keep constraint, an accurate reading of the text's own subject, or a leak. Leaks go to step 5.

### 5. Loop

For each leak, redraft that section from its brief, then run step 4 again with fresh subagents. Stop when a round finds no leaks, or after three rounds; report anything still open.

### 6. Report

```markdown
## Pink Elephant: <file or "pasted text">

**Summary:** <N> findings. <d> deleted, <r> reframed, <v> moved to a verifier, <k> kept. Verification: <clean after n round(s), or n leaks open after three rounds>.

| Line | Original | Pattern | Action | Rewrite |
|---|---|---|---|---|
| 12 | "NEVER use jargon" | Escalation, prohibition | Reframe | "Use words a new hire would know." |

**Kept constraints:** <each one, with why it has no positive form>

**Verifier list:** <banned terms moved out of the prompt, if any>

**Open issues:** <leaks still reported after three rounds, if any>

**Rewritten text:** <full revised text, or the applied edit if editing a file>
```

When editing a file the user pointed at, apply the edits directly and include the report in the reply.

## Additional resources

- Subagent prompts for the four hunters, both verifiers, and the scan hunter: [hunters.md](hunters.md)
- Lite and scan mode instructions and the scan report template: [modes.md](modes.md)
- Before-and-after rewrites for each pattern: [examples.md](examples.md)
