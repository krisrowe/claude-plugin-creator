# Claude Plugin Creator

A Claude Code plugin for scaffolding and testing new plugins that bundle
self-installing local MCP servers.

## Install

```bash
claude plugin install plugin-creator@productivity
```

Requires the [productivity marketplace](https://github.com/krisrowe/claude-plugins):

```bash
claude plugin marketplace add https://github.com/krisrowe/claude-plugins.git
```

## MCP Tools

### `scaffold_plugin`

Creates a complete working plugin skeleton in a target directory.

```
scaffold_plugin(animal_species, common_saying, path=None)
```

The generated plugin has a `speak_<animal>` tool, a generic
`speak-animal` skill, correct `python3 -m pip` hooks, and a
ready-to-run test command.

**Example — scaffold and test:**

```
> scaffold me a plugin

scaffold_plugin("alligator", "After while, crocodile", "/tmp/test-plugin")
```

Returns paths created and a test command. Run the test command to
verify the plugin works end-to-end:

```bash
claude -p "speak alligator" --plugin-dir=/tmp/test-plugin \
  --allowedTools "mcp__plugin_alligator-speak_alligator-speak__*"
```

**Expected output** — the tool fires and returns the saying:

```
🐊 "After while, crocodile!"
```

The scaffolded plugin also includes a `speak-animal` skill that
handles any animal. When no `speak_<animal>` tool exists, it
improvises:

```bash
claude -p "speak penguin" --plugin-dir=/tmp/test-plugin \
  --allowedTools "mcp__plugin_alligator-speak_alligator-speak__*"
```

**Expected output** — graceful fallback with improvisation:

```
I'm not an expert on that one, but I'll give it my best shot.

*waddles forward, flippers outstretched*

NOOT NOOT! 🐧
...
```

### `debug_plugin`

Runs a headless Claude session against a plugin directory to validate
that tools are discovered and invoked correctly.

```
debug_plugin(prompt, path=None)
```

The prompt should describe intent in natural language — not name
tools directly. This validates auto-discovery. Do not use on
long-running tools.

## Skills

### `create-mcp-plugin`

Full guide for scaffolding a plugin manually or converting an existing
MCP server into a plugin. Covers greenfield, absorb, and complement
patterns. Invoke with `/plugin-creator:create-mcp-plugin`.

### `debug-plugin`

Test a plugin by running a headless session. Uses the `debug_plugin`
MCP tool. Invoke with `/plugin-creator:debug-plugin`.

## Documentation

- [docs/plugin-patterns.md](docs/plugin-patterns.md) — self-installing
  MCP servers, dependency management, orchestration
