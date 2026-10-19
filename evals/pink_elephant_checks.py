"""Deterministic checks and test cases for the Pink Elephant skill.

The skill's output is an edited file, so every check reads the file the
agent left behind and compares it with the file it started from. Text in,
pass-or-fail out. No AI anywhere.

Import with ``from pink_elephant_checks import *``.
"""
import re

from pydantic import BaseModel, Field

from eval_kit import read_fixture

# Words that turn a sentence into a prohibition. Counted, not banned: a hard
# limit with a reason and a fallback is a legitimate Keep, so each case sets
# its own ceiling.
PROHIBITION = re.compile(
    r"\b(don'?t|do not|never|avoid|must not|mustn'?t|should not|shouldn'?t|refrain|"
    r"under no circumstances|not allowed|forbidden|prohibited)\b",
    re.IGNORECASE,
)
# Four or more capitals in a row, or a run of exclamation marks. Acronyms in
# backticks are stripped first; the allowlist covers file names and acronyms
# that legitimately appear in prose.
SHOUTING = re.compile(r"\b[A-Z]{4,}\b|!!")
SHOUTING_ALLOWED = {"JSON", "HTTP", "HTTPS", "YAML", "TODO", "README", "AGENTS", "CLAUDE", "OAUTH", "NOTES",
                    "RELEASE"}
CORRECTIVE = re.compile(
    r"\binstead of\b|\brather than\b|,\s*not an?\b|\bnot just\b|\bno longer\b|\banymore\b",
    re.IGNORECASE,
)
CHANGE_NARRATION = re.compile(
    r"\b(previously|used to|from now on|now (only|focuses|handles)|was removed|has been removed|"
    r"were removed|moved to (a|another) (team|bot|tool)|this (version|update))\b",
    re.IGNORECASE,
)
INLINE_CODE = re.compile(r"`[^`]*`")
# Quoted passages are sample content, such as an example post, so a "never"
# inside one is the example talking, not the instructions.
QUOTED = re.compile(r"\"[^\"]*\"|“[^”]*”")


class CheckResult(BaseModel):
    """What one rule made of one rewritten file."""

    name: str = Field(description="Which rule was checked, such as forbidden_absent. Reports group on this.")
    passed: bool = Field(description="Did the rewritten file satisfy the rule?")
    detail: str = Field(default="", description="What the check saw, so a failure explains itself.")


def count_prohibitions(text: str) -> int:
    """Count prohibition words in the text, outside inline code and quoted examples."""
    return len(PROHIBITION.findall(QUOTED.sub("", INLINE_CODE.sub("", text))))


def shouted_words(text: str) -> list[str]:
    """Return every shouted token in the text, outside inline code."""
    found = SHOUTING.findall(INLINE_CODE.sub("", text))
    return [word for word in found if word not in SHOUTING_ALLOWED]


def check_rewrite(original: str, rewritten: str | None, case: dict) -> list[CheckResult]:
    """Run every rule that can be settled without asking anyone's opinion.

    Args:
        original: The file as it was handed to the agent.
        rewritten: The file as the agent left it. None when it was deleted.
        case: The test case, carrying its forbidden and must-keep patterns.

    Returns:
        One result per rule. A deleted file fails file_edited and nothing
        else runs, since there is no text left to mark. Cases that expect no
        edit skip file_edited, because leaving the file alone is the answer.

    Example:
        results = check_rewrite(read_case(case, "input"), run.files[case["target"]], case)
    """
    if rewritten is None:
        return [CheckResult(name="file_edited", passed=False, detail="the target file was deleted")]
    results = []
    if case.get("expect_edit", True):
        results.append(CheckResult(name="file_edited", passed=rewritten.strip() != original.strip(),
                                   detail="the file differs from the original"))

    leaked = [p for p in case["forbidden"] if re.search(p, rewritten, re.IGNORECASE)]
    results.append(CheckResult(name="forbidden_absent", passed=not leaked,
                               detail=f"still present: {leaked}" if leaked else "none of the removed concepts remain"))

    lost = [p for p in case["must_keep"] if not re.search(p, rewritten, re.IGNORECASE)]
    results.append(CheckResult(name="kept_content", passed=not lost,
                               detail=f"lost: {lost}" if lost else "all required content survived"))

    prohibitions = count_prohibitions(rewritten)
    results.append(CheckResult(name="prohibitions_within_limit", passed=prohibitions <= case["max_prohibitions"],
                               detail=f"{prohibitions} prohibition words, limit {case['max_prohibitions']}"))

    shouted = shouted_words(rewritten)
    results.append(CheckResult(name="no_shouting", passed=not shouted, detail=f"shouted: {shouted}"))

    corrective = CORRECTIVE.findall(rewritten)
    results.append(CheckResult(name="no_corrective_framing", passed=not corrective,
                               detail=f"found: {corrective}"))

    narration = [m.group(0) for m in CHANGE_NARRATION.finditer(rewritten)]
    results.append(CheckResult(name="no_change_narration", passed=not narration, detail=f"found: {narration}"))
    return results


def all_passed(results: list[CheckResult]) -> bool:
    """Did every check pass? One failure fails the rewrite."""
    return all(r.passed for r in results)


def failed_names(results: list[CheckResult]) -> list[str]:
    """List the checks that failed, in the order they ran."""
    return [r.name for r in results if not r.passed]


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

# A file every workspace carries that the agent was not asked to touch. It
# contains prohibitions on purpose, so an over-eager audit has a reason to
# edit it. The trajectory eval checks it comes back unchanged.
BYSTANDER = "faq.md"

AUDIT_CASES = [
    {
        "id": "billing-removal",
        "target": "prompt.md",
        "prompt": "We moved billing questions to a different team, so the support bot in prompt.md should only "
                  "handle the login flow now. Clean the prompt up for that.",
        "forbidden": [r"\bbill", r"invoice", r"refund", r"payment", r"subscription", r"\bcharge", r"financ",
                      r"\bcard\b", r"plan change", r"\bv3\b", r"deprecated", r"\bmoved\b", r"no longer"],
        "must_keep": [r"send_reset_link", r"account_status", r"unlock_account", r"reenroll_2fa", r"escalate",
                      r"`security`", r"2FA", r"last four digits", r"password", r"(mask|private|redact|partial)",
                      r"30 minutes", r"60 minutes", r"120 words", r"locked"],
        "max_prohibitions": 2,
        "removed": "billing, invoices, refunds, payments, charges, subscriptions, plan changes, the Finance team "
                   "and its bot, deprecated billing tools, and the fact that the bot's scope changed",
        "near_miss_fails": ["forbidden_absent"],
    },
    {
        "id": "disguised-negation",
        # Deliberately not SKILL.md, so neither arm's harness mistakes the
        # fixture for an installed skill.
        "target": "db-migrations-skill.md",
        "prompt": "db-migrations-skill.md is one of our agent skills. Tighten it up so the agent only gets what "
                  "it needs.",
        "forbidden": [r"prisma", r"\bORM\b", r"\bseed", r"\bCI\b", r"docker", r"whether or not", r"regardless",
                      r"unrelated", r"no bearing", r"agnostic", r"independent"],
        "must_keep": [r"Excludes\s+schema\s+design\s+reviews", r"db-schema-review", r"pg-query-tuning",
                      r"lock_timeout", r"CONCURRENTLY", r"10,000", r"YYYYMMDDHHMM", r"pnpm db:migrate --env staging",
                      r"pnpm db:status", r"pnpm db:snapshot", r"maintainer approves", r"confirm the table name",
                      r"NOT NULL", r"UTC", r"-- down"],
        "max_prohibitions": 1,
        "removed": "Prisma and the ORM, seed data, CI providers, Docker Compose, and every statement that one of "
                   "these is unrelated to the workflow",
        "near_miss_fails": ["forbidden_absent"],
    },
    {
        "id": "shouting-rules",
        # AGENTS.md rather than CLAUDE.md, because Claude Code would load a
        # CLAUDE.md into both arms as instructions before the run began.
        "target": "AGENTS.md",
        "prompt": "Our AGENTS.md is full of shouting and the coding agent still does the things it says not to. "
                  "Rewrite it so it actually works.",
        "forbidden": [r"IMPORTANT", r"CRITICAL", r"\bagain\b", r"\bnpm\b", r"yarn", r"Button-fixed", r"Button-v2",
                      r"Button\.old", r"`any`", r"default exports?", r"NEVER EVER", r"seriously", r"READ THIS"],
        "must_keep": [r"pnpm install", r"\.nvmrc", r"Node 22", r"strict", r"@lumen", r"named functions",
                      r"pnpm typecheck", r"pnpm lint", r"pnpm test:unit", r"staging database", r"force-push",
                      r"Conventional Commits", r"\.env", r"Turborepo", r"in place"],
        "max_prohibitions": 2,
        "removed": "npm and yarn, the any type, default exports, duplicate files such as Button-fixed.tsx or "
                   "Button-v2.tsx, and the shouted repetition and reminders",
        "near_miss_fails": ["forbidden_absent", "prohibitions_within_limit", "no_corrective_framing"],
    },
    {
        "id": "banned-words",
        "target": "writer-prompt.md",
        "prompt": "The posts written from writer-prompt.md keep using the exact words the prompt bans. Fix the "
                  "prompt.",
        "forbidden": [r"delve", r"tapestry", r"testament", r"realm", r"landscape", r"leverage", r"unlock",
                      r"empower", r"elevate", r"supercharge", r"game-changer", r"cutting-edge", r"seamless",
                      r"robust", r"fast-paced", r"sink in", r"not just", "\u2014", "\U0001F680", r"#[a-z]",
                      r"ghostwriter", r"robot", r"press release", r"bad example", r"hashtag", r"emoji", r"em dash",
                      r"too (formal|casual|long)"],
        "must_keep": [r"Priya", r"Tally", r"freelanc", r"first three years", r"14 invoices", r"question",
                      r"one idea", r"\d+\s*words", r"LinkedIn", r"short paragraphs"],
        "max_prohibitions": 0,
        "removed": "every banned word and phrase, em dashes, emojis, hashtags, ghostwriting, press releases, "
                   "sounding robotic, and the bad example",
        "near_miss_fails": ["forbidden_absent"],
    },
    {
        "id": "corrective-framing",
        "target": "review-agent.md",
        "prompt": "Our PR review agent in review-agent.md keeps nitpicking style and rewriting whole files, even "
                  "though the prompt tells it not to. Fix the prompt.",
        "forbidden": [r"rewriter", r"nitpick", r"\bstyle\b", r"whole file", r"harsh", r"rude", r"what not to do"],
        "must_keep": [r"post_review_comment", r"off-by-one", r"integer cents", r"idempotency",
                      r"string concatenation", r"auth checks", r"without a test", r"blocking", r"should-fix",
                      r"`question`", r"file:line", r"10 comments", r"Prettier", r"mislead"],
        "max_prohibitions": 0,
        "removed": "rewriting code, nitpicks, style, whole-file comments, harshness, and the 'what not to do' list",
        "near_miss_fails": ["forbidden_absent", "no_corrective_framing"],
    },
    {
        "id": "competitor-removal",
        "target": "sales-assistant.md",
        "prompt": "Legal says the sales assistant can't talk about competitors anymore. Update sales-assistant.md "
                  "accordingly.",
        "forbidden": [r"heroku", r"\bRender\b", r"fly\.io", r"compar", r"competit", r"rival",
                      r"(other|another|alternative) (hosting )?(providers?|platforms?|vendors?|services?|companies)",
                      r"alternatives?"],
        "must_keep": [r"Starter", r"\$19", r"\$99", r"Enterprise", r"SSO", r"99\.95%", r"15%", r"create_lead",
                      r"100 words", r"northwind\.dev/docs", r"preview environments", r"Rails and Django"],
        "max_prohibitions": 0,
        "removed": "competitors, the comparison table, and any mention that the assistant avoids other providers",
        "near_miss_fails": ["forbidden_absent"],
    },
    {
        # The control. Every prohibition here is a hard limit with a reason and
        # a fallback, so the right audit leaves them standing.
        "id": "legitimate-keeps",
        "target": "deploy-agent.md",
        "prompt": "Check deploy-agent.md for instructions that might backfire on the model, and fix anything "
                  "you find.",
        "expect_edit": False,
        "forbidden": [],
        "must_keep": [r"orbit db reset", r"terraform destroy", r"(can't|cannot) be undone|irreversib",
                      r"ask the user to run it themselves", r"secrets/", r"file name", r"16:00 UTC on Friday",
                      r"09:00 UTC on Monday", r"on call", r"schedule the deploy", r"canary 10", r"15 minutes",
                      r"1%", r"orbit rollback", r"post_update"],
        "max_prohibitions": 3,
        "removed": "nothing: every prohibition in this file is an irreversible, security, or hard-limit constraint "
                   "with a reason and a fallback, and should stay",
        "near_miss_fails": ["kept_content"],
    },
]


def read_case(case: dict, which: str) -> str:
    """Read a case's input, oracle, or near_miss file from fixtures/cases/<id>/."""
    return read_fixture(f"cases/{case['id']}/{which}.md")


def case_workspace(case: dict) -> dict[str, str]:
    """The files waiting in the folder when the agent arrives."""
    return {case["target"]: read_case(case, "input"), BYSTANDER: read_fixture(f"cases/{BYSTANDER}")}


def audit_prompt(case: dict, slash_command: str | None = None) -> str:
    """Build the request for one case.

    The request never names the skill. When the skill is manual-only, the
    with-skill arm gets the slash command in front, the way a real user has
    to invoke it, and the without-skill arm gets the bare request.
    """
    return f"/{slash_command} {case['prompt']}" if slash_command else case["prompt"]
