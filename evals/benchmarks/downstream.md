# Mention-rate benchmark

Does naming the unwanted thing make the model say it? Yes, often enough to measure.

**92% fewer mentions.** With the prohibition in the system prompt, 60 of 240 responses (25%) mentioned the forbidden thing. With the Pink Elephant rewrite, 5 of 240 (2%) did. The 95% interval for the reduction runs from 62% to 100%.

## Method

- There are 8 scenarios. Each one is a system prompt in two or three versions.
  - **Negated** is the prohibition or leftover the way an agent usually leaves it, such as "Do not discuss billing".
  - **Rewritten** is the skill's rewrite. Several of these are the hand-written oracles from the fixtures.
  - **Clean** is the same prompt with no guidance on the subject at all. It only exists where it differs from the other two.
- Each version answers the same user messages. The messages sit next to the forbidden subject without asking about it.
- Every version gets 10 samples per message on claude-sonnet-5-5, at medium effort and default temperature, through Claude Code via claude-agent-sdk. Each call is one turn with no tools, the scenario prompt as the entire system prompt, no settings or CLAUDE.md loaded, in an empty folder.
- A response counts as a mention when it matches the scenario's literal regex. Before any call goes out, every regex gets checked against hand-written positive and negative strings.
- The Wilson intervals treat responses as independent. They aren't, quite. Responses to the same message are correlated, so the interval for the reduction resamples whole (scenario, message) cells instead.
- The run is `samples-20261018T090911Z.jsonl`. Scenarios, prompts and regexes live in [downstream.py](../downstream.py). To reproduce, run `python run_evals.py mention_rate` from `evals/`.

## Overall

| Version | Mentions | Rate | 95% Wilson |
| --- | --- | --- | --- |
| negated | 60/240 | 25% | 20% to 31% |
| rewritten | 5/240 | 2% | 1% to 5% |
| clean | 30/150 | 20% | 14% to 27% |

## Per scenario

| Scenario | Forbidden | Negated | Rewritten | Clean | Reduction |
| --- | --- | --- | --- | --- | --- |
| `billing-support` | billing, invoices, refunds, payments, charges, or subscriptions | 4/30 | 0/30 | 0/30 | 100% |
| `competitor-sales` | competitors or other hosting providers, or comparisons with them | 1/30 | 0/30 | - | 100% |
| `banned-words-writer` | the words delve, tapestry, testament, realm, landscape, leverage, unlock, empower, elevate, supercharge, game-changer, cutting-edge, seamless, robust | 0/30 | 0/30 | 0/30 | - |
| `shouting-agents` | npm or yarn, the TypeScript any type, default exports, or duplicate files such as Button-fixed.tsx | 0/30 | 0/30 | - | - |
| `console-log-coding` | console.log or any other console.* call | 29/30 | 0/30 | 30/30 | 100% |
| `legacy-helper-coding` | the deprecated fetchJson helper or the legacy HTTP module | 25/30 | 0/30 | 0/30 | 100% |
| `rebrand-old-name` | the product's former name Tasko, or the fact that it was renamed | 1/30 | 5/30 | - | -400% |
| `em-dash-support` | em dashes, or dashes used in their place | 0/30 | 0/30 | 0/30 | - |

Most of the gain comes from two coding scenarios, `console-log-coding` and `legacy-helper-coding`, which account for 54 of the 60 negated mentions. `rebrand-old-name` went the wrong way, and I'm not going to pretend otherwise. The rewrite drew 5 mentions where the prohibition drew 1. Those 5 are every rewritten-version mention in the run, so this is the scenario to fix next.

## Clean control

These are the scenarios that have a clean version, run over the same messages:

| Version | Mentions | Rate |
| --- | --- | --- |
| negated | 58/150 | 39% |
| rewritten | 0/150 | 0% |
| clean | 30/150 | 20% |

This is the table I find most interesting. Saying nothing at all gets 20%. Adding the prohibition pushes it to 39%, so on these scenarios the negation made things worse than silence. The rewrite gets 0.

## Cost

The run used 834,697 prompt tokens and 718,333 output tokens. Claude Code reported $9.54 for the samples at API list prices, but the run went through a Claude subscription login, so that figure is notional. 0 failed requests were excluded.
