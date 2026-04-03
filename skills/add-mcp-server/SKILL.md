---
name: add-mcp-server
description: Add MCP tools to a Claude Code plugin by bundling a local MCP server that is managed by the plugin — no separate server installation or registration required. The tools are guaranteed available wherever the plugin is installed and active, and can be drawn on from other plugin capabilities like skills and hooks. Use when working on a Claude plugin and a desired or required capability is best served by deterministic, scripted, or predictable repeatable behaviors, or involves technical complexity such as service or data integrations.
user-invocable: true
---

# Add MCP Server to a Plugin

Add a self-installing MCP server to an existing Claude Code plugin
so that MCP tools are bundled with the plugin and available wherever
it is installed. No separate `pipx install`, no `claude mcp add`,
no manual setup for users.

## When to use this

Add MCP tools when a plugin capability requires:

- **Deterministic behavior** — the tool always does the same thing
  for the same input, unlike skill instructions which the agent
  interprets
- **Technical integrations** — API calls, subprocess execution,
  file I/O, data transformations
- **Predictable, repeatable operations** — scaffolding files,
  running commands, querying services
- **Complex logic** — anything that would be unreliable as natural
  language instructions in a skill

Skills teach the agent *when* and *how* to orchestrate. Tools do
the actual work. If a skill would need to tell the agent to shell
out to run Python code, that's a missing tool.

## Step 1: Inspect the plugin

Check what the plugin already has:

```
.claude-plugin/plugin.json  — must exist (it's a plugin)
.mcp.json                   — MCP server registration (may not exist yet)
hooks/hooks.json            — hooks (may not exist yet)
requirements.txt            — Python dependencies (may not exist yet)
server.py                   — MCP server (may not exist yet)
```

If `.mcp.json` already exists, the plugin already has an MCP server.
Add tools to the existing `server.py` instead of creating new files.

## Step 2: Create the MCP server files

If the plugin has no MCP server yet, create these files:

### `server.py`

```python
"""MCP server for <plugin-name>."""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("<plugin-name>")


@mcp.tool()
def my_tool(arg: str) -> dict:
    """What this tool does."""
    # Your logic here
    return {"result": "..."}


if __name__ == "__main__":
    mcp.run(transport="stdio")
```

### `.mcp.json`

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

If the plugin is an installable Python package (has `pyproject.toml`),
use `python3 -m <module.path>` instead of a standalone `server.py`:

```json
{
  "mcpServers": {
    "<plugin-name>": {
      "command": "python3",
      "args": ["-m", "<package>.mcp.server"],
      "env": {
        "PYTHONPATH": "${CLAUDE_PLUGIN_DATA}/site-packages"
      }
    }
  }
}
```

### `requirements.txt`

```
mcp>=1.0.0
```

Add any other dependencies the tools need. If the plugin is an
installable package, use `.` to install the package itself:

```
.
```

### `hooks/hooks.json`

If the plugin has no hooks yet, create this file. If it already has
hooks, add the `SessionStart` entry to the existing file.

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

**IMPORTANT:** Use `python3 -m pip`, not `pip`. The `pip` command
does not exist on macOS — only `pip3` does, and `python3 -m pip` is
the cross-platform way to invoke it.

## Step 3: How it works

When the plugin is installed and a Claude session starts:

1. The `SessionStart` hook compares `requirements.txt` against a
   cached copy in `${CLAUDE_PLUGIN_DATA}`
2. On first run or when dependencies change, `python3 -m pip install -t`
   installs packages into `${CLAUDE_PLUGIN_DATA}/site-packages`
3. The MCP server starts via `python3` with `PYTHONPATH` set to that
   directory
4. Tools are available to Claude immediately — no user action needed

The server runs over stdio (local, no network). Dependencies are
isolated in the plugin's own `site-packages` — they don't pollute
the system Python.

## Step 4: Test

Use `debug_plugin` to verify the tools work:

1. Call `debug_plugin` with a natural-language prompt that should
   trigger one of the new tools
2. The prompt should describe intent, not name the tool directly
3. Check that the tool was discovered and returned the expected result

Or test manually:

```bash
claude --plugin-dir=<path-to-plugin-repo>
```

## Step 5: Update skills to use the new tools

If the plugin has skills, update them to reference the new tools.
Prefer the tool when available, but don't assume it will always be
there:

> Check if `my_tool` is available. If so, call it. Otherwise,
> handle the request with your own capabilities.

See `CONTRIBUTING.md` in the plugin (if scaffolded) for the full
guidance on writing skills that reference plugin tools.

Use the `develop-skill` skill (`/develop-skill`) when authoring or
updating skills.

## Common issues

- **MCP server not starting:** Check that `.mcp.json` exists at the
  plugin root and the command/args are correct. Check `claude --debug`
  for the actual error.
- **Module not found:** If using `python3 -m <module>`, ensure the
  package is installable (`pyproject.toml` with proper
  `[tool.setuptools.packages.find]`) and `requirements.txt` contains
  `.` to install it.
- **Dependencies not installing:** Verify the `SessionStart` hook
  uses `python3 -m pip` (not `pip`). Check that `requirements.txt`
  exists at the plugin root.
- **Tools not appearing:** Start a new Claude session after adding
  the MCP server. The server connects at session start.
