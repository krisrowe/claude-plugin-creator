# Contributing to claude-plugin-creator

## Design principles

The patterns this plugin promotes — both for plugins it scaffolds and
for plugins authors work on while plugin-creator is loaded as an
agent context — are documented at length in
the [plugin patterns doc](docs/plugin-patterns.md). Preserve these
principles when modifying the scaffolder, its generated output, or
the skills and agent context that guide work on other plugins.

### Direct-source MCP servers over install-to-site-packages

Plugins should run their MCP server source directly from
`${CLAUDE_PLUGIN_ROOT}`. `requirements.txt` declares only external
dependencies — never `.` — so the plugin's own source is never
duplicated into `${CLAUDE_PLUGIN_DATA}/site-packages`. This applies
both to plugins this tool scaffolds and to plugins being worked on
with plugin-creator's guidance.

The install hook uses `diff -q requirements.txt` for cache invalidation
(file-content signal) rather than a version string (proxy signal that
requires human discipline and can lie).

Do not introduce the `requirements.txt = .` antipattern. It copies the
plugin's own source into site-packages, producing a second copy that
drifts silently from the plugin cache. Symptoms are hard to diagnose —
the plugin looks installed and version checks pass, but imports resolve
to stale code. See [the patterns doc](docs/plugin-patterns.md#install-pattern-variants-and-antipattern)
for the full failure-mode analysis.

### Orchestration belongs in the agent .md; content belongs in skills

A plugin that composes multiple skills should use its agent definition
(`agents/<name>.md`) for orchestration — preloaded skills via
frontmatter plus a thin workflow outline in the body that names other
skills at the moments they apply.

The agent .md must not become a monolith. Skills remain the source of
truth for their respective domains. The agent .md's orchestration is
intentionally redundant with skills' own frontmatter descriptions — it
is a safety net for imperfect skill discovery, not a replacement for
the skills themselves.

Rule of thumb when adding content to an agent .md:

- Content specific to a task a skill handles? Put it in the skill.
- Workflow-level context that crosses skill boundaries? Agent .md.
- Critical skill that must always be in context? Add to `skills:`
  frontmatter, describe briefly in the body.

This separation only works because a plugin bundles its skills as an
all-or-nothing unit. See [the patterns doc](docs/plugin-patterns.md#plugin-as-orchestration-the-bundling-guarantee)
for why the bundling guarantee makes orchestration safe and why
standalone skills can't replicate this.

### Evolving toward `uvx` + `pyproject.toml`

The current scaffolded pattern (direct-source + explicit-deps with a
`SessionStart` install hook) is the recommended default. An `uvx` +
`pyproject.toml` pattern is under consideration for plugins that need
dual distribution (usable as a plugin AND as a standalone pipx/uvx-
installable MCP server from one repo). See
[the patterns doc](docs/plugin-patterns.md#future-uvx--pyprojecttoml-dual-distribution)
for the comparison and the conditions under which it becomes the right
choice.

If you extend the scaffolder to emit an `uvx`-based plugin shape, keep
the existing pattern available — both variants should be supported
until `uv` availability is ambient in the ecosystem.

## Updating the patterns doc

Changes to how plugins should be structured — new patterns, new
antipatterns discovered, new alternatives worth considering — belong
in the [plugin patterns doc](docs/plugin-patterns.md) first. The
scaffolder's generated output and the README summaries should then
follow. Avoid encoding patterns in the scaffolder code that aren't
documented first; the doc is the authoritative reference that plugin
authors (and coding agents working on plugins) should read to learn
the why, not just the how.
