"""Shared infrastructure for every eval in run_evals.py.

This module defines the infrastructure that every eval uses:
configuration constants, display helpers, the agent runner, and the
marker. Import it with ``from eval_kit import *`` at the top of a
session and then override the config via ``eval_kit.SKILL_DIR = ...``
before running any eval.
"""
import asyncio
import json
import logging
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import ClassVar, TypeVar

import yaml
from claude_agent_sdk import ClaudeAgentOptions, query
from claude_agent_sdk.types import (
    AssistantMessage,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ToolUseBlock,
)
from pydantic import BaseModel, Field, ValidationError
from rich import box
from rich.console import Console
from rich.highlighter import RegexHighlighter
from rich.logging import RichHandler
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table
from rich.theme import Theme

# ---------------------------------------------------------------------------
# Paths — all relative to this file, which sits in the project root.
# ---------------------------------------------------------------------------

HERE = Path(__file__).parent
SKILL_DIR = HERE / ".staged" / "pink-elephant"
FIXTURES_DIR = HERE / "fixtures"
RESULTS_DIR = HERE / "results"
LOGS_DIR = HERE / "logs"

# ---------------------------------------------------------------------------
# Configuration — override in the notebook: eval_kit.AGENT_MODEL = "..."
# ---------------------------------------------------------------------------

AGENT_MODEL = os.environ.get("EVAL_MODEL") or "claude-opus-5"
JUDGE_MODEL = os.environ.get("EVAL_JUDGE_MODEL") or os.environ.get("EVAL_MODEL") or "claude-sonnet-5"
# low, medium, high, xhigh or max. Unset leaves Claude Code's default.
EFFORT = os.environ.get("EVAL_EFFORT") or None
DEFAULT_TOOLS: list[str] = ["Skill", "Read", "Bash"]

# Claude Code bills ANTHROPIC_API_KEY ahead of a subscription login whenever it
# can see the key, and every claude process started here inherits this
# environment. So the key is dropped unless EVAL_USE_API_KEY=1 asks for it.
if os.environ.get("EVAL_USE_API_KEY") != "1":
    os.environ.pop("ANTHROPIC_API_KEY", None)
# The SDK waits this many milliseconds for a claude process to start, 60
# seconds by default. Several starting at once on a busy machine take longer.
os.environ.setdefault("CLAUDE_CODE_STREAM_CLOSE_TIMEOUT", "300000")

# ---------------------------------------------------------------------------
# Logging and display
# ---------------------------------------------------------------------------

log = logging.getLogger("skill_eval")


class EvalHighlighter(RegexHighlighter):
    """Colours the words worth catching your eye in a log line.

    Good news green, bad news red, everything else tinted by what sort of thing
    it is. A wall of scrolling text keeps some shape that way. Only the
    terminal gets colour. The file in logs/ stays plain, because you will grep
    it later and colour codes make terrible search terms.
    """

    base_style = "eval."
    highlights: ClassVar[list[str]] = [
        r"(?P<good>\b(PASS|ok|passes|helps|safe|True)\b)",
        r"(?P<bad>\b(FAIL|FAILED|MISMATCH|DROPPED|ERROR|REJECT|harms|False)\b|do not install)",
        r"(?P<tool>\btool call \d+: \w+)",
        r"(?P<arm>\bWITH skill \S+|\bWITHOUT skill\b|\b(with|without)_skill\b|\bbaseline\b|\bwith-skill\b)",
        r"(?P<case>\b(case|pair|pairwise|rubric grading|fast judge on) [\w-]+)",
        r"(?P<num>\$\d+\.\d+|\b\d+\.\d+s\b|\b\d+ turns\b|\b\d+ rows\b)",
        r"(?P<skill>the agent loaded the skill|installed [\w-]+ into)",
    ]


THEME = Theme({
    "eval.good": "bold green",
    "eval.bad": "bold red",
    "eval.tool": "cyan",
    "eval.arm": "magenta",
    "eval.case": "bold yellow",
    "eval.num": "bright_blue",
    "eval.skill": "bold cyan",
})


class _ConsoleFilter(logging.Filter):
    """Keeps records tagged file_only out of the terminal.

    section() draws a divider on screen and writes one into the log file.
    Without this filter you would see the same divider twice. That looks like
    a bug, and is somehow more annoying than one.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        return not getattr(record, "file_only", False)


def configure_logging(log_name: str) -> None:
    """Turn on the commentary: colour on screen, plain text in a file.

    Every eval calls this first. At the normal setting you watch every agent
    run, every tool it reached for and every marking decision go past. Set
    SKILL_EVAL_LOG=debug and you also get the full prompts, the full replies
    and every argument handed to every tool. It is a lot of text. It is also
    the fastest way to work out what happened when a run goes sideways.

    Args:
        log_name: The eval's log name, such as 01_structural_lint. It names the
            log file, so 09_statistics ends up in logs/09_statistics.log.

    Example:
        configure_logging("09_statistics")
    """
    level = logging.DEBUG if os.environ.get("SKILL_EVAL_LOG", "").lower() == "debug" else logging.INFO
    LOGS_DIR.mkdir(exist_ok=True)

    console = RichHandler(
        console=Console(theme=THEME, stderr=True),
        highlighter=EvalHighlighter(),
        show_path=False,
        log_time_format="%H:%M:%S",
        rich_tracebacks=True,
    )
    console.setFormatter(logging.Formatter("%(message)s"))
    console.addFilter(_ConsoleFilter())

    file = logging.FileHandler(LOGS_DIR / f"{log_name}.log", mode="w")
    file.setFormatter(logging.Formatter("%(asctime)s %(levelname)-5s %(message)s", datefmt="%H:%M:%S"))

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)
    root.addHandler(console)
    root.addHandler(file)
    # The libraries underneath announce every network request they make. Left
    # alone they bury the story you are trying to follow. So they stay quiet
    # unless you asked for debug output.
    for noisy in ("claude_agent_sdk", "typesafe_sdk", "httpx", "httpx2"):
        logging.getLogger(noisy).setLevel(logging.DEBUG if level == logging.DEBUG else logging.WARNING)
    # asyncio warns about an "unknown child process" now and then when a
    # finished claude process gets tidied away. The run itself is fine, and
    # in a stored output the warning reads like a failure. So it stays quiet.
    logging.getLogger("asyncio").setLevel(logging.ERROR)
    log.info("starting %s. You will see %s-level detail here, and everything in logs/%s.log",
             log_name, logging.getLevelName(level), log_name)


out = Console()


def section(title: str) -> None:
    """Draw a labelled line across the screen to mark a new scene.

    Without these, one run's tool calls run straight into the next one's. The
    whole thing becomes a wall of text you stop reading.

    Args:
        title: A short label for whatever is about to happen.

    Example:
        section("case api-paging attempt 0")
    """
    out.print()
    out.rule(f"[bold]{escape(title)}", style="grey50", align="left")
    log.info("---- %s ----", title, extra={"file_only": True})


def table(title: str, columns: list[str], rows: list[list]) -> None:
    """Print the findings as a table.

    Values get tidied on the way in. True and False turn into a green "pass"
    and a red "FAIL". Decimals get two places. Anything missing shows as a
    dash rather than the word None, which always looks like a bug.

    Args:
        title: The caption above the table.
        columns: The headings, left to right.
        rows: One list of values per row, in the same order as the columns.

    Example:
        table("findings", ["level", "rule"], [["error", "name_required"]])
    """
    t = Table(title=title, title_justify="left", title_style="bold", box=box.SIMPLE_HEAVY,
              header_style="bold", show_edge=False, pad_edge=False)
    for column in columns:
        t.add_column(column)
    for row in rows:
        t.add_row(*(_cell(value) for value in row))
    out.print(t)


def _cell(value) -> str:
    """Turn one value into something worth looking at.

    Args:
        value: Anything a row might be carrying.

    Returns:
        The text for that cell. True and False become "pass" and "FAIL", a
        missing value becomes a dash, decimals get two places, and anything
        else is shown exactly as it came in.
    """
    if isinstance(value, bool):
        return "[bold green]pass[/]" if value else "[bold red]FAIL[/]"
    if value is None:
        return "[dim]-[/]"
    if isinstance(value, float):
        return f"{value:.2f}"
    return escape(str(value))


def headline(text: str, good: bool | None = None) -> None:
    """Print the one line you should walk away with, in a box.

    If a reader takes nothing else from an eval, they take this. Write it as
    a sentence a person could say out loud, not as a score.

    Args:
        text: The thing to take away, in full sentences where you can.
        good: True for good news, which gets a green box. False for bad news,
            which gets red. Leave it out for a plain number worth knowing,
            which gets blue.

    Example:
        headline("nothing that has to be fixed, 2 suggestions", good=True)
    """
    colour = {True: "green", False: "red", None: "blue"}[good]
    out.print(Panel(escape(text), border_style=colour, expand=False))
    log.info("headline: %s", text, extra={"file_only": True})


def note(text: str) -> None:
    """Print a quiet aside under a table or a headline.

    Args:
        text: The short version of something you would say over someone's
            shoulder. Caveats and pointers live here. Findings do not.
    """
    out.print(f"[dim]{escape(text)}[/]")


def show_text(title: str, text: str, colour: str = "grey50") -> None:
    """Put a block of text on screen in a labelled box.

    This is how the request to the agent, and the answer back, get shown.
    Reading the actual words turns a number into something you can believe.
    It is also how you catch the day your marker is wrong and the agent was
    right.

    Args:
        title: What to call the box, such as "the agent's reply".
        text: The text itself. Nothing at all shows as "(empty)".
        colour: The border colour. Grey is the neutral default.
    """
    out.print(Panel(escape(text.strip() or "(empty)"), title=title, border_style=colour, title_align="left"))
    log.info("%s:\n%s", title, text, extra={"file_only": True})


def show_pair(left_title: str, left: str, right_title: str, right: str) -> None:
    """Put two blocks of text side by side.

    The answer with the skill on the left, the answer without it on the right.
    Stacked, you have to remember the first while reading the second. You will
    not. Side by side, the difference is just there.

    Args:
        left_title: What to call the left box.
        left: The text for the left box.
        right_title: What to call the right box.
        right: The text for the right box.
    """
    t = Table.grid(expand=True, padding=(0, 1))
    t.add_column(ratio=1)
    t.add_column(ratio=1)
    t.add_row(Panel(escape(left.strip() or "(empty)"), title=left_title, border_style="green", title_align="left"),
              Panel(escape(right.strip() or "(empty)"), title=right_title, border_style="magenta", title_align="left"))
    out.print(t)
    log.info("%s:\n%s\n%s:\n%s", left_title, left, right_title, right, extra={"file_only": True})


EXPLAIN_TITLES = {
    "next": "what happens next",
    "meaning": "what this means",
    "reading": "how to read this",
}


def explain(text: str, kind: str = "next") -> None:
    """Narrate what is going on, in a yellow box, while it goes on.

    These evals are meant to be watched, not just run. So the narration
    lives in the output, not in a comment nobody scrolls to. Three kinds:

      next     what is about to happen, and why it is worth doing
      meaning  what the thing that just appeared tells you
      reading  how to make sense of the table coming up

    Once you know the material and only want the numbers, set
    SKILL_EVAL_EXPLAIN=0 and the boxes stop.

    Args:
        text: The explanation, in plain sentences.
        kind: One of "next", "meaning" or "reading". It picks the box title.

    Example:
        explain("Both sides passed, so the skill bought you nothing here.",
                kind="meaning")
    """
    if os.environ.get("SKILL_EVAL_EXPLAIN", "1") == "0":
        return
    title = EXPLAIN_TITLES[kind]
    out.print(Panel(escape(text), title=title, title_align="left", border_style="yellow"))
    log.info("%s: %s", title, text, extra={"file_only": True})


# ---------------------------------------------------------------------------
# Skill loader
# ---------------------------------------------------------------------------

class Skill(BaseModel):
    """A SKILL.md file, taken apart into its pieces.

    Every record in this notebook is a Pydantic model, for two reasons. The
    field descriptions are the documentation, and they sit next to the data
    instead of in a README that stopped being true in March. And a record that
    does not match its model fails the moment it is built, not three steps
    later as a puzzling number you chase for an hour.
    """

    name: str = Field(description="The skill's id, taken from the top of SKILL.md. Must match the folder name.")
    description: str = Field(
        description="What the skill does and when to use it. This one sentence is all Claude Code has to go on "
                    "when it decides whether to open the skill.")
    frontmatter: dict = Field(description="Every setting from the YAML block at the top of SKILL.md.")
    body: str = Field(
        description="The markdown instructions below the settings block. The model does not see a word of this "
                    "until the skill has already been opened.")
    path: Path = Field(description="The folder that holds SKILL.md.")


def load_skill(skill_dir: Path = SKILL_DIR) -> Skill:
    """Open a SKILL.md and take it apart.

    The file comes in two halves. A settings block written in YAML, fenced off
    by a pair of '---' lines, and then the instructions in markdown underneath.

    Args:
        skill_dir: The folder holding SKILL.md.

    Returns:
        A Skill with the settings and the instructions separated.

    Raises:
        ValueError: There is no settings block to split on.
        KeyError: The settings block left out name or description.

    Example:
        skill = load_skill()
        print(skill.name)  # "commit-message"
    """
    text = (skill_dir / "SKILL.md").read_text()
    # Split on the first two "---" and no further. The instructions underneath
    # may have their own horizontal rules. Those must not be mistaken for the
    # end of the settings block.
    _, frontmatter_text, body = text.split("---", 2)
    frontmatter = yaml.safe_load(frontmatter_text)
    return Skill(
        name=frontmatter["name"],
        description=frontmatter["description"],
        frontmatter=frontmatter,
        body=body.strip(),
        path=skill_dir,
    )


def read_fixture(relative_path: str) -> str:
    """Fetch one of the sample inputs kept in fixtures/.

    Args:
        relative_path: The path under fixtures/, such as
            "diffs/docs_cli_readme.diff".

    Returns:
        Whatever is in the file, as text.

    Example:
        diff = read_fixture("diffs/docs_cli_readme.diff")
    """
    return (FIXTURES_DIR / relative_path).read_text()


def show_skill(skill_dir: Path = SKILL_DIR) -> None:
    """Introduce the defendant.

    Every eval opens with this, so anyone watching knows what is on trial
    before the evidence arrives. The description in that box is not a summary
    written for you. It is the exact sentence Claude Code reads when deciding
    whether to use this skill. That is why it gets a box of its own.

    Args:
        skill_dir: The folder holding SKILL.md. Defaults to the commit-message
            skill that comes with this notebook.

    Example:
        show_skill()
    """
    shown = skill_dir.relative_to(HERE) if skill_dir.is_relative_to(HERE) else skill_dir
    try:
        skill = load_skill(skill_dir)
    except (OSError, ValueError, KeyError, yaml.YAMLError):
        # The structural lint and security scan get pointed at skills that are
        # broken on purpose. Failing to read one here is usually the whole
        # point, not a disaster. Say so calmly and let the eval explain below.
        out.print(Panel(f"[dim]{escape(str(shown))}/SKILL.md[/]\n\ncould not be read. The findings below explain why",
                        title="skill under test", border_style="cyan", title_align="left"))
        log.info("skill under test: %s (the file could not be read)", shown, extra={"file_only": True})
        return
    body = (f"[bold]{escape(skill.name)}[/]   [dim]{escape(str(shown))}/SKILL.md[/]\n\n"
            f"{escape(skill.description)}")
    out.print(Panel(body, title="skill under test", border_style="cyan", title_align="left"))
    log.info("skill under test: %s (%s): %s", skill.name, shown, skill.description, extra={"file_only": True})


# ---------------------------------------------------------------------------
# Agent runner
# ---------------------------------------------------------------------------

class ToolCall(BaseModel):
    """One thing the agent did, such as reading a file or running a command."""

    name: str = Field(description="Which tool it used: Skill to open a skill, Read to read a file, Bash to run a "
                                  "shell command, and so on.")
    input: dict = Field(
        description="What it handed that tool. Bash carries 'command', Read carries 'file_path', and Skill "
                    "carries 'skill'.")
    id: str = Field(default="", description="The tool call's own id. A subagent's calls point back at it.")
    parent: str | None = Field(
        default=None,
        description="The id of the Task or Agent call that spawned the subagent making this call. None for "
                    "the main agent. Subagent work streams back on the same channel, so this is how to tell "
                    "them apart.")


class AgentRun(BaseModel):
    """Everything one run of the agent left behind.

    Marking always happens on one of these, never on a live agent. A saved run
    can be marked again next month against rules you have not written yet.
    You paid for it once.
    """

    prompt: str = Field(description="What the agent was asked to do.")
    skill_installed: bool = Field(description="Was the skill sitting there in the folder? True for the with-skill "
                                              "side of a comparison.")
    skill_invoked: bool = Field(default=False, description="Did the agent actually open it? A different question "
                                                           "from the one above. The trigger eval is about the gap between them.")
    final_text: str = Field(default="", description="The last thing the agent said. This is what gets marked.")
    tool_calls: list[ToolCall] = Field(default_factory=list,
                                       description="Everything the agent did, in order. The trajectory eval marks "
                                                   "this rather than the answer.")
    model: str = Field(default="", description="Which model served this run. Read back from the reply, not assumed "
                                               "from what we asked for.")
    num_turns: int = Field(default=0, description="How many times the agent spoke. Every turn re-reads the whole "
                                                  "conversation. That is where the money goes.")
    cost_usd: float = Field(default=0.0, description="What this run cost, in US dollars.")
    input_tokens: int = Field(default=0, description="Text the model read fresh, at full price. A token is roughly "
                                                     "three quarters of a word.")
    cache_read_tokens: int = Field(default=0, description="Text it had read before and got back cheaply. Leave this "
                                                          "out of your sums and a skill looks free when it is not.")
    cache_write_tokens: int = Field(default=0,
                                    description="Text put aside for next time. A little dearer than reading it "
                                                "fresh, much cheaper on every run after.")
    output_tokens: int = Field(default=0, description="Text the model wrote.")
    duration_ms: int = Field(default=0, description="How long the whole thing took, in milliseconds.")
    available_skills: list[str] = Field(
        default_factory=list,
        description="Skills and slash commands the session announced at start-up. A skill invoked by slash "
                    "command never makes a Skill tool call, so this is the evidence it was there to invoke.")
    files: dict[str, str | None] = Field(
        default_factory=dict,
        description="The end state of the files named in collect_files, read just before the folder is "
                    "deleted. None means the file was gone. Skills that edit files get marked on this.")
    error: str | None = Field(
        default=None, description="Filled in when the run fell over for reasons unrelated to the skill, such as "
                                  "the network dying. Marking skips these.")


def reads_skill_file(call: ToolCall) -> bool:
    """Is this action the agent opening SKILL.md by hand, with the Read tool?

    Args:
        call: One thing the agent did.

    Returns:
        True when the tool was Read and the path ends in SKILL.md.
    """
    return call.name == "Read" and "SKILL.md" in str(call.input.get("file_path", ""))


def skill_was_loaded(run: AgentRun) -> bool:
    """Decide whether the skill's instructions reached the agent at all.

    There is more than one door. Loading the skill properly, through the
    Skill tool, is the front one. But an agent that notices SKILL.md in the
    folder and reads the file has the same words in front of it. Counting
    that as a miss would score the mechanism rather than the outcome. Both
    count, and every eval uses this one definition, so the regression check never compares
    a number built one way against a number built the other.

    Args:
        run: A finished AgentRun.

    Returns:
        True if the skill's instructions reached the agent, by either route.

    Example:
        if skill_was_loaded(run): ...
    """
    return run.skill_invoked or any(reads_skill_file(c) for c in run.tool_calls)


def run_agent(
    prompt: str,
    skill_dir: Path | None = SKILL_DIR,
    workspace_files: dict[str, str] | None = None,
    model: str | None = None,
    allowed_tools: list[str] | None = None,
    max_turns: int = 8,
    git_init: bool = False,
    collect_files: list[str] | None = None,
) -> AgentRun:
    """Run Claude Code once, in a folder built fresh and thrown away after.

    Every run gets its own empty folder, destroyed the moment the run ends.
    Nothing survives to the next one. No leftover files, no history, no
    remembered answers. That clean slate is what makes two runs comparable.

    Args:
        prompt: What to ask, worded the way somebody would ask it.
        skill_dir: The folder holding the skill to install. Pass None to run
            with no skill. That is the side you compare against.
        workspace_files: Files to put in the folder first, as
            {filename: contents}. You need this when the request mentions a
            file, such as {"changes.diff": "..."} for "summarise changes.diff".
        model: Which model to use. Defaults to AGENT_MODEL.
        allowed_tools: What the agent is allowed to touch. Defaults to
            DEFAULT_TOOLS.
        max_turns: Pull the plug after this many turns, so a confused agent
            cannot spend your money all afternoon.
        git_init: Make the folder a real git repository first. Some cases are
            about what the agent did, or wisely refused to do, with git.
        collect_files: Files to read back after the run, as paths relative
            to the folder. Their contents land on AgentRun.files, so a skill
            that edits files can be marked on what it left behind.

    Returns:
        An AgentRun holding the reply, everything the agent did on the way, and
        the bill.

    Example:
        run = run_agent("Write a commit message for this diff:\\n\\n...")
        print(run.skill_invoked, run.cost_usd)
    """
    if model is None:
        model = AGENT_MODEL
    if allowed_tools is None:
        allowed_tools = list(DEFAULT_TOOLS)
    skill_name = load_skill(skill_dir).name if skill_dir else None
    arm = f"WITH skill {skill_name}" if skill_dir else "WITHOUT skill"
    log.info("running the agent %s, on %s at %s effort. The request starts: %.70r",
             arm, model, EFFORT or "default", prompt.replace("\n", " "))
    log.debug("the full request:\n%s", prompt)

    # A brand new folder for every run. Everything below is ordinary blocking
    # code. Only the back-and-forth with Claude Code has to be async.
    with tempfile.TemporaryDirectory(prefix="skill-eval-") as workspace:
        workspace = Path(workspace)
        log.debug("working folder for this run: %s", workspace)
        if skill_dir:
            # .claude/skills/ is where Claude Code looks for a project's
            # skills. So that is where a real user's skill would sit.
            shutil.copytree(skill_dir, workspace / ".claude" / "skills" / skill_name)
            log.info("  installed %s into .claude/skills/, where Claude Code will look for it", skill_name)
        for relative_path, content in (workspace_files or {}).items():
            (workspace / relative_path).write_text(content)
            log.info("  dropped %s into the folder for it to find (%d characters)", relative_path, len(content))
        if git_init:
            subprocess.run(["git", "init", "-q"], cwd=workspace, check=True)
            subprocess.run(["git", "add", "-A"], cwd=workspace, check=True)
            log.info("  turned the folder into a git repository with everything staged. Now we see what it does "
                     "with that")
        run = asyncio.run(_run_agent_async(prompt, workspace, skill_name, model, allowed_tools, max_turns))
        for relative_path in collect_files or []:
            target = workspace / relative_path
            run.files[relative_path] = target.read_text() if target.exists() else None
        return run


async def _run_agent_async(prompt: str, workspace: Path, skill_name: str | None, model: str,
                           allowed_tools: list[str], max_turns: int) -> AgentRun:
    """Have the actual conversation, in the folder run_agent just built.

    Args:
        prompt: What to ask.
        workspace: The folder, already prepared.
        skill_name: The installed skill's name, or None if there isn't one.
        model: Which model to use.
        allowed_tools: What the agent is allowed to touch.
        max_turns: The hard stop on turns.

    Returns:
        An AgentRun put together from every message that came back.
    """
    options = ClaudeAgentOptions(
        cwd=workspace,
        model=model,
        # "project" means take settings from this folder and nowhere else. Your
        # own global settings are shut out on purpose. Otherwise the personal
        # skills and plugins you have collected could wander into the
        # experiment and change the answer. Same for MCP servers. None here,
        # none from your account.
        setting_sources=["project"],
        mcp_servers={},
        strict_mcp_config=True,
        allowed_tools=allowed_tools,
        # The folder is deleted the moment this finishes. Nothing in it needs
        # protecting, so there is no reason to ask permission before every
        # command.
        permission_mode="bypassPermissions",
        max_turns=max_turns,
        effort=EFFORT,
    )

    run = AgentRun(prompt=prompt, skill_installed=skill_name is not None, model=model)
    started = time.monotonic()

    # >>> THIS IS THE REAL THING. query() starts the `claude` program as a
    #     separate process, points it at the folder we just built, hands it the
    #     request and streams back every message. Every number in every table
    #     in this folder comes out of the loop below.
    try:
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, SystemMessage) and message.subtype == "init":
                data = message.data or {}
                run.available_skills = sorted({str(s).lstrip("/") for s in
                                               [*data.get("skills", []), *data.get("slash_commands", [])]})
            elif isinstance(message, AssistantMessage):
                parent = getattr(message, "parent_tool_use_id", None)
                if parent is None:
                    run.model = message.model
                for block in message.content:
                    if isinstance(block, ToolUseBlock):
                        run.tool_calls.append(ToolCall(name=block.name, input=block.input, id=block.id,
                                                       parent=parent))
                        log.info("  tool call %d: %s %s", len(run.tool_calls), block.name,
                                 _summarise_input(block.input))
                        log.debug("  what it was given: %s", block.input)
                        if block.name == "Skill" and block.input.get("skill") == skill_name:
                            run.skill_invoked = True
                            log.info("  the agent loaded the skill")
                    elif isinstance(block, TextBlock) and parent is None:
                        # An agent says several things on its way to an answer.
                        # "Let me read that file first", some thinking out loud,
                        # then the answer. The last thing it says is what counts.
                        run.final_text = block.text
            elif isinstance(message, ResultMessage):
                run.num_turns = message.num_turns
                run.cost_usd = message.total_cost_usd or 0.0
                usage = message.usage or {}
                # All four counts, straight from the API, not guessed. Record only
                # input_tokens and you miss the reused instructions. Those are
                # most of what a run reads.
                run.input_tokens = usage.get("input_tokens", 0)
                run.cache_read_tokens = usage.get("cache_read_input_tokens", 0)
                run.cache_write_tokens = usage.get("cache_creation_input_tokens", 0)
                run.output_tokens = usage.get("output_tokens", 0)
                if message.is_error:
                    run.error = f"{message.subtype}: {message.result or message.errors}"
    except Exception as exc:  # The SDK raises bare Exception for a start-up timeout.
        # The network died, or the claude program did. That is news about your
        # setup, not your skill. Write it on the run and hand the run back, so
        # the runs before it stay paid for and the ones after it still happen.
        run.error = f"{type(exc).__name__}: {exc}"

    run.duration_ms = int((time.monotonic() - started) * 1000)
    if run.error:
        log.warning("  this one fell over before it finished: %s", run.error)
    log.info("  done in %.1fs, %d turns. Skill loaded: %s. That cost $%.4f. The answer starts: %.60r",
             run.duration_ms / 1000, run.num_turns, run.skill_invoked, run.cost_usd,
             run.final_text.replace("\n", " "))
    log.debug("the full answer:\n%s", run.final_text)
    return run


def _summarise_input(tool_input: dict) -> str:
    """Pull out the one detail from a tool call worth putting in the log.

    Args:
        tool_input: Whatever the agent handed to the tool.

    Returns:
        The command, file path or skill name, on one line and cut off at 80
        characters. Empty when there was nothing interesting.
    """
    detail = tool_input.get("command") or tool_input.get("file_path") or tool_input.get("skill") or ""
    return str(detail).replace("\n", " ")[:80]


# ---------------------------------------------------------------------------
# Saving and loading results
# ---------------------------------------------------------------------------

def save_jsonl(path: Path, rows: list[BaseModel | dict]) -> None:
    """Write the findings down, one JSON object per line.

    The format is boring on purpose. One record per line. You can grep it,
    append to it, open it in anything, and mark it again next month without
    running an agent. The rows are usually Pydantic models, so their field
    descriptions double as documentation for whoever opens the file next.
    That will probably be you, having forgotten all of this.

    Args:
        path: Where to write it. Missing folders get created.
        rows: The records to keep.

    Example:
        save_jsonl(RESULTS_DIR / "06_ab_runs.jsonl", rows)
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for row in rows:
            data = row.model_dump(mode="json") if isinstance(row, BaseModel) else row
            f.write(json.dumps(data) + "\n")
    log.info("wrote %d rows to %s. You never have to pay for those runs again", len(rows), path.relative_to(HERE))


def load_jsonl(path: Path) -> list[dict]:
    """Read back what save_jsonl() wrote.

    Args:
        path: The file to read.

    Returns:
        One dictionary per line that had anything on it.
    """
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def results_from(producer: str, filename: str) -> Path:
    """Fetch a results file, or say which eval makes it if it is missing.

    The cheap evals read rows an expensive one saved earlier. If the file is
    missing, this stops and names the eval to run, instead of quietly
    spending money on your behalf.

    That reuse is the habit this notebook is trying to teach. Agent runs cost
    money and minutes. Pay once, then mark them as often as you like, against
    rules you have not thought of yet.

    Args:
        producer: The eval that makes the file, such as "the A/B comparison (run_evals.py ab)".
        filename: What it is called inside results/.

    Returns:
        The path, now definitely pointing at a file that exists.

    Raises:
        FileNotFoundError: The file is not there yet. Run the producer first.

    Example:
        path = results_from("the A/B comparison (run_evals.py ab)", "06_ab_runs.jsonl")
    """
    path = RESULTS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"there is no results/{filename} yet, so {producer} has to run first. That one "
                                "spends real money.")
    return path


# ---------------------------------------------------------------------------
# Asking the marker
# ---------------------------------------------------------------------------

Reply = TypeVar("Reply", bound=BaseModel)


def ask_model(prompt: str, response_model: type[Reply], model: str | None = None) -> Reply | None:
    """Put one question to a model and make it answer in a shape you chose.

    This is what the evals use when one model marks another model's
    homework. The marker gets no tools, no conversation and no room to
    improvise. Just the question and the shape its answer has to fit.

    The fixed shape matters. Let a marker reply in prose and you end up
    fishing a score out of a paragraph with string matching. That is where
    quiet marking bugs live. So the shape goes to the API up front, and the
    reply gets checked against it on the way back.

    It all goes through Claude Code, like everything else here, so it works
    with an ordinary Claude Code login. With an API key you could call the API
    directly and not a single number would change.

    Args:
        prompt: The question, with whatever is being marked inside it.
        response_model: The shape the answer has to fit, as a Pydantic model.
        model: Which model to ask. Defaults to JUDGE_MODEL, which is
            deliberately not the model being tested.

    Returns:
        The answer, already checked against response_model. None when the
        model produced something unusable. The caller counts that as a fail
        instead of waving it through.

    Example:
        reply = ask_model("Grade this...", RubricReply)
        if reply is None:
            ...  # count it as a fail
    """
    if model is None:
        model = JUDGE_MODEL
    log.info("asking the marker, %s. The question is %d characters long. The answer has to fit %s",
             model, len(prompt), response_model.__name__)
    log.debug("the full question put to the marker:\n%s", prompt)
    result = asyncio.run(_ask_model_async(prompt, model, response_model.model_json_schema()))
    if not result or result.structured_output is None:
        log.warning("  nothing usable came back from the marker, so this counts as a fail")
        return None
    try:
        reply = response_model.model_validate(result.structured_output)
    except ValidationError as exc:
        # The answer came back, but not in the shape that was asked for. Same
        # rule as above. An unusable answer is a fail, never a crash and never
        # a pass.
        log.warning("  the marker answered in the wrong shape, so this counts as a fail: %s", exc)
        return None
    log.info("  the marker says: %.100s", reply.model_dump_json())
    return reply


async def _ask_model_async(prompt: str, model: str, output_schema: dict) -> ResultMessage | None:
    """Ask the question, with no tools allowed and the answer shape enforced.

    Args:
        prompt: The question.
        model: Which model to ask.
        output_schema: The shape the answer has to satisfy, as JSON schema.

    Returns:
        The last message the model sent, or nothing if the call fell over.
    """
    # Getting an answer into the right shape takes Claude Code an extra turn or
    # two. Allow only one and it fails at random. Three is plenty when there
    # are no tools to get distracted by.
    result = None
    # An empty folder, so no AGENTS.md or CLAUDE.md from this repository is in
    # reach of the marker.
    with tempfile.TemporaryDirectory(prefix="skill-eval-judge-") as empty:
        options = ClaudeAgentOptions(cwd=empty, model=model, effort=EFFORT, setting_sources=[], allowed_tools=[],
                                     tools=[], mcp_servers={}, strict_mcp_config=True, max_turns=3,
                                     output_format={"type": "json_schema", "schema": output_schema})
        try:
            # >>> THIS IS THE REAL THING. The marker runs here, through the same
            #     Claude Code program as everything else, but with nothing to
            #     reach for and a required shape for its answer.
            async for message in query(prompt=prompt, options=options):
                if isinstance(message, ResultMessage):
                    result = message
        except Exception as exc:  # The SDK raises bare Exception for a start-up timeout.
            # A marker that crashes is telling you about your setup, not your
            # skill. Say so and let the caller count it as a fail, rather than
            # taking the whole run down.
            log.warning("  the call to the marker model fell over: %s", exc)
    return result
