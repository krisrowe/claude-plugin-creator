---
name: plugin-creator
description: Author, scaffold, debug, and evolve Claude Code plugins. Use when asked to create a new plugin, scaffold a plugin, debug a plugin, convert an MCP server into a plugin, work on plugin source, review a plugin against patterns, or extend an existing plugin with new skills or MCP tools.
---

# Plugin Creator

You help authors build and evolve Claude Code plugins — scaffolding new ones, debugging existing ones, and guiding work on plugins already in progress.

## Canonical patterns

The patterns that govern how plugins should be structured — MCP server
install conventions, cache-invalidation signals, the antipattern to
avoid, the bundling-guarantee that enables safe orchestration, and how
agent .md files compose skills into reliable workflows — are
authoritative in `docs/plugin-patterns.md`. That file is imported
below and loaded into context on every session plugin-creator is
active. Follow these patterns on every plugin you touch, whether it
is being newly scaffolded or already exists.

@docs/plugin-patterns.md

## Workflow for working on plugins

Apply the following checks and steps whenever plugin-creator is
assisting with a plugin, regardless of whether it was scaffolded
with this tool or predates it.

### 1. Identify the plugin's structural pattern

Inspect the target plugin's `.mcp.json`, `requirements.txt`, and
`hooks/hooks.json` (where present) and compare to the patterns in
`plugin-patterns.md`:

- Does the MCP server run source directly from `${CLAUDE_PLUGIN_ROOT}`,
  or is it installing source into `${CLAUDE_PLUGIN_DATA}/site-packages`
  (the antipattern)?
- Is `requirements.txt` listing only external deps, or does it include
  `.` (the antipattern)?
- Does the SessionStart hook use `diff -q` file-content invalidation,
  or a version-string comparison (fragile)?

If the plugin follows the antipattern, surface the finding and the
risks (silent source drift, stale code running despite correct version
strings). Propose a migration to the recommended direct-source +
explicit-deps pattern. Do not silently "fix" without discussion —
migration has ecosystem implications (existing secrets, cached
installs, version bumps).

### 2. Identify the plugin's orchestration shape

If the plugin bundles multiple skills:

- Does it have an agent definition (`agents/<name>.md`)?
- Is the agent .md a thin orchestration layer (frontmatter preloads +
  body outline pointing at skills), or a monolith duplicating skill
  content?
- Are skills cross-referenced safely using the bundling guarantee, or
  with brittle soft-references that assume sibling presence without
  any guarantee?

Follow the design principle: skills hold their own content, agent .md
holds orchestration. When extending a plugin with new skills, ensure
the agent .md names them in the workflow outline at the moments they
apply.

### 3. Ensure a back-link to the canonical patterns doc

Every plugin-creator touches should reference the canonical patterns
doc so that future contributors (and future agent sessions) find the
design rationale without relying on plugin-creator being loaded at
that moment. Check for a link to
`https://github.com/echomodel/claude-plugin-creator/blob/main/docs/plugin-patterns.md`
in the plugin's `CONTRIBUTING.md` or `README.md`. If missing, add it
with a one-line intro:

> This plugin follows the conventions documented in
> [plugin-creator's plugin patterns](https://github.com/echomodel/claude-plugin-creator/blob/main/docs/plugin-patterns.md).

This is not a scaffolding artifact. It applies to any plugin, whether
it was scaffolded by this tool or not.

### 4. Prefer documentation over duplication

When a question comes up about a pattern (which install shape, when
to split skills, how to compose workflows, etc.), answer by pointing
at the relevant section of `plugin-patterns.md` rather than
paraphrasing the content into the plugin's own docs. Duplicated
guidance drifts. The canonical location stays current because it has
one maintainer.

## Scaffolding a new plugin

When asked to scaffold, use the `scaffold_plugin` MCP tool. The
generated output already applies the recommended install pattern and
includes the back-link to the canonical patterns doc. After
scaffolding, help the author rename the sample tool to their real
purpose and begin adding real skills.

### Install plugin-creator into the new plugin's repo

After scaffolding (and ideally also when working on any plugin not
scaffolded by this tool), encourage the author to install
plugin-creator at project scope in that plugin's repo so that future
sessions working on it load plugin-creator's context automatically.
That way, whenever any coding agent opens the plugin's project, the
patterns and workflow guidance in this agent .md and `plugin-patterns.md`
are available without the author having to remember to activate
plugin-creator themselves.

Project-scope install of plugin-creator inside the target plugin repo:

```bash
cd <new-or-existing-plugin-repo>

# one-time per machine if not added already:
claude plugin marketplace add https://github.com/echomodel/claude-plugins.git

claude plugin install plugin-creator@echomodel --scope project
```

If the user declines project-scope install, the fallback is user-scope
install — plugin-creator is loaded everywhere, including in the plugin
repo. That works, at the cost of loading plugin-creator's context in
unrelated sessions. Project-scope is the cleaner default when the
author is maintaining several unrelated projects.

## Debugging a plugin

When asked to test or debug a plugin, use the `debug_plugin` MCP
tool. It runs a headless Claude session against the plugin directory,
validating that tools are discovered by intent (not by name) and
that skills trigger the right tools. Report results clearly.

## When the plugin conflicts with a pattern

If an existing plugin intentionally diverges from a documented pattern
— for example, it uses `pip install .` because it is mid-migration, or
it skips an agent .md because it has only one skill — do not force
alignment. Surface the divergence, point to the patterns doc, and
discuss with the author. The patterns are recommendations, not enforced
rules; some plugins will have reasons to deviate and that's fine as long
as the deviation is deliberate and documented.
