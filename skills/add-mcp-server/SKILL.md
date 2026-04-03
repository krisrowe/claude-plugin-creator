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

## Alternative: Register an external MCP server

The steps above are for bundling a new MCP server *inside* the plugin.
There is a different scenario: the user already has an existing MCP
server whose source is maintained separately — by a third party or by
the user in another repo for independent deployment and use outside
the plugin context — and they want the plugin to ensure that server
is registered and available in Claude whenever the plugin is active.

This is much simpler. No `server.py`, no `requirements.txt`, no
`SessionStart` hook for dependency installation. The plugin just
registers the external server in `.mcp.json`.

### For a locally installed server (stdio)

The server is already installed on the user's machine (e.g., via
`pipx install` or `npm install -g`). Add it to `.mcp.json`:

```json
{
  "mcpServers": {
    "<server-name>": {
      "command": "<command>",
      "args": ["<args>"],
      "env": {
        "SOME_VAR": "${SOME_VAR}"
      }
    }
  }
}
```

The command must be on the user's PATH. If the server isn't
installed, it will fail to start — the plugin doesn't manage
installation. Consider documenting prerequisites in the plugin's
README.

Environment variables in `.mcp.json` support `${VAR}` expansion
and `${VAR:-default}` for fallbacks. These resolve from the user's
shell environment at session start.

### For a remote server (HTTP)

The server runs elsewhere (Cloud Run, a SaaS provider, etc.).
Use `"type": "http"` with a URL:

```json
{
  "mcpServers": {
    "<server-name>": {
      "type": "http",
      "url": "https://example.com/mcp"
    }
  }
}
```

If the server requires authentication, add headers:

```json
{
  "mcpServers": {
    "<server-name>": {
      "type": "http",
      "url": "${API_BASE_URL:-https://example.com}/mcp",
      "headers": {
        "Authorization": "Bearer ${API_KEY}"
      }
    }
  }
}
```

The `${API_KEY}` and `${API_BASE_URL}` values come from the user's
environment. If a required variable is not set and has no default,
the config fails to parse. Document which environment variables
users need to set in the plugin's README or add a setup skill.

### Key difference

| | Bundled server | External server |
|---|---|---|
| Source lives in | This plugin repo | Separate repo or third party |
| Installed by | Plugin's SessionStart hook | User (pipx, npm, etc.) or hosted remotely |
| Versioned with | The plugin | Independently |
| Works offline | Yes (stdio, local) | Depends on transport |
| `.mcp.json` points to | `${CLAUDE_PLUGIN_ROOT}/server.py` | External command or URL |
| Needs `requirements.txt` | Yes | No |
| Needs `SessionStart` hook | Yes (for deps) | No |
| Auth/config | Handled in code | Via `env`, `headers`, or `${VAR}` expansion |

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
