# Claude Plugin Creator

A Claude Code plugin for scaffolding and testing new plugins that bundle
self-installing local MCP servers.

## Why this exists

Claude Code plugins can bundle an MCP server alongside skills and hooks
into a single installable unit — no separate `pipx install`, no
`claude mcp add`, no manual setup. But getting the configuration right
is tricky: the `SessionStart` hook must install Python dependencies into
an isolated `site-packages` using `python3 -m pip` (not `pip`, which
doesn't exist on macOS), the `.mcp.json` must set `PYTHONPATH` to that
directory, and the server must be invocable from any working directory
via `${CLAUDE_PLUGIN_ROOT}`.

This plugin generates all of that correctly. It scaffolds a working
plugin with an MCP server, a skill, and a dependency hook — tested
end-to-end — so you can rename the sample tool and start building
your real plugin on a known-good foundation.

## Install

```bash
claude plugin install plugin-creator@productivity
```

Requires the [productivity marketplace](https://github.com/krisrowe/claude-plugins):

```bash
claude plugin marketplace add https://github.com/krisrowe/claude-plugins.git
```

## Scaffolding a plugin

Ask Claude to scaffold a plugin. It picks a random animal and saying,
creates all the files, and tells you how to test:

```
> scaffold me a plugin
```

The generated plugin includes:

- **A sample MCP tool** (`speak_<animal>`) — proves the full
  self-installing pipeline works.
  [Details →](docs/sample-tool.md)
- **A sample skill** (`speak-animal`) — demonstrates graceful
  degradation between tool calls and improvisation.
  [Details →](docs/sample-skill.md)
- Correct `SessionStart` hook with `python3 -m pip`
- `.mcp.json` with proper `PYTHONPATH` configuration
- `requirements.txt` for dependency management

## Testing plugins

After scaffolding (or any time you have a plugin's source locally),
ask Claude to test it:

```
> debug that plugin
```

Claude runs a headless session against the plugin directory, validates
that tools are discovered by intent (not by name), and reports the
result. No manual commands needed.

**Or run manually:**

```bash
claude -p "speak alligator" --plugin-dir=/path/to/plugin \
  --allowedTools "mcp__plugin_alligator-speak_alligator-speak__*"
```

### Testing any plugin

The `debug_plugin` tool works on any Claude Code plugin you have
locally — not just plugins created by this scaffolder. Point it at
any directory with a `.claude-plugin/plugin.json` and give it a
natural-language prompt that should trigger one of the plugin's tools.
It auto-discovers the plugin's MCP tool names from `.mcp.json` and
pre-approves them so the headless session runs without permission
prompts.

This is useful for:

- Verifying a plugin after code changes
- Testing plugins created manually or by other tools
- Validating that skills trigger the right tools
- Quick smoke tests before publishing to a marketplace

## MCP Tools

### `scaffold_plugin`

Creates a complete working plugin skeleton.

```
scaffold_plugin(animal_species, common_saying, path=None)
```

- `animal_species` — animal name (e.g., "alligator")
- `common_saying` — what it says (e.g., "After while, crocodile")
- `path` — target directory (default: current working directory)

### `debug_plugin`

Runs a headless Claude session against a plugin directory.

```
debug_plugin(prompt, path=None)
```

- `prompt` (required) — natural-language phrase that should trigger
  the plugin. Describe intent, don't name tools directly.
- `path` — plugin directory (default: current working directory)

Do not use on long-running tools (deploys, builds, CI). It has a
60-second timeout.

## Skills

- **`create-mcp-plugin`** — full guide for scaffolding manually or
  converting an existing MCP server into a plugin. Covers greenfield,
  absorb, and complement patterns.
- **`debug-plugin`** — test a plugin via the `debug_plugin` MCP tool.

## Documentation

- [docs/plugin-patterns.md](docs/plugin-patterns.md) — self-installing
  MCP servers, dependency management, orchestration
- [docs/sample-tool.md](docs/sample-tool.md) — the generated sample tool
- [docs/sample-skill.md](docs/sample-skill.md) — the generated sample skill
