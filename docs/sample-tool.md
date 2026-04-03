# Sample Tool: `speak_<animal>`

The scaffolded plugin includes a single MCP tool that demonstrates
the self-installing pattern working end-to-end.

## What it generates

For `scaffold_plugin("alligator", "After while, crocodile")`:

```python
"""MCP server for alligator-speak."""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("alligator-speak")


@mcp.tool()
def speak_alligator() -> str:
    """Say something like a alligator."""
    return "After while, crocodile"


if __name__ == "__main__":
    mcp.run(transport="stdio")
```

## What this proves

When this tool responds correctly, you know:

- The `SessionStart` hook installed `mcp` into the plugin's
  isolated `site-packages`
- `PYTHONPATH` is set correctly in `.mcp.json`
- The MCP server started via `python3` and connected over stdio
- Claude discovered and invoked the tool by matching user intent

## Expected output

```
> speak alligator

🐊 "After while, crocodile!"
```

## Next steps

Rename `speak_alligator` to your real tool, update `server.py`
with your actual logic, and add dependencies to `requirements.txt`.
The plugin infrastructure (hooks, `.mcp.json`, `plugin.json`) stays
the same.
