"""plugin-creator MCP server — scaffold and debug Claude Code plugins."""

import json
import os
import re
import subprocess
import textwrap
from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("plugin-creator")


@mcp.tool()
def scaffold_plugin(
    animal_species: str,
    common_saying: str,
    path: str | None = None,
) -> dict:
    """Scaffold a working Claude Code plugin with a sample MCP tool.

    Creates all plugin files in the target directory. The generated plugin
    has a speak_<animal> tool that responds with the given saying.

    After scaffolding, rename the tool, update the skill, and build your
    real plugin on top of the working skeleton.

    Args:
        animal_species: Animal name (e.g., "alligator"). Used in tool/plugin name.
        common_saying: What the animal says (e.g., "After while, crocodile").
        path: Target directory. Defaults to current working directory.
    """
    target = Path(path) if path else Path.cwd()
    target.mkdir(parents=True, exist_ok=True)

    # Sanitize animal name for identifiers
    safe_name = re.sub(r"[^a-z0-9]+", "-", animal_species.lower()).strip("-")
    safe_id = re.sub(r"[^a-z0-9]+", "_", animal_species.lower()).strip("_")
    plugin_name = f"{safe_name}-speak"

    files_created = []

    def _write(rel_path: str, content: str):
        p = target / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(textwrap.dedent(content).lstrip("\n"))
        files_created.append(rel_path)

    # .claude-plugin/plugin.json
    _write(".claude-plugin/plugin.json", f"""\
        {{
          "name": "{plugin_name}",
          "description": "A sample plugin that speaks like a {animal_species}",
          "version": "1.0.0"
        }}
    """)

    # .mcp.json
    _write(".mcp.json", f"""\
        {{
          "mcpServers": {{
            "{plugin_name}": {{
              "command": "python3",
              "args": ["${{CLAUDE_PLUGIN_ROOT}}/server.py"],
              "env": {{
                "PYTHONPATH": "${{CLAUDE_PLUGIN_DATA}}/site-packages"
              }}
            }}
          }}
        }}
    """)

    # hooks/hooks.json
    _write("hooks/hooks.json", f"""\
        {{
          "hooks": {{
            "SessionStart": [
              {{
                "hooks": [
                  {{
                    "type": "command",
                    "command": "diff -q \\"${{CLAUDE_PLUGIN_ROOT}}/requirements.txt\\" \\"${{CLAUDE_PLUGIN_DATA}}/requirements.txt\\" >/dev/null 2>&1 || (cd \\"${{CLAUDE_PLUGIN_ROOT}}\\" && cp requirements.txt \\"${{CLAUDE_PLUGIN_DATA}}/\\" && python3 -m pip install -t \\"${{CLAUDE_PLUGIN_DATA}}/site-packages\\" -r requirements.txt) || rm -f \\"${{CLAUDE_PLUGIN_DATA}}/requirements.txt\\""
                  }}
                ]
              }}
            ],
            "PostToolUse": [
              {{
                "matcher": "mcp__plugin_{plugin_name}_{plugin_name}__speak_{safe_id}",
                "hooks": [
                  {{
                    "type": "command",
                    "command": "echo '{{\\\"hookSpecificOutput\\\": {{\\\"hookEventName\\\": \\\"PostToolUse\\\", \\\"additionalContext\\\": \\\"After showing the user the tool result, please display this legal disclaimer verbatim: [legal hook] The views expressed above do not necessarily represent the views of {animal_species}s, their families, or their habitats.\\\"}}}}'"
                  }}
                ]
              }}
            ]
          }}
        }}
    """)

    # requirements.txt
    _write("requirements.txt", """\
        mcp>=1.0.0
    """)

    # server.py
    _write("server.py", f"""\
        \"\"\"MCP server for {plugin_name}.\"\"\"

        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("{plugin_name}")


        @mcp.tool()
        def speak_{safe_id}() -> str:
            \"\"\"Say something like a {animal_species}.\"\"\"
            return "{common_saying}"


        if __name__ == "__main__":
            mcp.run(transport="stdio")
    """)

    # skills/speak-animal/SKILL.md
    _write("skills/speak-animal/SKILL.md", """\
        ---
        name: speak-animal
        description: Speak as any animal. Use when asked to talk like, speak as, say something as, or imitate any animal.
        user-invocable: true
        argument-hint: "[animal]"
        ---

        # Speak Animal

        When the user asks you to speak as an animal:

        1. Check if a `speak_<animal>` tool is available for that
           species (e.g., `speak_alligator`, `speak_cat`).
        2. If the tool exists, call it and present what it says.
        3. If no tool exists for that animal, tell the user:
           "I'm not an expert on that one, but I'll give it my best
           shot." Then give your very best impression of what that
           animal would say. Be creative and have fun with it.
    """)

    tool_pattern = f"mcp__plugin_{plugin_name}_{plugin_name}__*"
    test_cmd = (
        f'claude -p "Can you say something as a {animal_species}?" '
        f'--plugin-dir={target} --allowedTools "{tool_pattern}"'
    )

    return {
        "plugin_name": plugin_name,
        "path": str(target),
        "files_created": files_created,
        "test_command": test_cmd,
        "next_steps": (
            f"The plugin is ready. Rename speak_{safe_id} to your real tool, "
            f"or test it now with:\n  ! {test_cmd}"
        ),
    }


@mcp.tool()
def debug_plugin(
    prompt: str,
    path: str | None = None,
) -> dict:
    """Run a headless Claude session to test a plugin.

    Launches claude with --plugin-dir pointed at the plugin and a natural
    language prompt. Returns the session output.

    IMPORTANT guidance for the calling agent:
    - The prompt MUST describe intent in natural language, NOT name a
      specific tool (e.g., "say something as an alligator" not
      "call speak_alligator"). This validates auto-discovery.
    - Do NOT use this on long-running tools (deploys, builds, CI).
      It's for quick functional checks only.

    Args:
        prompt: Natural-language phrase that should trigger the plugin.
        path: Plugin directory. Defaults to current working directory.
    """
    target = Path(path) if path else Path.cwd()

    if not (target / ".claude-plugin" / "plugin.json").exists():
        return {
            "error": f"No plugin found at {target}. Missing .claude-plugin/plugin.json.",
        }

    # Discover MCP tool names to pre-approve them
    allowed = []
    mcp_json = target / ".mcp.json"
    if mcp_json.exists():
        mcp_cfg = json.loads(mcp_json.read_text())
        for server_name in mcp_cfg.get("mcpServers", {}):
            # Plugin MCP tools are namespaced as mcp__plugin_<name>_<server>__*
            plugin_json = target / ".claude-plugin" / "plugin.json"
            if plugin_json.exists():
                plugin_name = json.loads(plugin_json.read_text()).get("name", server_name)
                allowed.append(f"mcp__plugin_{plugin_name}_{server_name}__*")

    cmd = ["claude", "-p", prompt, f"--plugin-dir={target}"]
    if allowed:
        cmd.extend(["--allowedTools", ",".join(allowed)])

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(target),
    )

    return {
        "path": str(target),
        "prompt": prompt,
        "output": result.stdout.strip() if result.stdout else result.stderr.strip(),
        "exit_code": result.returncode,
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
