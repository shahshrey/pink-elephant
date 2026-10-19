# Evals

These are the evals for Pink Elephant. Each run drives the real Claude Code through `claude-agent-sdk` in a fresh temporary folder, then grades the file the agent left behind. I adapted the harness from the [skill evals course](https://github.com/shahshrey/skill_evals_course).

## Setup

```bash
cd evals
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

The paid evals need the `claude` CLI logged in, and so does the mention-rate benchmark. Check with `claude auth status`. Claude Code bills a visible `ANTHROPIC_API_KEY` ahead of a subscription login, so `eval_kit` drops that key from the environment before it starts Claude Code. Set `EVAL_USE_API_KEY=1` if you want the key billed instead.

Three variables pick the model and effort for every eval that calls Claude. That covers grading, the A/B comparison, the LLM judge, the trajectory check, and the mention-rate benchmark.

- `EVAL_MODEL`: the agent model, and the judge model unless `EVAL_JUDGE_MODEL` is set. Defaults to `claude-opus-5` for the agent and `claude-sonnet-5` for the judge.
- `EVAL_JUDGE_MODEL`: the judge model for the LLM judge and the mention-rate benchmark.
- `EVAL_EFFORT`: `low`, `medium`, `high`, `xhigh` or `max`, passed to Claude Code as `--effort`. Leave it unset to keep Claude Code's default.

```bash
EVAL_MODEL=claude-sonnet-5-5 EVAL_EFFORT=medium .venv/bin/python run_evals.py mention_rate paid report
```

## Running

```bash
.venv/bin/python run_evals.py free      # structural lint, security scan, routing, grader check, mention-rate check
.venv/bin/python run_evals.py paid      # trigger, grading, with/without-skill A/B, LLM judge, trajectory
.venv/bin/python run_evals.py report    # statistics, regression check, cost
.venv/bin/python run_evals.py ab stats  # any evals by name
```

`free` makes no API calls. `report` only reads what `paid` saved in `results/`, so it's free too. The mention-rate benchmark, `mention_rate` or `downstream`, belongs to neither paid group. It has its own section below.

| Eval | Name on the command line | Group | Log file |
| --- | --- | --- | --- |
| Structural lint of `SKILL.md` | `lint` | free | `01_structural_lint.log` |
| Security scan | `scan` | free | `02_security_scan.log` |
| Offline routing against decoy skills | `routing` | free | `03_routing_offline.log` |
| Trigger eval (auto-invocation only) | `trigger` | paid | `04_trigger_eval.log` |
| Grader check (oracles pass, near misses fail) | `sanity` | free | `05_grader_sanity.log` |
| Deterministic grading | `grade` | paid | `05_deterministic_grading.log` |
| With/without-skill A/B comparison | `ab` | paid | `06_ab_comparison.log` |
| LLM judge | `judge` | paid | `07_llm_judge.log` |
| Trajectory check | `trajectory` | paid | `08_trajectory_eval.log` |
| Statistics | `stats` | report | `09_statistics.log` |
| Regression check | `regression` | report | `10_regression_check.log` |
| Cost | `cost` | report | `11_efficiency_eval.log` |
| Mention-rate check | `mention_rate_check` (`downstream_check`) | free | `12_downstream_check.log` |
| Mention-rate benchmark | `mention_rate` (`downstream`) | separate | `12_downstream.log` |

`paid` makes 37 agent runs. Grading takes 7, the trajectory check takes 2, and the A/B comparison takes 28, which is 7 cases times 2 attempts, once with the skill and once without. The LLM judge adds about 58 judge calls on top. Most of the money goes to the 23 with-skill runs, since each one dispatches six or more subagents.

## The cases

Each folder in `fixtures/cases/` holds three files:

- `input.md`: the file the agent starts from. It's a realistic 20 to 60 line prompt, skill, or AGENTS.md, with several patterns mixed into content that has to survive.
- `oracle.md`: a correct rewrite, written by hand.
- `near_miss.md`: the plausible wrong rewrite a careless agent produces, such as rewording "unrelated to seed data" as "seed data is handled separately".

`pink_elephant_checks.py` defines the cases. For each one it lists the patterns that must disappear, the content that must survive, and the checks the near miss must trip.

| Case | Pattern under test | The near miss |
| --- | --- | --- |
| `billing-removal` | Billing threaded through a support bot's scope, tool table, escalation queues, change note, and example dialog | Redirects billing questions instead of dropping the topic |
| `disguised-negation` | Four non-relationship statements in a skill, each worded differently, next to routing exclusions and a data-loss limit that stay | Rewords each statement so the concept survives |
| `shouting-rules` | An AGENTS.md with caps, `!!!`, a reminders section repeating three rules, and "X, not Y" framing, plus a secrets limit that stays | Lowercases the shouting but keeps every prohibition |
| `banned-words` | A 15-item banned list, punctuation bans, vague tone rules, and a "bad example" that quotes the banned words | Softens the list into "steer clear of words like..." |
| `corrective-framing` | A PR-review agent built from "reviewer, not rewriter", "rather than", and "instead of" | Swaps "not" for "rather than" and "instead of" |
| `competitor-removal` | A removal with no prohibitions in the input: competitors and a comparison table have to leave a sales prompt | Adds "if a visitor brings up another provider..." |
| `legitimate-keeps` | The control: every prohibition is an irreversible, security, or on-call limit with a reason and a fallback, so the right audit leaves them | Turns the limits into vague positives and loses the commands, times, and fallbacks |

Every workspace also contains `faq.md`, a help-center FAQ packed with prohibitions. Nobody asks the agent to touch it. If it changes, the trajectory check fails the run.

Before any paid run, the grader check tests the grader itself. I don't trust a grader I haven't seen fail. Every oracle has to pass. Every untouched input has to fail, and it has to fail on substance, not just for being unchanged. The control is the exception, because there the untouched input is already correct and has to pass. Every near miss has to fail on the checks it was built to trip.

The routing eval uses five decoy skills from neighbouring territory, including a prompt linter and an AGENTS.md writer. Its requests are worded the way people describe the problem, such as "my CLAUDE.md says never use console.log and now the agent sprinkles console.log everywhere".

## The mention-rate benchmark

The other evals grade the rewritten file. This one tests the premise the whole skill rests on. When a system prompt names the unwanted thing as a prohibition, how often do the model's answers mention it anyway?

`downstream.py` defines eight scenarios:

- a billing-free support bot
- a sales assistant that leaves out competitors
- a banned-words post writer
- the shouting `AGENTS.md`
- a `CLAUDE.md` that bans `console.log`, asked for debugging changes
- a `CLAUDE.md` that bans a legacy HTTP helper
- a help widget after a rebrand
- a support writer with an em-dash ban

Each scenario has a negated system prompt, which is the prohibition as an agent leaves it, and a rewritten one in the skill's style. Four of the rewritten prompts reuse the `oracle.md` fixtures. Five scenarios also get a clean control with no guidance on the subject at all. Every version answers the same three user messages. Each message sits next to the forbidden subject without asking about it. A response counts as a mention when it matches the scenario's regexes. Set `DOWNSTREAM_JUDGE=1` to also send responses with no literal hit to an LLM judge, so synonyms count too.

```bash
.venv/bin/python run_evals.py mention_rate_check   # free, also part of `free`
.venv/bin/python run_evals.py mention_rate         # 630 Claude Code calls
.venv/bin/python run_evals.py mention_rate_report  # re-mark the latest saved run, free
```

The older names `downstream_check`, `downstream` and `downstream_report` run the same evals.

`mention_rate_check` makes no calls. For each scenario it confirms that the negated prompt names the thing and that the rewritten prompt, the clean prompt, and every user message don't. It also confirms the regexes catch hand-written positive strings and leave the negative ones alone. Then it checks the statistics against known answers and prints the planned call count and cost.

`mention_rate` sends every sample through Claude Code with `claude-agent-sdk`, so a subscription login is enough. Each sample is one turn in an empty temporary folder, with no tools and no MCP servers. It runs with `setting_sources=[]`, with CLAUDE.md and memory loading switched off, and with the scenario's prompt passed as a plain string, which replaces Claude Code's default system prompt. Claude Code still adds a one-line SDK identity, an environment block with the folder, platform, and date, and the account email. Every version gets those same additions, so they don't favor one prompt over another. Samples run six at a time. A failed call is retried with waits of up to 15 minutes, so a rate limit pauses the run instead of killing it. `DOWNSTREAM_RESUME=1` picks up the latest run and requests only the samples it's missing.

By default the benchmark takes 10 samples per version per message on `eval_kit.JUDGE_MODEL` at `eval_kit.EFFORT`, which comes to 630 calls. Each result records Claude Code's `total_cost_usd`, the API list-price equivalent. Under a subscription login that number is notional. These variables change the defaults:

- `DOWNSTREAM_MODEL`
- `DOWNSTREAM_EFFORT`
- `DOWNSTREAM_SAMPLES`
- `DOWNSTREAM_MAX_TOKENS`, an output cap that includes thinking. Unset leaves Claude Code's own cap.
- `DOWNSTREAM_CONCURRENCY`
- `DOWNSTREAM_JUDGE_MODEL`
- `DOWNSTREAM_PRICE_INPUT` and `DOWNSTREAM_PRICE_OUTPUT`, which only feed the estimate in `mention_rate_check`.

The report gives each version's mention rate with a 95% Wilson interval, the relative reduction from negated to rewritten, and a per-scenario table. Responses to the same message are correlated, so the interval for the reduction comes from resampling whole scenario-and-message cells. Treating every sample as independent would make the interval look tighter than it is. Raw samples and a JSON summary go to `results/downstream/`. The linkable summary, [`benchmarks/downstream.md`](benchmarks/downstream.md), is written only from a real run's saved samples.

## Manual invocation

The skill sets `disable-model-invocation: true`, so it only runs as `/pink-elephant`. The evals read that setting and adjust:

- The with-skill arm sends `/pink-elephant <request>`, the way a user has to. The without-skill arm sends the bare request with no skill installed.
- The trigger eval is skipped. A manual-only skill never triggers on its own, so there's nothing to measure.
- The routing eval still runs. It shows how the description would compete if auto-invocation were turned on.

Remove the setting from `SKILL.md` and the same commands test auto-invocation instead. Requests go out without the slash command, and the trigger eval runs.

## What gets installed

`run_evals.py` copies the skill folder, `skills/pink-elephant/`, into `.staged/` and installs only that copy. The folder holds `SKILL.md`, `hunters.md`, `examples.md`, `modes.md`, and Codex's `agents/openai.yaml`. Everything else in the repository stays outside the installed skill, including this `evals/` folder with its oracles, the plugin manifests, and the rule files. That matters, because an agent that could read the oracles would ace the evals for the wrong reason. Any file added to `skills/pink-elephant/` ships with the skill, and the evals install it too. The regression check also takes its fingerprint from the staged copy.
