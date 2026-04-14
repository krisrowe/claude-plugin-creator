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
            "command": "diff -q \"${CLAUDE_PLUGIN_ROOT}/requirements.txt\" \"${CLAUDE_PLUGIN_DATA}/requirements.txt\" >/dev/null 2>&1 || (cd \"${CLAUDE_PLUGIN_DATA}\" && cp \"${CLAUDE_PLUGIN_ROOT}/requirements.txt\" . && python3 -m pip install -t \"${CLAUDE_PLUGIN_DATA}/site-packages\" -r requirements.txt) || rm -f \"${CLAUDE_PLUGIN_DATA}/requirements.txt\""
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

## Install-pattern variants and antipattern

The self-installing pattern above is the **recommended** shape. Two variants and one antipattern are worth naming explicitly because they look similar and produce very different outcomes.

### Recommended: direct-source + explicit-deps

The pattern already documented above:

- Source runs **directly from `${CLAUDE_PLUGIN_ROOT}`** — `.mcp.json` points at `${CLAUDE_PLUGIN_ROOT}/server.py` (or equivalent), no copy step
- `requirements.txt` lists **only external dependencies** (e.g., `mcp>=1.0.0`), not `.` or the plugin itself
- Install hook uses `diff -q requirements.txt` to detect changes — file-content signal, not version string
- Only third-party deps end up in `${CLAUDE_PLUGIN_DATA}/site-packages`

Result: source can never drift because it isn't duplicated. The only thing that can go out of sync is the dependency set, which the `diff` check catches.

### Antipattern: `requirements.txt = .` with version-string cache invalidation

```
# DON'T DO THIS
requirements.txt:
.

hook compares __version__ from the source against a cached installed_version file
```

This pattern installs the **plugin's own source** into site-packages alongside its deps, producing a second copy that can drift from the plugin cache. The drift is invisible until symptoms appear.

Why it breaks:

- `pip install .` copies the plugin source into `${CLAUDE_PLUGIN_DATA}/site-packages/<plugin>/`, creating a duplicate of what's already at `${CLAUDE_PLUGIN_ROOT}`
- The hook's comparison (e.g., `__version__` in `__init__.py` vs a cached `installed_version` file) can report "already installed" when the cache file is stale but the site-packages contents don't match the current source (e.g., install was partial, the marketplace refreshed the cache after the installed_version was written, or the version string didn't change even though the code did)
- User runs `.mcp.json`'s `python3 -m <package>.server` which imports from `PYTHONPATH=${CLAUDE_PLUGIN_DATA}/site-packages` — picking up the stale copy, not the fresh plugin cache
- Debugging this is painful because the plugin looks installed (files are there, version string matches), but the code is old

Version strings are proxies for "content changed." They require human discipline to stay accurate and can silently lie. File diffs and content hashes are computed from reality and can't.

Real-world symptom pattern: a plugin bumps its version and pushes a new release. The marketplace refreshes the cache. Sessions restart. Users see "still behaves like the old version" despite `plugin list` showing the new version number — because site-packages was never rewritten.

### Future: uvx + pyproject.toml dual distribution

An emerging alternative that supports both plugin use and standalone (non-plugin) use from the same source:

```json
{
  "mcpServers": {
    "my-tool": {
      "command": "uvx",
      "args": ["--from", "${CLAUDE_PLUGIN_ROOT}", "my-tool-mcp"]
    }
  }
}
```

With a matching `pyproject.toml`:

```toml
[project]
name = "my-tool"
dependencies = ["mcp", ...]

[project.scripts]
my-tool-mcp = "my_tool.server:main"
```

[`uvx`](https://docs.astral.sh/uv/guides/tools/) (part of [`uv`](https://docs.astral.sh/uv/)) creates an isolated environment from the local path, installs the package + deps, and runs the declared entry point. uv handles cache invalidation internally based on source and metadata, so no custom install hook is needed.

Advantages over the direct-source + explicit-deps pattern:

- **Dual distribution from one repo**: the same `pyproject.toml` that serves the plugin also makes the package installable standalone via `pipx install git+<url>@<tag>`, giving users a non-plugin path (any MCP client, not just Claude Code) without duplicating code across repos.
- **No custom install hook**: uv's cache handles reinstall decisions automatically.
- **Entry points are declarative**: `[project.scripts]` is the source of truth for commands, usable by both the plugin and standalone install.

Tradeoffs:

- Requires `uv` on the user's PATH. `uv` is rapidly becoming the standard for Python tool-running ([Claude Code docs recommend `uvx`](https://code.claude.com/docs/en/mcp)), and installs trivially (`brew install uv` or a curl script), but it's not yet guaranteed on every machine.
- First launch is slower than a pre-installed package (uv creates the env), but subsequent launches are fast thanks to aggressive caching.
- If the plugin has no standalone-distribution ambition, this adds dependencies (`uv`, `pyproject.toml`) without commensurate benefit over direct-source + explicit-deps.

### Comparison

| Property | Direct-source + explicit-deps (recommended) | `pip install .` + version-string cache (antipattern) | uvx + pyproject.toml (future) |
|---|---|---|---|
| Source duplication risk | None (source runs from ROOT) | High (source copied to site-packages) | None (uv env references source) |
| Cache invalidation signal | File-content diff (reliable) | Version string (proxy, can lie) | uv-managed (reliable) |
| Custom install hook required | Yes (small, content-based) | Yes (custom, version-based) | No (uv handles it) |
| Works as standalone MCP server outside the plugin | Manual venv + pip (possible but clunky) | Same, with drift risk | One-liner via `pipx install` or `uvx --from` |
| Dep manifest | `requirements.txt` (external deps only) | `pyproject.toml` or `requirements.txt` | `pyproject.toml` (standard) |
| External tool requirement | python3 + pip | python3 + pip | python3 + uv |
| Ecosystem alignment | Matches [Anthropic's self-installing recommendation](https://code.claude.com/docs/en/plugins-reference#persistent-data-directory) | Legacy / pre-uvx workaround | Matches [Claude Code docs on MCP invocation](https://code.claude.com/docs/en/mcp) and Python tooling trend |

**Current recommendation**: direct-source + explicit-deps. Move to uvx + pyproject.toml when:

- A new plugin needs dual distribution from day one
- Or the plugin has existing or imminent demand for standalone MCP server use outside Claude Code
- Or the ecosystem reaches a point where `uv` availability is ambient (on par with `python3`)

## Plugin as orchestration: the bundling guarantee

A plugin is more than a bundle of skills. It's an **all-or-nothing unit** that enables orchestration patterns individual skills can't safely do alone.

### The problem with skill-to-skill cross-references

Standalone skills — those distributed individually via a marketplace, a skills install CLI, or manual copy — must function when installed alone, without assuming any sibling skill is present. This means:

- A skill can't confidently say "when you finish here, invoke skill X" because skill X may not be installed
- Cross-references must be soft hints, not structural dependencies
- Multi-skill workflows have no way to enforce order or completeness across skill boundaries
- Skills either duplicate content from their neighbors (fighting DRY) or live with broken references (fighting reliability)

### How plugins lift the constraint

A plugin bundles a set of skills **together**. When the plugin is installed, every skill it declares is present. When it isn't, none of them are.

This turns a collection of loosely-coupled skills into a cohesive product. Inside the plugin's scope — its agent definition (`agents/<name>.md`) and its bundled skills — the plugin knows exactly which sibling skills exist. It can orchestrate them with confidence.

### The agent .md orchestration pattern

Claude Code plugins can ship agent definition files (e.g., `agents/<agent-name>.md`) that declare preloaded skills in frontmatter and provide orchestration in the body.

```markdown
---
name: my-agent
description: ...
skills:
  - step-one-skill
  - step-two-skill
  - final-step-skill
---

# My Agent

You help users accomplish <workflow>. The workflow has three stages:

## Stage 1 — preparation
Use `step-one-skill` before starting any real work.

## Stage 2 — execution
...

## Stage 3 — verification
Before marking the task done, invoke `final-step-skill` to confirm ...
```

Two narrow jobs for the agent .md:

1. **Preload** critical skills via the `skills:` frontmatter so their content is in context from the start of every session. This guarantees the model has them without relying on frontmatter-based discovery.
2. **Orchestrate** via a thin, high-level workflow outline in the body that names other skills at the moments they apply, with short summaries of what each one does and when to invoke it.

### Design principle: avoid a monolith

The agent .md is explicitly NOT the place to pack the full content of every skill. Skills remain the source of truth for their respective domains. The agent .md's orchestration is intentionally redundant with skills' own descriptions — the redundancy is a safety net for imperfect skill discovery, not a substitute for the skills themselves.

When writing or extending an agent .md:

- Does the content belong in a specific skill? → put it in the skill, reference it from the agent .md with a short summary
- Is it workflow-level orchestration that crosses skill boundaries? → goes in the agent .md body
- Is it a critical skill that should always be in context? → add to frontmatter `skills:`
- Otherwise → probably belongs in a skill, not here

### Why this belongs in plugins specifically

Without the plugin's bundling guarantee, the same orchestration discipline is unsafe:

- A skill with hard references to siblings breaks when sibling is missing
- A standalone "orchestrator skill" doesn't have the guarantee either — it still depends on siblings being installed
- No other Claude Code mechanism provides "these skills are guaranteed present" scope for orchestration to rely on

So: multi-skill workflows that need reliable cross-references belong in a plugin, and the plugin's agent .md is where the orchestration lives. Plugins don't just deliver skills — they deliver **composed workflows** that couldn't exist otherwise.

### When to use this pattern

- A plugin offers a set of skills that work better together than alone
- The skills compose into a multi-step workflow with natural ordering
- You want to ensure certain skills are always loaded in context (not just discoverable) when the plugin is active
- Cross-skill references need to be reliable, not conditional

Plugins with a single skill, or skills that are genuinely independent, don't need this pattern. It's for products that compose.

## MCP Orchestration

A plugin's MCP server can act as both server (exposing tools to Claude)
and client (calling tools on other MCP servers). This is useful when a
plugin needs to augment, filter, or compose data from an external
service with local business logic.

### Framework

We use the official [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
(`pip install mcp`) for both server and client. See
[MCP framework](https://github.com/krisrowe/mcp/blob/main/docs/mcp-framework.md) for details on the SDK,
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
