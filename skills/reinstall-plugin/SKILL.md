---
name: reinstall-plugin
description: Reinstall a Claude Code plugin from a marketplace after code changes. Use when the user says "reinstall plugin", "update plugin", "bump plugin version", or when a plugin needs to pick up source code changes from its repo.
user-invocable: true
argument-hint: "[plugin-name]"
---

# Reinstall Claude Plugin from Marketplace

When a plugin's source code has changed and the installed (cached) copy is stale,
follow this process to get the new version installed.

## Prerequisites

- The plugin source repo has the changes committed and pushed
- A marketplace repo has an entry for the plugin

## Steps

### 1. Verify all changes are committed

**CRITICAL:** Before bumping the version, run `git status` in the plugin
repo and confirm there are no uncommitted changes. The tag captures a
snapshot of the repo at that commit — any unstaged or uncommitted files
will NOT be included in the installed plugin, even though they exist in
the working tree.

This is a common pitfall: you update a skill or tool, bump the version,
tag it, and push — but the skill update was never staged. The installed
plugin ships with the old skill because the tag points to a commit that
doesn't include it.

```
git status
git add <any-uncommitted-files>
git commit -m "..."
```

### 2. Bump the plugin version

Edit `.claude-plugin/plugin.json` in the plugin's source repo and increment
the `version` field (e.g., `1.2.1` → `1.2.2`).

### 3. Commit and tag

The marketplace pins plugins to git tags. The tag must match the version:

```
git add .claude-plugin/plugin.json
git commit -m "Bump plugin version to X.Y.Z"
git tag vX.Y.Z
git push && git push --tags
```

### 4. Update the marketplace ref

Edit `marketplace.json` in the marketplace repo and update the plugin's
`"ref"` field to the new tag (e.g., `"ref": "vX.Y.Z"`).

Commit and push the marketplace repo.

### 5. Reinstall

```bash
claude plugin marketplace update <marketplace-name>
claude plugin install <plugin-name>@<marketplace-name> --scope user
```

**Important:** If the plugin has an MCP server, the new tools won't
appear until the next Claude Code session. The MCP server connects
at session start and does not hot-reload. Tell the user to start a
new session after reinstalling.

### 6. Verify

Check the cache has the new version:

```bash
ls ~/.claude/plugins/cache/<marketplace-name>/<plugin-name>/
```

The directory name should match the new version.

### 7. Clear stale plugin data (if needed)

If the SessionStart hook installs dependencies keyed by version, clear the
old installed state so it re-runs:

```bash
rm -f ~/.claude/plugins/data/<plugin-name>-<marketplace-name>/installed_version
```

## Troubleshooting

- **Marketplace still serves old version**: Check that the git tag exists
  on the remote (`git ls-remote --tags origin | grep vX.Y.Z`) and that
  `marketplace.json` references it.
- **Plugin cache not updated**: The `claude plugin install` command should
  replace the cache directory. If it doesn't, check `claude plugin marketplace update`
  output for errors.
- **MCP server still fails after reinstall**: Start a new Claude session
  (the MCP server launches at session start). Check `claude --debug` logs
  for the actual error.
- **Installed plugin is missing recent changes**: If you know the path
  to the plugin's local source repo, run `git status` and
  `git log @{u}..HEAD` there. If there are uncommitted changes or
  unpushed commits, the tagged version doesn't include them. Commit
  and push the missing changes, then bump the version again (new
  increment), update the marketplace ref to the new tag, and reinstall.
  Every round of forgotten changes requires its own version bump —
  never retag an existing version.
