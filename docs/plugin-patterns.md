# Plugin Patterns

Patterns for building Claude Code plugins that bundle local MCP servers,
orchestrate external tools, and manage dependencies without requiring
separate installation steps.

## Self-Installing MCP Servers

Plugins can bundle an MCP server that has non-stdlib Python dependencies
(e.g., `pydantic`, `mcp`, `httpx`) and install them automatically on
first session start — no `pipx install`, no PyPI, no manual setup.

This is documented by Anthropic at
[Plugins reference — Persistent data directory](https://code.claude.com/docs/en/plugins-reference#persistent-data-directory):

> **`${CLAUDE_PLUGIN_DATA}`**: a persistent directory for plugin state
> that survives updates. Use this for installed dependencies such as
> `node_modules` or Python virtual environments, generated code, caches,
> and any other files that should persist across plugin versions.

The [recommended pattern](https://code.claude.com/docs/en/plugins-reference#persistent-data-directory)
uses a `SessionStart` hook to detect dependency changes and install only
when needed:

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
  },
  "mcpServers": {
    "my-server": {
      "command": "python3",
      "args": ["${CLAUDE_PLUGIN_ROOT}/server.py"],
      "env": {
        "PYTHONPATH": "${CLAUDE_PLUGIN_DATA}/site-packages"
      }
    }
  }
}
```

How it works:
1. `diff` checks if the plugin's `requirements.txt` matches the cached
   copy in `${CLAUDE_PLUGIN_DATA}`
2. On first run or dependency change, `pip install -t` installs into
   a persistent `site-packages` directory
3. If install fails, the cached manifest is removed so the next session
   retries
4. The MCP server runs via `python3` with `PYTHONPATH` pointing to the
   installed packages

### When to use this pattern

- **Local-only tools** that read/write the local filesystem (config
  managers, bill trackers, project scaffolders)
- **Tool orchestrators / proxies** that wrap or compose calls to other
  MCP servers (see [Orchestration](#mcp-orchestration) below)
- **Plugins with tightly coupled skills** where the skill workflow
  depends on specific MCP tools being available and co-versioned

### Alternatives considered

**Separately installed MCP server (pipx install + claude mcp add).**
This is the traditional approach: install the package globally, then
register it as an MCP server. It works but requires a manual setup step
outside the plugin system. The plugin's `.mcp.json` points to a command
that may or may not exist on the user's machine. If the binary is
missing, the plugin silently fails to start the MCP server.

**Hook-based caching with external MCP servers.** Another approach uses
`PostToolUse` hooks to intercept responses from a separately registered
MCP server and cache the data to disk. The plugin's own MCP server then
reads from cache instead of calling the external server directly. This
works but introduces coupling between two independently versioned
systems (the plugin's hooks must understand the external server's
response format), and the external server must still be installed and
registered separately.

**Remote HTTP MCP servers.** Hosting the MCP server on Cloud Run or
similar. Eliminates local install entirely but requires internet,
adds latency, and means local filesystem access requires a sync layer.
Best for tools that are inherently cloud-based (SaaS API wrappers,
shared data services), not for local config management.

The self-installing pattern is superior for local-only tools because:
- Zero setup beyond plugin install
- Plugin and MCP server are co-versioned (no compatibility drift)
- Works offline
- No external package registry (PyPI) required
- Dependencies auto-update when the plugin updates

## MCP Orchestration

A plugin's MCP server can act as both server (exposing tools to Claude)
and client (calling tools on other MCP servers). This is useful when a
plugin needs to augment, filter, or compose data from an external
service with local business logic.

### Framework

We use the official [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
(`pip install mcp`) for both server and client. See
[docs/mcp-framework.md](mcp-framework.md) for details on the SDK,
how it relates to other packages in the ecosystem, and working examples.

### Server and client in one process

A single `server.py` can:

1. **Expose tools** to Claude via stdio (the standard plugin MCP
   pattern)
2. **Call tools** on a remote MCP server via HTTP using the SDK's
   client session

```python
from mcp.server.fastmcp import FastMCP
from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession

mcp = FastMCP("my-orchestrator")

async def call_remote_tool(tool_name: str, arguments: dict) -> list:
    """Call a tool on a remote MCP server."""
    async with streamablehttp_client(REMOTE_URL) as (r, w, _):
        async with ClientSession(r, w) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            return result.content

@mcp.tool()
async def enriched_list(category: str) -> dict:
    """Fetch remote data and enrich with local logic."""
    remote_data = await call_remote_tool("list_items", {"category": category})
    local_config = load_local_config()
    return cross_reference(remote_data, local_config)
```

### When to use orchestration

- The plugin adds value by **combining** data from an external service
  with local configuration or business rules
- The external service is already available as an MCP server (HTTP or
  stdio)
- You want a **single plugin install** to give the user the full
  workflow, rather than requiring them to separately install and
  register multiple MCP servers
- Skills in the plugin are tightly coupled to both the local tools and
  the remote data

### When NOT to use orchestration

- The external MCP server's tools are useful on their own (let the user
  register it separately)
- The plugin only reads local data (no external dependency needed)
- The remote service is unreliable and you want the local tools to work
  independently
