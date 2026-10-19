# Contributing

Pink Elephant is one prompt. Most changes belong in [`skills/pink-elephant/`](skills/pink-elephant/), and the rest of the repo just loads that prompt into different agents.

## Most useful contributions

- **A mention-rate scenario.** Add a `Scenario` to `SCENARIOS` in [`evals/downstream.py`](evals/downstream.py). It needs a system prompt that states the prohibition the way an agent typically leaves it, plus the rewrite. Include a clean version too if it differs from the rewrite. Then write three user messages that sit next to the forbidden subject without asking about it. Finish with regexes and hand-written positive and negative strings to test them against.
- **An audit case.** Add a folder to [`evals/fixtures/cases/`](evals/fixtures/cases/) with three files. `input.md` is the original, `oracle.md` is the correct rewrite, and `near_miss.md` is the plausible wrong one. Then describe what must disappear and what must survive in `AUDIT_CASES` in [`evals/pink_elephant_checks.py`](evals/pink_elephant_checks.py).
- **A verified install.** Did you run an install route from [INSTALL.md](INSTALL.md) end to end? Open a pull request that marks it verified and names the agent version you used.
- **A real-world before and after.** If Pink Elephant fixed an instruction file for you, I'd love to see it. Send it as an issue or add it to [examples.md](skills/pink-elephant/examples.md).

## Before opening a pull request

Run the free evals. They make no model calls.

```bash
cd evals
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python run_evals.py free
```

The grader checks itself first. Every oracle has to pass and every near miss has to fail.

If you change the skill text, run the skill on itself with `/pink-elephant skills/pink-elephant/SKILL.md`. The prompt follows its own rules, and I'd like to keep it that way.

Paid evals run through Claude Code, and [evals/README.md](evals/README.md) describes them. If you ran them, mention the results in your pull request.

Keep the eight companion rule copies identical to [AGENTS.md](AGENTS.md). [INSTALL.md](INSTALL.md#companion-rule) lists where they live.
