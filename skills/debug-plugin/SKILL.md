---
name: debug-plugin
description: Test a Claude Code plugin by running a headless session against it. Use after writing or modifying plugin code (hooks, MCP tools, skills, plugin.json) when the next step is to verify changes work. Also use when the user explicitly asks to test, debug, or validate a plugin.
user-invocable: true
argument-hint: "[natural-language prompt]"
---

# Debug Plugin

Test a new or modified Claude Code plugin by running a headless session
that loads the plugin and triggers its functionality with a natural prompt.

## Steps

1. **Identify what to test.** What tool, skill, or hook was just written
   or changed? What user intent should trigger it?

2. **Craft a natural prompt.** Do NOT name the tool or skill directly.
   The prompt should describe the user's intent in natural language,
   forcing the agent to discover and use the right tool/skill on its own.
   This validates auto-discovery, not just execution.

   Examples:
   - Testing a deploy tool: "deploy my app to cloud run"
   - Testing a branding tool: "check if the name 'foobar' is available"
   - Testing a bill tracker: "show me my upcoming bills"

3. **Call `debug_plugin`** with the natural prompt and the path to the
   plugin directory (defaults to CWD if omitted).

4. **Review the output.** Check:
   - Did the agent find and use the right tool/skill/hook?
   - Did the tool return the expected result?
   - Were there any errors?
   - Exit code 0 = success

5. **Do NOT use this on long-running tools** — deploys, builds, CI
   triggers, etc. It has a 60-second timeout. Use it for quick
   functional checks only.

## Common issues

- **Plugin not loaded:** Check that `.claude-plugin/plugin.json` exists
  at the plugin root.
- **MCP server not starting:** Check `.mcp.json` and ensure the
  SessionStart hook installs dependencies (uses `python3 -m pip`, not
  `pip`).
- **Tool not found:** The MCP server may need dependencies installed.
  Check `requirements.txt` and the SessionStart hook.
- **Hook not firing:** Check `hooks/hooks.json` has the right matcher
  pattern.
