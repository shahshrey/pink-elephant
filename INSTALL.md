# Install

Pick your agent below. The skill is one folder, [`skills/pink-elephant/`](skills/pink-elephant/): [`SKILL.md`](skills/pink-elephant/SKILL.md) plus [`hunters.md`](skills/pink-elephant/hunters.md), [`modes.md`](skills/pink-elephant/modes.md), and [`examples.md`](skills/pink-elephant/examples.md). Any agent that loads Agent Skills can install that folder as the skill. The repo also ships a five-point always-on [companion rule](#companion-rule), [`AGENTS.md`](AGENTS.md), for agents that read `AGENTS.md` or a rules file. Agent not listed? Copy the skill folder into its skills directory, or copy `AGENTS.md` into your project.

The audit dispatches parallel subagents, using the `Task` tool in Cursor and Claude Code. In an agent without a subagent tool, it runs each reviewer as its own pass in the same session, one after another. You get the same result. It just takes longer.

The skill runs when you invoke it by name. `disable-model-invocation: true` in `SKILL.md` sets that for Claude Code, Cursor, and OpenClaw; `agents/openai.yaml` sets it for Codex, and the `opencode/autoinvoke` metadata for OpenCode. Other hosts may also pick the skill on their own when a task matches its description.

Pink Elephant has no hooks and no persistent modes, so every install below is a skill, a rule file, or both. Each section carries one of these labels:

- **Verified**: run end to end against this repo.
- **Unverified**: follows the host's documentation and the manifest format it publishes, but hasn't been run against this repo yet.
- **After publishing**: works once I publish to that registry. [Publishing](#publishing) has the steps.

Right now only the Cursor clone install is verified. The rest is my best reading of each host's docs, so expect the odd rough edge.

## Claude Code

*Unverified.* As a plugin, in two separate prompts:

```
/plugin marketplace add shahshrey/pink-elephant
```
```
/plugin install pink-elephant@pink-elephant
```

The same two commands work in the Code tab of the Claude Code desktop app. Plugin skills are namespaced by plugin, so the skill runs as `/pink-elephant:pink-elephant`. The plugin loads the skill from `skills/`, the default folder in the [plugin manifest reference](https://code.claude.com/docs/en/plugins-reference).

As a personal skill, which runs as `/pink-elephant`, copy the skill folder out of a clone:

```bash
git clone https://github.com/shahshrey/pink-elephant ~/src/pink-elephant
cp -R ~/src/pink-elephant/skills/pink-elephant ~/.claude/skills/
```

To update, `git pull` in the clone and copy the folder again. The [skills CLI](#skills-cli) does the same in one command.

**CodeBuddy** reads the Claude manifests and installs the same plugin with the same two `/plugin` commands. *Unverified.*

## Cursor

*Verified* for a clone straight into the skills folder:

```bash
git clone https://github.com/shahshrey/pink-elephant ~/.cursor/skills/pink-elephant
```

Cursor walks `~/.cursor/skills/` recursively, so it finds `skills/pink-elephant/SKILL.md` inside the clone. It also finds the five test skills under `evals/fixtures/catalog/`, and those show up in your skill list too. That's the cost of the one-line install. Update with `git pull` inside that folder.

To install only the skill, copy it out of a clone kept elsewhere:

```bash
git clone https://github.com/shahshrey/pink-elephant ~/src/pink-elephant
cp -R ~/src/pink-elephant/skills/pink-elephant ~/.cursor/skills/
```

The plugin route also installs the companion rule as an always-on rule. In Cursor, open **Customize**, import from a GitHub repository, and paste `https://github.com/shahshrey/pink-elephant`. The repo carries [`.cursor-plugin/marketplace.json`](.cursor-plugin/marketplace.json) for this import. *Unverified.*

Run `/pink-elephant` in a new chat.

## Codex

*Unverified.* As a plugin, for Codex CLI and the Codex desktop app:

```bash
codex plugin marketplace add shahshrey/pink-elephant
codex plugin add pink-elephant@pink-elephant
```

Restart the desktop app after installing. The marketplace is [`.agents/plugins/marketplace.json`](.agents/plugins/marketplace.json) and the plugin is [`.codex-plugin/plugin.json`](.codex-plugin/plugin.json).

As a plain skill, Codex reads personal skills from `~/.agents/skills/` and follows symlinks there:

```bash
git clone https://github.com/shahshrey/pink-elephant ~/src/pink-elephant
ln -s ~/src/pink-elephant/skills/pink-elephant ~/.agents/skills/pink-elephant
```

Mention it with `$pink-elephant`, or pick it from `/skills`. [`agents/openai.yaml`](skills/pink-elephant/agents/openai.yaml) keeps Codex from starting it on its own. Codex, including the VS Code Codex extension, also reads `AGENTS.md`; see [Companion rule](#companion-rule).

## GitHub Copilot CLI

*Unverified.*

```bash
copilot plugin marketplace add shahshrey/pink-elephant
copilot plugin install pink-elephant@pink-elephant
```

Inside an interactive session, send the same commands as `/plugin marketplace add ...` and `/plugin install ...`. Copilot CLI namespaces plugin skills, so the audit runs as `/pink-elephant:pink-elephant`. The manifests are in [`.github/plugin/`](.github/plugin/).

For the companion rule alone, Copilot CLI reads `AGENTS.md` and `.github/copilot-instructions.md` in a project, and `~/.copilot/copilot-instructions.md` for every project.

## Gemini CLI

*Unverified.*

```bash
gemini extensions install https://github.com/shahshrey/pink-elephant
```

The extension loads `AGENTS.md` as always-on context, ships the skill from `skills/`, and adds a `/pink-elephant` command that runs it with your arguments. That command lives in [`commands/pink-elephant.toml`](commands/pink-elephant.toml). Restart Gemini CLI after installing.

**Qwen Code** installs the same extension through its Gemini compatibility: `qwen extensions install shahshrey/pink-elephant:pink-elephant`. *Unverified.*

## Pi

*Unverified.*

```bash
pi install git:github.com/shahshrey/pink-elephant
```

Pi reads the `pi` key in [`package.json`](package.json), which points at `skills/`. *After publishing* to npm, `pi install npm:pink-elephant` works too.

## Oh My Pi (omp)

*Unverified.*

```bash
omp plugin marketplace add shahshrey/pink-elephant
omp plugin install pink-elephant@pink-elephant
```

Start a new session after installing.

## Kimi Code

*Unverified.* In Kimi Code, run `/plugins install https://github.com/shahshrey/pink-elephant`, then `/reload` or start a new session. [`.kimi-plugin/plugin.json`](.kimi-plugin/plugin.json) adds the skill, which Kimi also offers as `/pink-elephant`, and puts `AGENTS.md` into the system prompt every turn.

## OpenCode

*Unverified.* OpenCode loads skills from plain folders, so no plugin code is needed. Install the skill with the [skills CLI](#skills-cli):

```bash
npx skills add shahshrey/pink-elephant --skill pink-elephant --agent opencode --global
```

Or copy it into OpenCode's global skills folder:

```bash
git clone https://github.com/shahshrey/pink-elephant ~/src/pink-elephant
cp -R ~/src/pink-elephant/skills/pink-elephant ~/.config/opencode/skills/
```

The skill's `opencode/slash` metadata exposes it as `/pink-elephant` in the TUI. OpenCode also reads `AGENTS.md` from the project root for the companion rule.

**Kilo Code** is built on OpenCode, so install with `--agent kilo`. Kilo reads `AGENTS.md` from the project root or `~/.config/kilo/AGENTS.md`. *Unverified.*

## Qoder

*Unverified.* As a plugin: `qodercli plugins install https://github.com/shahshrey/pink-elephant`. [`.qoder-plugin/plugin.json`](.qoder-plugin/plugin.json) adds the skill from `skills/` and the companion rule from [`.qoder/rules/`](.qoder/rules/).

Without the plugin, Qoder reads `AGENTS.md` from the project root; for a per-project rule, copy [`.qoder/rules/pink-elephant.md`](.qoder/rules/pink-elephant.md) into your project's `.qoder/rules/`.

## Antigravity

*Unverified.* Antigravity CLI:

```bash
agy plugin install https://github.com/shahshrey/pink-elephant
```

That installs the skill, and Antigravity [turns skills into slash commands](https://www.antigravity.google/docs/skills#slash-command-conversion), so it runs as `/pink-elephant`. The Antigravity IDE [reads `AGENTS.md`](https://www.antigravity.google/docs/rules) as workspace rules, and it reads `.agents/rules/` too. Copy `AGENTS.md` or [`.agents/rules/pink-elephant.md`](.agents/rules/pink-elephant.md) into your project.

## Hermes Agent

*Unverified.*

```bash
hermes plugins install shahshrey/pink-elephant --enable
```

Or clone it into the plugins folder and enable it:

```bash
git clone https://github.com/shahshrey/pink-elephant.git ~/.hermes/plugins/pink-elephant
hermes plugins enable pink-elephant
```

Restart Hermes after installing. [`plugin.yaml`](plugin.yaml) declares the plugin, and [`__init__.py`](__init__.py) registers the skill as `pink-elephant:pink-elephant`; it adds no hooks or commands.

## Devin CLI

*Unverified.*

```bash
devin plugins install shahshrey/pink-elephant
```

The skill runs as `/pink-elephant:pink-elephant`.

## Grok Build

*Unverified.*

```bash
grok plugin install shahshrey/pink-elephant --trust
```

Plugins start disabled. Enable it in `/plugins` by pressing Space on `pink-elephant`, or in `~/.grok/config.toml`:

```toml
[plugins]
enabled = ["pink-elephant"]
```

Start a new session; the skill shows as `/pink-elephant`. Check with `grok inspect`. Grok reads [`.grok-plugin/marketplace.json`](.grok-plugin/marketplace.json), which points at `skills/`.

## Goose

*Unverified.*

```bash
goose plugin install https://github.com/shahshrey/pink-elephant.git
```

That imports the skill as `pink-elephant:pink-elephant`. For the companion rule, copy `AGENTS.md` into your project or to `~/.agents/AGENTS.md`.

## OpenClaw

*Unverified.* From a clone, into the shared skills folder:

```bash
git clone https://github.com/shahshrey/pink-elephant ~/src/pink-elephant
openclaw skills install ~/src/pink-elephant/skills/pink-elephant --global
```

OpenClaw honors `disable-model-invocation`, so the skill stays out of the model's prompt and runs as `/pink-elephant`. *After publishing* to ClawHub: `clawhub install pink-elephant`.

## Skills CLI

*Unverified.* The [skills CLI](https://skills.sh) copies the skill into the skills folder of the agents you pick, including Claude Code, Codex, Cursor, Gemini CLI, GitHub Copilot, OpenCode, Kilo Code, Windsurf, Cline, and Kiro CLI:

```bash
npx skills add shahshrey/pink-elephant --skill pink-elephant
```

Pick the agent with `--agent`, for example `--agent claude-code`. Add `--global` to install for your user instead of the current project. `--skill pink-elephant` selects the skill in `skills/` by name. This installs the skill only; for the always-on habit, also add the [companion rule](#companion-rule).

## More agents with a skills folder

*Unverified.* These agents load `SKILL.md` folders and read `AGENTS.md`. Copy `skills/pink-elephant/` into the folder listed, and `AGENTS.md` into your project for the companion rule.

| Agent | Skills folder | Global `AGENTS.md` |
|---|---|---|
| Cline | `.agents/skills/` in the project, or `cline skill add shahshrey/pink-elephant` | Also reads `.clinerules/`; see [Companion rule](#companion-rule) |
| Factory Droid | `.factory/skills/` or `~/.factory/skills/` | `~/.factory/AGENTS.md` |
| Command Code | `cmd skills add https://github.com/shahshrey/pink-elephant`, plus `--global` for `~/.commandcode/skills/` | Reads the project `AGENTS.md` |
| Freebuff | `.agents/skills/` or `~/.agents/skills/` | `~/.agents.md` |
| DeepSeek Harness (dsh) | `~/.agents/skills/` | `~/.dsh/AGENTS.md` |
| Muse Code | `~/.agents/skills/` | `~/.config/muse/AGENTS.md` |

## Companion rule

[`AGENTS.md`](AGENTS.md) is a five-point rule that teaches the core habit on every turn, without running the full audit: describe the behavior you want, rebuild a section when something comes out of it, state each rule once, and keep real safety limits with a reason and a fallback. It points to `/pink-elephant` for a full audit.

Copy the file that matches your agent into your project, or into the global location where the agent supports one. *Unverified* per agent; each row follows that agent's documentation.

| Agent | File | Where it goes |
|---|---|---|
| Codex (CLI, desktop, VS Code extension), Zed, CodeWhale, Amp, Jules, Goose, Kilo Code, OpenCode, Qoder, Antigravity IDE, and other agents that read `AGENTS.md` | [`AGENTS.md`](AGENTS.md) | Project root. Global copies: `~/.codex/AGENTS.md` for Codex, `~/.config/amp/AGENTS.md` for Amp, `~/.agents/AGENTS.md` for Goose |
| Cursor | [`.cursor/rules/pink-elephant.mdc`](.cursor/rules/pink-elephant.mdc) | `.cursor/rules/` in your project, with `alwaysApply: true` |
| Windsurf | [`.windsurf/rules/pink-elephant.md`](.windsurf/rules/pink-elephant.md) | `.windsurf/rules/` in your project, with `trigger: always_on` |
| Cline | [`.clinerules/pink-elephant.md`](.clinerules/pink-elephant.md) | `.clinerules/` in your project, or `~/Documents/Cline/Rules/` for every project |
| Kiro | [`.kiro/steering/pink-elephant.md`](.kiro/steering/pink-elephant.md) | `.kiro/steering/` in your project, or `~/.kiro/steering/` for every project, with `inclusion: always` |
| GitHub Copilot Chat (VS Code, JetBrains, Visual Studio) and Copilot CLI | [`.github/copilot-instructions.md`](.github/copilot-instructions.md) | `.github/` in your project. Append to an existing file |
| Qoder | [`.qoder/rules/pink-elephant.md`](.qoder/rules/pink-elephant.md) | `.qoder/rules/` in your project |
| Antigravity | [`.agents/rules/pink-elephant.md`](.agents/rules/pink-elephant.md) | `.agents/rules/` in your project |
| Aider | [`AGENTS.md`](AGENTS.md) | Load it with `aider --read AGENTS.md`, or add `read: AGENTS.md` to `.aider.conf.yml` |
| JetBrains Junie | [`AGENTS.md`](AGENTS.md) | Project root, then set Settings → Tools → Junie → Project Settings → Guidelines Path to it |
| Gemini CLI, Kimi Code | [`AGENTS.md`](AGENTS.md) | Installed by the extension or plugin above |

All eight files carry the same text. When you edit one, copy the change to the others. Nothing in the repo syncs them for you.

These files also apply to any agent working on this repo itself.

## Uninstall

| Install | Command |
|---|---|
| Claude Code and CodeBuddy plugin | `/plugin remove pink-elephant`, then `/plugin marketplace remove pink-elephant` |
| Codex plugin | `codex plugin remove pink-elephant` |
| Copilot CLI plugin | `copilot plugin uninstall pink-elephant` |
| Gemini CLI extension | `gemini extensions uninstall pink-elephant` |
| Qwen Code extension | `qwen extensions uninstall pink-elephant` |
| Pi | `pi uninstall pink-elephant` |
| Oh My Pi | `omp plugin uninstall pink-elephant@pink-elephant`, then `omp plugin marketplace remove pink-elephant` |
| Kimi Code | `/plugins` in Kimi Code, then remove pink-elephant |
| Qoder plugin | `qodercli plugins uninstall pink-elephant` |
| Antigravity CLI | `agy plugin uninstall pink-elephant` |
| Hermes Agent | `hermes plugins remove pink-elephant`, or delete `~/.hermes/plugins/pink-elephant` |
| Devin CLI | `devin plugins remove pink-elephant` |
| Grok Build | `grok plugin uninstall pink-elephant` |
| Goose | `goose plugin uninstall pink-elephant` |
| OpenClaw | `openclaw skills uninstall pink-elephant --global`, or delete `~/.openclaw/skills/pink-elephant` |
| Cursor plugin | Customize, then uninstall pink-elephant |
| Skills CLI | `npx skills remove pink-elephant`, with the same `--agent` and `--global` flags as the install |
| Copied or linked skill folder | Delete it: `~/.claude/skills/pink-elephant`, `~/.cursor/skills/pink-elephant`, `~/.agents/skills/pink-elephant`, `~/.config/opencode/skills/pink-elephant`, or the folder you copied it to |
| Companion rule | Delete the copied rule file |

The uninstall commands are *unverified*, like the installs they reverse.

## Publishing

These steps are for the repo owner, which means me. Two install routes above depend on them.

- **npm**, for `pi install npm:pink-elephant`: run `npm publish` from the repo root. `package.json` limits the package to `AGENTS.md`, `skills/`, and `LICENSE`.
- **ClawHub**, for `clawhub install pink-elephant`: run `clawhub publish ./skills/pink-elephant --slug pink-elephant --version 1.0.0`.

The Codex, Claude Code, Copilot CLI, Oh My Pi, Grok, Kimi, Qoder, Devin, Hermes, Goose, Antigravity, and Gemini installs read straight from the GitHub repo, so they work as soon as the manifests are pushed. Keep the version at the same number in every manifest when you release: `.claude-plugin/`, `.codex-plugin/`, `.cursor-plugin/`, `.github/plugin/`, `.grok-plugin/`, `.kimi-plugin/`, `.devin-plugin/`, `.qoder-plugin/`, `skills/plugin.json`, `plugin.json`, `plugin.yaml`, `package.json`, and `gemini-extension.json`.
