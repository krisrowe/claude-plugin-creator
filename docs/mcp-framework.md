# MCP Framework

Which MCP framework we use, what it provides, and how it relates to
other packages in the ecosystem.

## The two Python packages

There are two Python packages for building MCP servers. Both provide a
class called `FastMCP` with similar decorator-based APIs, but they are
separate packages with different maintainers.

### 1. MCP Python SDK (`mcp`)

The official SDK maintained under the
[modelcontextprotocol](https://github.com/modelcontextprotocol) GitHub
org.

| | |
|---|---|
| **Install** | `pip install mcp` or `uv add "mcp[cli]"` |
| **Import** | `from mcp.server.fastmcp import FastMCP` |
| **Source** | [github.com/modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk) |
| **PyPI** | [pypi.org/project/mcp](https://pypi.org/project/mcp/) |
| **Docs** | Inline in the [GitHub README](https://github.com/modelcontextprotocol/python-sdk#readme) |

> The FastMCP server is your core interface to the MCP protocol. It
> handles connection management, protocol compliance, and message
> routing.
>
> — [MCP Python SDK on PyPI](https://pypi.org/project/mcp/)

Provides:
- **FastMCP server** — decorator-based tools, resources, prompts
- **Client module** (`from mcp import ClientSession`) — call tools on
  other MCP servers over stdio, SSE, or streamable HTTP
- **Transport security** — for authenticated HTTP servers

The official [MCP quickstart](https://modelcontextprotocol.io/quickstart/server)
uses this package:

> ```bash
> uv add "mcp[cli]" httpx
> ```
> ```python
> from mcp.server.fastmcp import FastMCP
> ```
>
> — [modelcontextprotocol.io/quickstart/server](https://modelcontextprotocol.io/quickstart/server)

### 2. Standalone FastMCP (`fastmcp`)

A separate package by Jeremiah Lowin (confirmed as author on
[PyPI](https://pypi.org/project/fastmcp/)), founder of
[Prefect](https://www.prefect.io/).

| | |
|---|---|
| **Install** | `pip install fastmcp` or `uv add fastmcp` |
| **Import** | `from fastmcp import FastMCP` |
| **Source** | [github.com/jlowin/fastmcp](https://github.com/jlowin/fastmcp) |
| **PyPI** | [pypi.org/project/fastmcp](https://pypi.org/project/fastmcp/) |
| **Docs** | [gofastmcp.com](https://gofastmcp.com) |

> The fast, Pythonic way to build MCP servers, clients, and
> applications. Servers wrap your Python functions into MCP-compliant
> tools, resources, and prompts. Clients connect to any server with
> full protocol support.
>
> — [gofastmcp.com](https://gofastmcp.com/getting-started/welcome)

Provides everything in the official SDK plus additional features
including a richer [client API](https://gofastmcp.com/clients/client)
with automatic transport selection and multi-server configuration.

The standalone project frames the version bundled in the official `mcp`
SDK as "FastMCP 1.0" and positions itself as the actively maintained
successor:

> If you're using FastMCP 1.0 via the `mcp` package (meaning you
> import FastMCP as `from mcp.server.fastmcp import FastMCP`),
> upgrading is straightforward.
>
> — [gofastmcp.com/getting-started/installation](https://gofastmcp.com/getting-started/installation)

## What we chose and why

**We use the official `mcp` SDK.** All our servers import from
`mcp.server.fastmcp`, not from `fastmcp`.

Reasons:

1. **It's what the protocol authors recommend.** The official MCP
   quickstart at [modelcontextprotocol.io](https://modelcontextprotocol.io/quickstart/server)
   uses `uv add "mcp[cli]"` and `from mcp.server.fastmcp import FastMCP`.

2. **Fewer dependencies.** One package (`mcp`) covers both server and
   client. No need to evaluate version compatibility between two
   packages that expose the same class name.

3. **Sufficient for our needs.** We build straightforward tool servers
   and (planned) client calls to remote MCP servers. The official SDK's
   `FastMCP` and `ClientSession` cover both cases.

4. **Stability.** The standalone `fastmcp` evolves faster, which means
   more features but also more churn. For tools we deploy and rely on,
   we prefer the conservative choice.

If a future need arises that only the standalone `fastmcp` supports
(e.g., its multi-server client configuration), we can evaluate
switching at that point.

**Assessment (2026-03-23):** If starting from scratch today, we would
make the same choice. The official SDK is where protocol changes land
first (MCP is authored by Anthropic; the SDK is maintained under their
org). The standalone `fastmcp`'s advantages are ergonomic (nicer client
config, multi-server setup) rather than capability gaps. The one
scenario favoring standalone `fastmcp` would be a client-heavy
application aggregating many MCP servers, where the richer client API
would save significant code. Our tools are server-heavy with limited
client needs (calling one remote server), so the official SDK covers
us. Revisit if client requirements grow.

## History

The standalone `fastmcp` was created first. The official SDK integrated
it in late 2024. This is confirmed in the SDK's own git history:

> This commit integrates FastMCP, a high-level MCP server implementation
> originally written by Jeremiah Lowin, into the official MCP SDK.
>
> — Commit [557e90d](https://github.com/modelcontextprotocol/python-sdk/commit/557e90d),
> December 21, 2024, by David Soria Parra (dsp-ant),
> [modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk/commits/main/src/mcp/server/fastmcp)

After integration, the two projects diverged. The official SDK's
version stayed at roughly the FastMCP 1.0 API. The standalone project
continued adding features and now considers the SDK's bundled version
a legacy baseline.

## Working examples

All of these use `from mcp.server.fastmcp import FastMCP` (the official
`mcp` SDK):

- [bills-agent/bills/mcp/server.py](https://github.com/krisrowe/bills-agent/blob/main/bills/mcp/server.py) — local config management with cross-reference against a financial API
- [monarch-access/monarch/mcp/server.py](https://github.com/krisrowe/monarch-access/blob/main/monarch/mcp/server.py) — remote HTTP server wrapping a financial API
- [dotfiles-manager/dotgit/mcp/server.py](https://github.com/krisrowe/dotfiles-manager/blob/main/dotgit/mcp/server.py) — local filesystem tool (git-based dotfile management)
