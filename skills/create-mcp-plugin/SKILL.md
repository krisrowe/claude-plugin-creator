---
name: create-mcp-plugin
description: Scaffold a Claude Code plugin that bundles a self-installing local MCP server with Python dependencies. Use when creating a new plugin with MCP tools, or converting an existing MCP server into a plugin.
disable-model-invocation: true
argument-hint: [plugin-name]
---

# Create MCP Plugin

Scaffold a Claude Code plugin that bundles a local MCP server with
automatic dependency installation. No pipx, no PyPI, no manual setup
for end users — the plugin installs its own Python dependencies on
first session start.

## Architecture

This follows the self-installing pattern documented by Anthropic at
[Plugins reference — Persistent data directory](https://code.claude.com/docs/en/plugins-reference#persistent-data-directory).

Key concepts:
- `${CLAUDE_PLUGIN_ROOT}` — plugin install directory (read-only, changes on update)
- `${CLAUDE_PLUGIN_DATA}` — persistent directory for installed dependencies
- `SessionStart` hook — detects dependency changes, runs `pip install -t` once
- MCP server runs via `python3` with `PYTHONPATH` pointing to installed packages

For full details on patterns, framework choice, and proxy justification,
read these supporting docs when the user asks "why" questions:

- [Plugin patterns](${CLAUDE_SKILL_DIR}/../../docs/plugin-patterns.md) — self-installing pattern, alternatives considered, orchestration
- [MCP framework](${CLAUDE_SKILL_DIR}/../../docs/mcp-framework.md) — which MCP SDK we use and why
- [MCP proxy](${CLAUDE_SKILL_DIR}/../../docs/mcp-proxy.md) — whether tool proxying is appropriate, with authoritative sources

## Steps

1. **Ask for the plugin name** if not provided as `$ARGUMENTS`.
   Use kebab-case (e.g., `my-tool`).

2. **Ask what the plugin does** — what tools it exposes, whether it
   wraps an external MCP server (proxy pattern) or is standalone.

3. **Create the plugin directory structure:**

```
$0/
├── .claude-plugin/
│   └── plugin.json
├── .mcp.json
├── hooks/
│   └── hooks.json
├── skills/
│   └── (optional — add if the plugin needs a workflow skill)
├── server.py
└── requirements.txt
```

4. **Generate `plugin.json`:**

```json
{
  "name": "$0",
  "description": "<from step 2>",
  "version": "1.0.0"
}
```

5. **Generate `requirements.txt`** with the needed dependencies.
   Always include `mcp>=1.0.0`. Add `pydantic`, `httpx`, etc. as
   needed based on step 2.

6. **Generate `hooks/hooks.json`** with the SessionStart
   auto-installer:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "diff -q \"${CLAUDE_PLUGIN_ROOT}/requirements.txt\" \"${CLAUDE_PLUGIN_DATA}/requirements.txt\" >/dev/null 2>&1 || (cd \"${CLAUDE_PLUGIN_DATA}\" && cp \"${CLAUDE_PLUGIN_ROOT}/requirements.txt\" . && pip install -t \"${CLAUDE_PLUGIN_DATA}/site-packages\" -r requirements.txt) || rm -f \"${CLAUDE_PLUGIN_DATA}/requirements.txt\""
          }
        ]
      }
    ]
  }
}
```

7. **Generate `.mcp.json`:**

```json
{
  "mcpServers": {
    "$0": {
      "command": "python3",
      "args": ["${CLAUDE_PLUGIN_ROOT}/server.py"],
      "env": {
        "PYTHONPATH": "${CLAUDE_PLUGIN_DATA}/site-packages"
      }
    }
  }
}
```

8. **Generate `server.py`** — a starter FastMCP server using the
   official MCP Python SDK (`from mcp.server.fastmcp import FastMCP`).
   Include one or two example tools based on step 2. If the plugin
   wraps an external MCP server, include a `call_remote_tool` helper
   using `ClientSession` and `streamablehttp_client`.

9. **Test the plugin** by suggesting:

```bash
claude --plugin-dir ./$0
```

## If wrapping an external MCP server (proxy pattern)

When the plugin needs to call tools on another MCP server:

- Import `ClientSession` and `streamablehttp_client` from the `mcp`
  package
- The server.py acts as both MCP server (stdio to Claude) and MCP
  client (HTTP to the remote server)
- Expose high-level intent-based tools, not 1-to-1 mirrors of the
  remote API
- This pattern is explicitly supported by MCP's creators — see
  [MCP proxy](${CLAUDE_SKILL_DIR}/../../docs/mcp-proxy.md) for
  authoritative sources
