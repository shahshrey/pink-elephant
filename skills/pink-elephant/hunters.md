# Subagent prompts

Fill in the placeholders and send each prompt as its own subagent task. Launch all hunters in one message, and later both verifiers in one message, so each group runs in parallel.

- `{{TEXT}}`: the full text being audited, with line numbers (`12| ...`).
- `{{PURPOSE}}`: one sentence on what the text is for, such as "A Claude Code skill for calling LinkedIn's internal APIs." Write it from what the text does now.
- `{{REMOVED}}`: the removed-concepts list from the rewrite step. Only the leak hunter gets this.
- `{{FILES}}`: for the scan hunter, each file in the batch as a `=== <path> ===` header followed by its numbered lines.

## Shared output format (hunters)

Append this to every hunter prompt:

```
Read every line. Judge by meaning, because the same idea can be phrased many ways; a sentence counts even when none of the example wordings appear in it.

Return a list, one item per finding:

- line: <number>
  quote: "<exact text>"
  pattern: <name from your category>
  why: <one sentence on what concept the line keeps active>
  suggested_action: Delete | Reframe | Move to a verifier | Keep
  rewrite: <proposed replacement, or "none" for Delete>

Non-relationship statements, leftovers, and change narration default to Delete.
For Reframe, the rewrite must name only the wanted behavior. When the only possible rewrite still names the unwanted concept, suggest Delete.
For Keep, the line guards something irreversible, security- or safety-critical, legal, a hard technical limit, or routes requests elsewhere in a skill description.
When nothing in your category is present, return "No findings."
```

## Hunter 1: Exclusions

```
You are auditing instruction text that will be read by an AI model. Your job is to find every place the text rules something out, in any grammar.

What the text is for: {{PURPOSE}}

Look for:
- Prohibitions: telling the reader to refrain from something ("don't", "never", "avoid", "no X", "without X", "refrain from", "stay away from").
- Disguised negations: an exclusion phrased as a positive ("runs independently of X", "works regardless of X", "X-free", "separate from X", "unaffected by X", "X is irrelevant here", "X plays no part").
- Non-relationship statements: claims that two things are unconnected ("A does not depend on B", "A is unrelated to B", "A has nothing to do with B"). Readers already assume things are unconnected, so these plant a link.
- Banned lists: lists of words, phrases, tools, or behaviors to stay away from.
- Meta-secrecy: instructions to hide or refrain from mentioning the instructions themselves.

Text:
{{TEXT}}
```

## Hunter 2: Emphasis

```
You are auditing instruction text that will be read by an AI model. Your job is to find emphasis and repetition that make a rule louder without making it clearer.

What the text is for: {{PURPOSE}}

Look for:
- Escalation: capitals, "CRITICAL", "IMPORTANT", "under no circumstances", "absolutely", stacked exclamation marks, bold used as alarm.
- Repetition: the same rule stated more than once anywhere in the text, even in different words or different sections. List every location of each repeated rule together.
- Stacking: three or more exclusions about the same subject in one place.

Text:
{{TEXT}}
```

## Hunter 3: Framing

```
You are auditing instruction text that will be read by an AI model. Your job is to find framing that names an unwanted alternative, or that would make the reader suppress useful work.

What the text is for: {{PURPOSE}}

Look for:
- Corrective framing: a contrast where the rejected half adds nothing ("X, not Y", "rather than Y", "instead of Y", "Y is the wrong approach; use X", "think of it as X, as opposed to Y").
- Anti-examples: a bad sample or bad output shown with no matching good sample.
- Over-broad bans: limits that a literal reader would apply too widely and drop wanted behavior along with the unwanted part ("don't nitpick", "only report high-severity issues", "keep it minimal", "do the bare minimum", "nothing else"). Name the wanted behavior that would get suppressed.

Text:
{{TEXT}}
```

## Hunter 4: Irrelevance

```
You are auditing instruction text that will be read by an AI model. Your job is to find content the reader has no reason to think about, given what the text is for.

What the text is for: {{PURPOSE}}

Look for:
- Leftovers: mentions of topics, features, or behaviors outside the text's job, especially ones that read like they survived from an earlier draft.
- Change narration: language describing how the text or system used to be ("previously", "no longer", "we removed", "now only", "used to", "as of the latest change").
- Unprompted reassurance: sentences answering a worry the reader would never have had.

For each finding, say why it falls outside the stated purpose.

Text:
{{TEXT}}
```

## Scan hunter

Used by scan mode in [modes.md](modes.md). One prompt covers all four categories across a batch of files and carries its own one-line-per-finding output format.

```
You are triaging agent instruction files: rules, skills, commands, and prompts that an AI model reads. For each file, find every line that keeps an unwanted concept active. Judge by meaning, because the same idea can be phrased many ways.

Look for:
- Exclusions: prohibitions, disguised negations ("works regardless of X", "X is irrelevant"), non-relationship statements ("A is unrelated to B"), banned lists, meta-secrecy.
- Emphasis: capitals, urgency words, bold used as alarm, the same rule stated more than once, three or more exclusions stacked on one subject.
- Framing: "X, not Y" and "rather than Y" contrasts, bad examples with no good example beside them, over-broad limits that would suppress wanted work.
- Irrelevance: leftovers that name a tool, library, feature, or topic the project appears to have dropped; change narration ("previously", "we removed", "now only"); reassurance answering a worry the reader would never have.

A constraint guarding something irreversible, security- or safety-critical, legal, or a hard technical limit is a legitimate Keep. List it only when it is shouted or repeated, under Emphasis.

Return one block per file, in the order given:

=== <path> ===
purpose: <one sentence on what the file is for, judged from its content>
<line> | <Exclusions | Emphasis | Framing | Irrelevance> | <pattern> | "<exact quote, up to 80 characters>"

Pattern is one of: prohibition, disguised negation, non-relationship, banned list, meta-secrecy, escalation, repetition, stacking, corrective framing, anti-example, over-broad ban, leftover, change narration, reassurance. For a repeated rule, give one line per location.

When a file has nothing to report, write "clean" under its purpose line.

Files:
{{FILES}}
```

## Verifier 1: Blind reader

Send only the rewritten text in this prompt. Leave out the purpose, the original, and the removed-concepts list.

```
Read the text below as the AI model it was written for.

Answer three questions:
1. What does this text seem to be guarding against, reacting to, or steering away from? Quote the lines that give you that impression.
2. Which topics, systems, or behaviors does it mention that seem unrelated to its main job? Quote them.
3. Does any part read like it was edited to remove something, such as an empty heading, an orphaned reference, an example that seems to be missing its context, or a sentence explaining a change? Quote it.

When the text gives no such impression for a question, answer "Nothing."

Text:
{{TEXT}}
```

## Verifier 2: Leak hunter

```
The text below was rewritten to remove these concepts:
{{REMOVED}}

Find every place any of them survives. Judge by meaning, because a concept can return under a different name.

Check for five kinds of leak:
- Literal: the concept's name, spelling variants, abbreviations, labels, text inside code samples or examples.
- Semantic: synonyms, broader or narrower terms, paraphrases, euphemisms.
- Rationale: narration of the change ("instead of", "previously", "no longer", "we removed", "rather than").
- Attention: the absence itself becoming a topic, especially in titles, openings, summaries, or descriptions.
- Structural: empty headings, broken cross-references, placeholders, or examples that only make sense with the removed concept.

Return a list, one item per leak:

- line: <number>
  quote: "<exact text>"
  leak_type: Literal | Semantic | Rationale | Attention | Structural
  concept: <which removed concept>

When no leaks are present, return "No leaks."

Text:
{{TEXT}}
```
