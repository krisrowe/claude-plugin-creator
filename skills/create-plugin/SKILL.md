---
name: create-plugin
description: Scaffold a Claude Code plugin that bundles a self-installing local MCP server with Python dependencies. Use when creating a new plugin with MCP tools, or converting an existing MCP server into a plugin, or adding plugin-native tools to an existing repo. Trigger on intent — "make this a plugin", "convert this MCP server", "add plugin support", etc.
argument-hint: [plugin-name]
disable-model-invocation: false
user-invocable: true
---

# Create Plugin

Scaffold a Claude Code plugin that bundles a local MCP server with
automatic dependency installation. No pipx, no PyPI, no manual setup
for end users — the plugin installs its own Python dependencies on
first session start.

## Quick start: scaffold a working plugin

The fastest path is to call `scaffold_plugin` to generate a complete
working skeleton, then customize it:

1. Call `scaffold_plugin` with any animal and saying — this creates
   all plugin files (plugin.json, .mcp.json, hooks, server.py, skill)
   with correct configuration.
2. Test it with `debug_plugin` — just pass a natural-language prompt.
3. Rename the sample tool and skill to match your real use case.
4. Add your logic to `server.py` and dependencies to `requirements.txt`.

The scaffold generates known-good configuration that avoids common
pitfalls (e.g., using `python3 -m pip` instead of `pip` in hooks).

For more control — converting an existing MCP server, adding plugin
support to an existing repo, or understanding the architecture — read
the detailed guide below.

## Architecture

This follows the self-installing pattern documented by Anthropic at
[Plugins reference — Persistent data directory](https://code.claude.com/docs/en/plugins-reference#persistent-data-directory).

Key concepts:
- `${CLAUDE_PLUGIN_ROOT}` — plugin install directory (read-only, changes on update)
- `${CLAUDE_PLUGIN_DATA}` — persistent directory for installed dependencies
- `SessionStart` hook — detects dependency changes, runs `python3 -m pip install -t` once
- MCP server runs via `python3` with `PYTHONPATH` pointing to installed packages

For full details on patterns, framework choice, and proxy justification,
read these supporting docs when the user asks "why" questions:

- [Plugin patterns](${CLAUDE_SKILL_DIR}/../../docs/plugin-patterns.md) — self-installing pattern, alternatives considered, orchestration
- [MCP framework](https://github.com/krisrowe/mcp/blob/main/docs/mcp-framework.md) — which MCP SDK we use and why
- [MCP proxy](https://github.com/krisrowe/mcp/blob/main/docs/mcp-proxy.md) — whether tool proxying is appropriate, with authoritative sources

## Step 1: Inspect the current repo

Before asking questions, look for these things in the current
working directory:

1. **Existing MCP server** — search Python files for `FastMCP`
   imports (`from mcp.server.fastmcp import FastMCP`)
2. **SDK / business logic layer** — look for an `sdk/` directory
   or similar module that separates logic from interface
3. **Packaging** — look for `pyproject.toml` or `setup.py`
4. **Entry points** — look for `[project.scripts]` in pyproject.toml
5. **Remote dependencies** — look for:
   - HTTP MCP client usage (`streamablehttp_client`, `ClientSession`)
   - API client libraries (`httpx`, `requests`) calling external
     services
   - Auth tokens, API keys, or credential references

Tell the user what you found. This informs the questions in step 2.

## Step 2: Decide on the approach with the user

Based on what you found, present the relevant options. Not all
repos are the same — the user needs to make informed choices.

### If no existing MCP server code → Greenfield

1. **Ask for the plugin name** if not provided as `$ARGUMENTS`.
   Use kebab-case (e.g., `my-tool`).

2. **Ask what the plugin does** — what tools it exposes, what
   services or data it works with.

3. Skip to [step 3](#step-3-create-plugin-files).

### If existing MCP server code found

Read the existing MCP server and SDK to understand the full
picture, then present the relevant questions **up front** before
generating any files.

**Question 1: What's the plugin's relationship to the existing
MCP server?**

Explain how the plugin mechanism works first: the plugin uses
`python3 -m pip install -t` to install the package into its own isolated
`site-packages` at session start, then runs the existing MCP
module via `python3 -m`. **No code duplication. No wrapper. No
second MCP layer.** The plugin replaces the *installation
mechanism* (pipx), not the code.

Then ask which of these the user wants:

- **Absorb it (plugin-only).** The plugin runs the existing MCP
  server module. Remove the standalone `[project.scripts]` entry
  point — the plugin is the only way to use these tools. Simplest
  — one installation path, no pipx needed. Choose this if only
  Claude Code will use these tools.

- **Absorb + keep standalone entry point.** The plugin runs the
  existing MCP server module AND the `[project.scripts]` entry
  point stays for non-plugin users (Gemini CLI, other MCP
  clients, manual `claude mcp add`). Same code powers both — the
  only difference is how it gets installed. The plugin uses
  `python3 -m pip install -t`; standalone users use `pipx install`. No extra
  complexity in the code, just two documented installation paths.

Tell the user explicitly: **absorb + standalone costs zero extra
code over absorb-only.** The standalone entry point already exists
in `[project.scripts]` — keeping it is just *not deleting a line*.
The plugin files are identical either way. There is no reason to
choose absorb-only unless the user actively wants to remove the
standalone path.

- **Complement it.** The plugin adds NEW tools (via a new
  `server.py`) that call the same SDK as the existing MCP server.
  The existing server stays as-is. Choose this when the plugin
  tools serve a different purpose than the existing ones.

**Question 2: Does the plugin need to talk to a remote service?**

Ask this if you found remote dependencies, OR if the user
describes tools that need external connectivity. If yes, see
[Remote service configuration](#remote-service-configuration).

### If existing SDK but no MCP server → New tools on existing SDK

The repo has business logic (SDK layer) but no MCP server. The
plugin introduces MCP tools that call the SDK.

1. **Confirm the plugin name** — default to the package or
   directory name.

2. **Discuss which SDK operations to expose as tools.** Not every
   SDK function needs a tool — focus on operations an AI agent
   would use.

3. The plugin will have a `server.py` that imports from the SDK
   and exposes tools. The SDK stays where it is. No code moves.

## Code organization principles

Regardless of the path chosen, these principles apply:

**The plugin replaces the installation mechanism, not the code.**
Instead of `pipx install <package>` → `claude mcp add <name> <cmd>`,
the plugin's SessionStart hook runs `python3 -m pip install -t` into its own
isolated `site-packages`, and `.mcp.json` runs the existing module
via `python3 -m`. Same code, same module, zero duplication.

**Tool logic lives in the SDK, not in the MCP server.** The MCP
server (whether plugin-native or standalone) is a thin wrapper
that calls SDK functions and returns results. If the repo already
follows this pattern, the plugin doesn't change it. If it doesn't,
consider refactoring before adding plugin scaffolding.

**One SDK, many entry points.** The same business logic can power:
- A Claude Code plugin (MCP via `.mcp.json`)
- A standalone stdio MCP server (for Gemini CLI, etc.)
- A CLI (`click`, `argparse`, etc.)
- An HTTP MCP server (Cloud Run, etc.)

The plugin is just another thin entry point. No code duplication.

**Skills call tools, not shells.** If a skill workflow would
require Claude to shell out to run code or logic, that's a
missing MCP tool. Add it. The plugin auto-installs the package —
the SDK is right there. Wrap any SDK function the skill needs so
the whole experience feels native. Claude should never need to
drop to bash to execute the plugin's own logic.

**If you need the tools available outside Claude Code** (e.g.,
Gemini CLI), keep the standalone entry point in `[project.scripts]`.
Both paths run the same module — different install mechanism, same
code.

## Step 3: Create plugin files

### Directory structure

Plugin files are added to the repo root, alongside any existing
files:

**Greenfield:**

```
./
├── .claude-plugin/
│   └── plugin.json
├── .mcp.json
├── hooks/
│   └── hooks.json
├── server.py              # new MCP server
├── requirements.txt       # new
├── skills/
│   └── <skill-name>/
│       └── SKILL.md
```

**Conversion / complement (existing package):**

```
./
├── .claude-plugin/
│   └── plugin.json
├── .mcp.json
├── hooks/
│   └── hooks.json
├── requirements.txt       # new
├── server.py              # only if complement path with new tools
├── skills/
│   └── <skill-name>/
│       └── SKILL.md
└── ... (existing repo files unchanged)
```

### `plugin.json`

```json
{
  "name": "<plugin-name>",
  "description": "<from step 2>",
  "version": "1.0.0"
}
```

### `requirements.txt`

**Greenfield:** List dependencies directly. Always include
`mcp>=1.0.0`. Add `pydantic`, `httpx`, etc. as needed.

**If the repo has `pyproject.toml` or `setup.py`:**

| You found | `requirements.txt` content | Why |
|-----------|---------------------------|-----|
| `pyproject.toml` with `[project.dependencies]` | `.` | `pip install -t ... .` installs the package and all its declared deps. No duplication. |
| `pyproject.toml` with an optional extra needed for MCP | `.[mcp]` | Installs the package plus the MCP-specific extras. |
| `setup.py` only | `.` | Same — `pip install .` works with `setup.py` too. |

**If no packaging exists** (standalone scripts): list deps
explicitly — `mcp>=1.0.0`, etc. Enumerate what the scripts import.

### `hooks/hooks.json`

The SessionStart hook installs dependencies on first run and when
`requirements.txt` changes:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "diff -q \"${CLAUDE_PLUGIN_ROOT}/requirements.txt\" \"${CLAUDE_PLUGIN_DATA}/requirements.txt\" >/dev/null 2>&1 || (cd \"${CLAUDE_PLUGIN_ROOT}\" && cp requirements.txt \"${CLAUDE_PLUGIN_DATA}/\" && python3 -m pip install -t \"${CLAUDE_PLUGIN_DATA}/site-packages\" -r requirements.txt) || rm -f \"${CLAUDE_PLUGIN_DATA}/requirements.txt\""
          }
        ]
      }
    ]
  }
}
```

The `cd` target is `${CLAUDE_PLUGIN_ROOT}` so that relative paths
in `requirements.txt` (like `.`) resolve against the plugin
directory where `pyproject.toml` lives.

### `.mcp.json`

**Greenfield or complement (new `server.py`):**

```json
{
  "mcpServers": {
    "<plugin-name>": {
      "command": "python3",
      "args": ["${CLAUDE_PLUGIN_ROOT}/server.py"],
      "env": {
        "PYTHONPATH": "${CLAUDE_PLUGIN_DATA}/site-packages"
      }
    }
  }
}
```

**Absorb (existing module with `main()` or `__main__` block):**

Use `python3 -m` to invoke the existing module directly. No
`server.py` needed.

```json
{
  "mcpServers": {
    "<plugin-name>": {
      "command": "python3",
      "args": ["-m", "<existing.module.path>"],
      "env": {
        "PYTHONPATH": "${CLAUDE_PLUGIN_DATA}/site-packages"
      }
    }
  }
}
```

**Standalone scripts** (no installable package, no module path):
use `${CLAUDE_PLUGIN_ROOT}/server.py` like greenfield, but copy
the existing server code into `server.py`.

### `server.py`

**Greenfield:** Create a FastMCP server using the official MCP
Python SDK (`from mcp.server.fastmcp import FastMCP`). Include
tools based on step 2.

**Complement (new tools on existing SDK):** Create a new FastMCP
server that imports from the existing SDK:

```python
"""Plugin MCP server — new tools backed by existing SDK."""

from mcp.server.fastmcp import FastMCP
from mypackage.sdk.some_module import some_function

mcp = FastMCP("<plugin-name>")

@mcp.tool()
def my_tool(arg: str) -> dict:
    """Tool description."""
    return some_function(arg)

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

**Absorb:** No `server.py` needed — `.mcp.json` invokes the
existing module directly via `python3 -m`.

### `.gitignore` additions

If the repo has a `.gitignore`, ensure plugin runtime artifacts
won't be committed:

```
# Claude plugin data (installed at runtime)
site-packages/
```

## Step 4: Create skills

Every plugin needs at least one skill. Skills are what make the
plugin useful — they teach Claude *when* and *how* to use the
MCP tools, what workflow to follow, and how to present results.
Without skills, the plugin is just a bag of tools with no context.

**MCP tools are the hands. Skills are the brain.**

### What a skill is

A skill is a `SKILL.md` file that defines a workflow — a sequence
of tool calls, decision points, and presentation rules that Claude
follows when the skill is triggered. The skill document IS the
operational definition. It tells Claude exactly what to do, step
by step.

Skills compose MCP tools into higher-level, intent-based
operations. A single skill may call multiple tools from the
plugin's own MCP server, tools from other MCP servers, or both.

### Directory structure

```
skills/
├── <skill-name>/
│   └── SKILL.md
└── <another-skill>/
    └── SKILL.md
```

### SKILL.md format

Every skill file starts with YAML frontmatter:

```yaml
---
name: <skill-name>
description: <what this skill does and WHEN to trigger it>
argument-hint: [optional-argument-format]
disable-model-invocation: false
user-invocable: true
---
```

**`name`** — the skill identifier. Used in explicit invocation:
`/plugin-name:skill-name`.

**`description`** — what the skill does and when it's relevant.
Claude reads this to decide *when* to auto-trigger the skill.
Write it from the perspective of matching user requests — include
the user intents that should activate it.

Good descriptions:
- "Deploy a Python web server or MCP server to Google Cloud Run.
  Use when asked to deploy, set up hosting, get a service running
  on GCP, or push changes to production."
- "Review bill payment status by cross-referencing declared
  expectations against bank data. Use when asked about bills,
  payments due, or financial obligations."

Bad descriptions:
- "Manages deployments" (too vague, no trigger conditions)
- "Runs gapp commands" (describes implementation, not intent)

**`disable-model-invocation`** — controls whether Claude can
auto-trigger the skill. Default `false` means Claude CAN invoke
it automatically when the description matches user intent. Set to
`true` to restrict to explicit `/plugin:skill` invocation only.

**`user-invocable`** — controls whether the skill appears in the
`/` menu for manual invocation. Default `true`. Set to `false` to
hide it from users (Claude-only skill).

| Setting | User can invoke | Claude can invoke |
|---------|----------------|-------------------|
| Both defaults | Yes (`/plugin:skill`) | Yes (auto) |
| `disable-model-invocation: true` | Yes | No |
| `user-invocable: false` | No | Yes |

**`argument-hint`** — optional. Shows what arguments the skill
accepts (e.g., `[solution-name]`, `[card-name]`).

### Skill body content

After the frontmatter, the skill body should include:

1. **Overview** — what question or need this skill answers
2. **Data sources** — which MCP tools to call and what they return
3. **Workflow phases** — step-by-step instructions for Claude:
   - What to call and in what order (parallel where possible)
   - Decision points and branching logic
   - What to present to the user at each stage
4. **Presentation rules** — how to format output, what terms to
   use, what level of detail
5. **Error handling** — what to do when tools fail or data is
   missing

Write the skill as instructions to Claude, not documentation for
humans. Be specific and prescriptive — "Call X, then present Y
in this format" rather than "The system can do X."

### Invocation: implicit vs explicit

Skills can be triggered two ways:

**Explicit** — the user types `/plugin-name:skill-name`. Controlled
by `user-invocable` (default `true`).

**Implicit** — Claude auto-triggers the skill when the user's
request matches the `description`. Controlled by
`disable-model-invocation` (default `false` = implicit enabled).
No slash command needed — the user just says what they want.

**Ask the user which invocation style fits each skill.** Present
it this way:

> Each skill can be triggered explicitly (`/gapp:deploy`) or
> implicitly — Claude recognizes the user's intent and runs the
> skill automatically. For example, if someone says "help me get
> this deployed to Cloud Run", Claude would recognize that as a
> deploy workflow and start the skill without being asked.
>
> Implicit invocation is better for discovery — users don't need
> to know the skill exists. Explicit is better for precision —
> the user knows exactly what they're invoking.
>
> Which style works for each skill? (Most plugins use implicit
> for their primary workflows.)

For implicit skills, write the `description` with trigger phrases:
"Use when asked to...", "Trigger when the user wants to...".

For explicit-only skills, set `disable-model-invocation: true`.

For Claude-only skills (no `/` menu entry), set
`user-invocable: false`.

### How many skills?

Ask the user what workflows the plugin should support. Think in
terms of **user intents**, not tool coverage. Each distinct
"I want to..." from the user is a candidate skill.

Don't create a skill for every MCP tool — skills orchestrate
multiple tools into coherent workflows. A plugin with 8 tools
might have 2-3 skills.

### Skills that span multiple MCP servers

A skill can orchestrate tools from any MCP server available in
the session — not just the plugin's own. If the workflow requires
calling tools from other plugins or registered servers, list them
as data sources in the skill body.

## Step 5: Test

Suggest testing with:

```bash
claude --plugin-dir ./
```

If the user chose to keep a standalone entry point, also confirm
it still works (e.g., `gapp-mcp`).

If the user absorbed the MCP server (no standalone entry point),
suggest removing stale `claude mcp add` registrations.

## Remote service configuration

This section applies when the plugin needs to connect to an
external service — a remote HTTP MCP server, a REST API, or
anything requiring a URL and/or credential.

This is **orthogonal to greenfield vs. conversion** — any plugin
type might need it.

### Ask the user

> The plugin will need to connect to a remote service. This means
> storing a URL and/or credential locally so the plugin can
> authenticate. I'll add:
> - A config file in `${CLAUDE_PLUGIN_DATA}` (persists across
>   sessions and plugin updates)
> - A `configure` tool so you (or Claude) can set the URL and
>   credential without editing files
>
> Does that work?

### Config file pattern

Store config in `${CLAUDE_PLUGIN_DATA}/config.json`:

```python
import json, os
from pathlib import Path

CONFIG_PATH = Path(os.environ.get(
    "CLAUDE_PLUGIN_DATA", "."
)) / "config.json"

def load_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())
    return {}

def save_config(config: dict):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2))
```

### Configuration tool

Include a tool so credentials can be set via MCP:

```python
@mcp.tool()
def configure(url: str | None = None, token: str | None = None) -> dict:
    """Configure the connection to <service-name>.

    Args:
        url: Service URL.
        token: Authentication token or API key.
    """
    config = load_config()
    if url is not None:
        config["url"] = url
    if token is not None:
        config["token"] = token
    save_config(config)
    return {"status": "configured", **{k: "***" if k == "token" else v for k, v in config.items()}}
```

### Wrapper tools

Build **intent-based tools** — not 1-to-1 mirrors of the remote
interface. Each tool should:

1. Load the URL and credential from local config
2. Make the remote call
3. Return a useful result

The user shouldn't need to know the remote API structure or pass
credentials manually.

### If proxying a remote HTTP MCP server

- Import `ClientSession` and `streamablehttp_client` from `mcp`
- Build a `call_remote_tool` helper that reads URL/token from
  local config:

```python
from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession

async def call_remote_tool(tool_name: str, arguments: dict) -> list:
    config = load_config()
    url = config.get("url")
    token = config.get("token")
    if not url:
        raise ValueError("Not configured. Use the configure tool to set the URL.")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with streamablehttp_client(url, headers=headers) as (r, w, _):
        async with ClientSession(r, w) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            return result.content
```

- This pattern is explicitly supported by MCP's creators — see
  [MCP proxy](${CLAUDE_SKILL_DIR}/../../docs/mcp-proxy.md) for
  authoritative sources

### If wrapping a REST/GraphQL API

- Use `httpx` (async) or `requests` for HTTP calls
- Each tool maps to one or more API calls, with the credential
  injected from local config
- Handle auth header construction in one place (helper function),
  not per-tool

## Version Management

### plugin.json version

The `version` field in `.claude-plugin/plugin.json` controls
whether `claude plugin install` picks up changes. **If you change
plugin code but don't bump the version, users won't see updates.**

Claude Code caches installed plugins at `~/.claude/plugins/cache/`.
The cache is keyed by version — same version = cached copy used,
even if the source repo has changed.

**Always bump the version when shipping changes:**

```json
{
  "name": "my-plugin",
  "description": "...",
  "version": "1.1.0"
}
```

Follow semver: patch for fixes, minor for new features/skills,
major for breaking changes.

### Update workflow for users

```bash
claude plugin marketplace update <marketplace-name>
claude plugin install <plugin>@<marketplace> --scope user
```

If the install doesn't pick up changes, clear the cache:

```bash
rm -rf ~/.claude/plugins/cache/<marketplace>/
claude plugin install <plugin>@<marketplace> --scope user
```

Then restart Claude Code.

## Publishing to a Marketplace

To make the plugin installable via `claude plugin install`, add
it to a marketplace repo.

### Find the developer's marketplace repo

Check if the developer already has a marketplace repo by looking
for repos with the `claude-plugins-marketplace` topic:

```bash
gh repo list --topic claude-plugins-marketplace --json name,url --jq '.[] | "\(.name) \(.url)"'
```

If found, use that repo. If not found, ask the developer:

> I couldn't find a marketplace repo with the
> `claude-plugins-marketplace` topic on your GitHub account.
> Would you like me to create one? This is a public repo that
> acts as an index of your plugins — users add it as a
> marketplace source and install plugins from it.

If they agree, create it with the topic so it's discoverable:

```bash
gh repo create <owner>/claude-plugins --public --description "Claude Code plugin marketplace"
gh repo edit <owner>/claude-plugins --add-topic claude-plugins-marketplace
```

### Add to marketplace

In the marketplace repo, add an entry to
`.claude-plugin/marketplace.json`.

**CRITICAL: Source type matters.** There are two source types
with very different behavior:

**`url` (RECOMMENDED for plugins at repo root):**
```json
{
  "name": "my-plugin",
  "source": {
    "source": "url",
    "url": "https://github.com/<owner>/<repo>.git",
    "ref": "v1.0.0"
  },
  "description": "Short description"
}
```
Clones the full repo at the tagged ref. All directories are
present — skills, hooks, .claude-plugin, everything works.
Use `ref` with a version tag (not a SHA — SHAs trigger
precommit scanners as high-entropy strings).

**`git-subdir` (ONLY for plugins nested in a subdirectory):**
```json
{
  "name": "my-plugin",
  "source": {
    "source": "git-subdir",
    "url": "https://github.com/<owner>/<repo>.git",
    "path": "claude/plugin"
  },
  "description": "Short description"
}
```
**WARNING:** `git-subdir` does a sparse checkout that only
copies root-level files — **directories are excluded**. This
means `skills/`, `hooks/`, and `.claude-plugin/` are NOT
cached. The MCP server still works (installed via pip by the
SessionStart hook) but skills and hooks are broken. Only use
this when the plugin lives in a subdirectory of a larger repo
and you have no alternative. Prefer restructuring the repo to
put plugin files at root and using `url` source instead.

Do NOT use `"source": "github"` — it clones via SSH which
requires SSH keys.

### Marketplace setup (for users who don't have it)

```bash
claude plugin marketplace add <marketplace-url>
```

### Install from marketplace

```bash
claude plugin marketplace update <marketplace-name>
claude plugin install <plugin>@<marketplace> --scope user
```

### Formulate install commands from the discovered marketplace

Once you've identified the marketplace repo (e.g.,
`https://github.com/someuser/claude-plugins.git`), derive the
marketplace name from the repo name (e.g., `claude-plugins`) and
the plugin name from `marketplace.json`. Then provide the user
with the full install sequence:

```bash
# One-time marketplace setup
claude plugin marketplace add https://github.com/<owner>/<marketplace-repo>.git

# Install the plugin
claude plugin marketplace update <marketplace-repo>
claude plugin install <plugin-name>@<marketplace-repo> --scope user
```

### After publishing updates

Full release workflow:

1. Bump version in `.claude-plugin/plugin.json`
2. Commit and push the plugin repo
3. Tag the release and push the tag:
   ```bash
   git tag v1.2.0
   git push origin v1.2.0
   ```
4. Update the marketplace `ref` to the new tag:
   ```json
   "ref": "v1.2.0"
   ```
5. Commit and push the marketplace repo
6. Clear the local plugin cache (required — reinstall alone
   may not pick up changes due to caching bugs):
   ```bash
   rm -rf ~/.claude/plugins/cache/<marketplace>/<plugin-name>
   ```
7. Reinstall:
   ```bash
   claude plugin marketplace update <marketplace-name>
   claude plugin install <plugin>@<marketplace> --scope user
   ```
8. Restart Claude Code
9. Verify with `/skills` — all skills should appear

**Common gotchas:**
- Forgetting to push the tag before marketplace update →
  clone fails silently, old version loaded
- Not clearing cache → old version served even after
  marketplace update and reinstall
- Using `git-subdir` source → skills directories not cached
  (switch to `url` source with `ref` tag)
