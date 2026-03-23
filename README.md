# Claude Plugin Creator

A Claude Code plugin for scaffolding new plugins that bundle
self-installing local MCP servers.

## Install

```bash
claude plugin install plugin-creator@productivity
```

Requires the [productivity marketplace](https://github.com/krisrowe/claude-plugins):

```bash
claude plugin marketplace add krisrowe/claude-plugins
```

## Usage

```
/plugin-creator:create-mcp-plugin my-tool
```

Scaffolds a complete plugin directory with:
- `.claude-plugin/plugin.json` — plugin metadata
- `.mcp.json` — MCP server registration
- `hooks/hooks.json` — SessionStart hook for auto-installing Python dependencies
- `server.py` — starter FastMCP server
- `requirements.txt` — Python dependencies

The generated plugin installs its own dependencies on first session
start using `${CLAUDE_PLUGIN_DATA}`. No pipx, no PyPI, no manual
setup.

## Documentation

- [docs/plugin-patterns.md](docs/plugin-patterns.md) — self-installing MCP servers, dependency management, orchestration
- [docs/mcp-framework.md](docs/mcp-framework.md) — which MCP Python framework we use and why
- [docs/mcp-proxy.md](docs/mcp-proxy.md) — whether MCP tool proxying/orchestration is appropriate, with authoritative sources

## Architecture

This plugin follows the self-installing pattern documented by Anthropic
at [Plugins reference — Persistent data directory](https://code.claude.com/docs/en/plugins-reference#persistent-data-directory).
See the docs above for full analysis with sourced quotes from the MCP
protocol creators.
