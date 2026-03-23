# MCP Tool Proxying and Orchestration

Plugins introduce skills — opinionated workflows that compose multiple
MCP tools into higher-level operations. When a skill depends on tools
from an external MCP server (e.g., a financial API), the plugin can
either leave orchestration to the LLM or have its own MCP server
mediate those calls directly. This document captures whether that
mediation pattern is appropriate and what authoritative sources say
about it.

## Is it appropriate for an MCP tool to call another MCP tool?

**Yes.** This is explicitly intended by the protocol's creators,
supported by the spec's definitions, and implemented in major
frameworks.

---

### 1. The spec does not restrict clients to LLMs

The [official MCP architecture docs](https://modelcontextprotocol.io/docs/learn/architecture)
define the three participants:

> - **MCP Host**: The AI application that coordinates and manages one
>   or multiple MCP clients
> - **MCP Client**: A component that maintains a connection to an MCP
>   server and obtains context from an MCP server for the MCP host to
>   use
> - **MCP Server**: A program that provides context to MCP clients
>
> — [modelcontextprotocol.io/docs/learn/architecture](https://modelcontextprotocol.io/docs/learn/architecture)

A client is "a component that maintains a connection" — not "an LLM"
or "an agent." The [official client list](https://modelcontextprotocol.io/clients)
includes IDEs (VS Code, Cursor), CLI tools (Claude Code, Gemini CLI,
Amazon Q CLI), and frameworks (Genkit by Google/Firebase, BeeAI,
fast-agent). An MCP server that internally instantiates a
`ClientSession` to call another server is simply a program using the
client protocol — fully within the spec.

The spec also notes:

> MCP focuses solely on the protocol for context exchange — it does not
> dictate how AI applications use LLMs or manage the provided context.
>
> — [modelcontextprotocol.io/docs/learn/architecture](https://modelcontextprotocol.io/docs/learn/architecture)

---

### 2. The protocol creators explicitly endorse this pattern

David Soria Parra is an MCP co-creator at Anthropic, confirmed via his
[contributions to the official SDK](https://github.com/modelcontextprotocol/python-sdk/commits?author=dsp-ant)
(he authored the [commit that integrated FastMCP](https://github.com/modelcontextprotocol/python-sdk/commit/557e90d)
into the official SDK). In an
[interview on Latent Space](https://www.latent.space/p/mcp), he stated:

On servers simultaneously acting as clients:

> You can easily envision an MCP server that serves something to like
> something like Cursor or [Claude Desktop], but at the same time, also
> is an MCP client at the same time.
>
> — David Soria Parra, [Latent Space](https://www.latent.space/p/mcp)

On the recursive, composable design being intentional:

> We actually quite carefully in the design principles, try to retain
> [...] this recursive pattern.
>
> — David Soria Parra, [Latent Space](https://www.latent.space/p/mcp)

On building directed acyclic graphs of MCP servers:

> And now you have a recursive property... you have this little bundle
> of applications, both a server and a client. And I can add these in
> chains and build basically graphs like, uh, DAGs out of MCP servers.
>
> — David Soria Parra, [Latent Space](https://www.latent.space/p/mcp)

On using proxy servers specifically to manage tool overload:

> You could use an MCP server, which is a proxy to other MCP servers
> and does some filtering at that level or something like that.
>
> — David Soria Parra, [Latent Space](https://www.latent.space/p/mcp)

---

### 3. The official SDK provides client building blocks

The [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
(`pip install mcp`) includes a full client module alongside the server.
The official [MCP architecture docs](https://modelcontextprotocol.io/docs/learn/architecture)
show `ClientSession` usage in pseudocode:

```python
# From modelcontextprotocol.io architecture example
async with stdio_client(server_config) as (read, write):
    async with ClientSession(read, write) as session:
        init_response = await session.initialize()
```

And tool execution via the client:

```python
# From modelcontextprotocol.io architecture example
result = await session.call_tool(tool_name, arguments)
```

These are the same primitives a proxy server would use internally.
The official [Build an MCP client](https://modelcontextprotocol.io/docs/develop/build-client)
tutorial walks through `session.call_tool()` as a standard operation.

See [mcp-framework.md](mcp-framework.md) for details on the SDK.

---

### 4. Major frameworks implement dedicated proxy support

The standalone [FastMCP](https://gofastmcp.com) project (whose v1.0
was [integrated into the official SDK](https://github.com/modelcontextprotocol/python-sdk/commit/557e90d))
has a built-in [proxy provider](https://gofastmcp.com/patterns/proxy):

> Make an HTTP server available via stdio, or vice versa. Combine
> multiple source servers into one unified server. Act as a controlled
> gateway with authentication and authorization.
>
> — [FastMCP proxy docs](https://gofastmcp.com/patterns/proxy)

It also provides multi-server composition out of the box:

> Provide a stable endpoint even if backend servers change.
>
> — [FastMCP proxy docs](https://gofastmcp.com/patterns/proxy)

The official `mcp` SDK provides the same building blocks
(`ClientSession`, `streamablehttp_client`) without a dedicated proxy
abstraction, but the composition is straightforward — see the code
example in [plugin-patterns.md](plugin-patterns.md#server-and-client-in-one-process).

---

### 5. The actual anti-pattern

The anti-pattern is not wrapping or proxying — it's the opposite:
exposing raw API operations 1-to-1 as MCP tools without adding
semantic value. The MCP creators designed the proxy pattern precisely
to solve tool overload — filtering and composing lower-level tools
into higher-level intent-based operations so the LLM doesn't have to
navigate dozens of fine-grained endpoints. David Soria Parra's quote
above about "filtering at that level" addresses this directly.

---

## Why this matters for plugins

Our current architecture (documented in
[bills-agent CONTRIBUTING.md](https://github.com/krisrowe/bills-agent/blob/main/CONTRIBUTING.md))
uses the LLM as the sole orchestrator: the skill instructs the LLM
to call tools from two independent MCP servers (the plugin's own
server and an external one), with `PostToolUse` hooks caching external
responses to disk for later use by the plugin's server.

This works but has costs:

- **Dependency management** — the external MCP server must be
  separately installed and registered; the plugin can't guarantee it
  exists
- **Coupling via hooks** — the plugin's hooks must understand the
  external server's response format, creating a versioning dependency
  between independently maintained projects
- **Skill complexity** — the skill must include detailed multi-phase
  instructions for the LLM to call the right tools in the right order
  from the right servers
- **Context bloat** — exposing two full tool sets to the LLM consumes
  tokens before any reasoning occurs

A proxy/orchestrator pattern addresses all of these: the plugin's MCP
server calls the external server directly, exposing only high-level
intent-based tools to the LLM. The skill becomes simpler, the hooks
become unnecessary, and the external dependency is managed in code
rather than in installation instructions.

## Assessment (2026-03-23)

Tool-level orchestration via MCP proxy/client patterns is:

- **Explicitly intended** by the protocol co-creator (David Soria
  Parra, Anthropic) who described recursive server-client composition,
  DAGs of MCP servers, and proxy filtering in a
  [recorded interview](https://www.latent.space/p/mcp)
- **Supported by the spec** which defines clients as protocol
  components, not LLM-specific constructs
  ([architecture docs](https://modelcontextprotocol.io/docs/learn/architecture))
- **Implemented in frameworks** including FastMCP's dedicated
  [proxy provider](https://gofastmcp.com/patterns/proxy)
- **Buildable with the official SDK** using `ClientSession` and
  `call_tool()` as documented in the
  [official tutorial](https://modelcontextprotocol.io/docs/develop/build-client)

It is not an anti-pattern. We plan to adopt this pattern for plugins
that wrap external MCP servers, replacing the current hook-based
caching approach. See
[plugin-patterns.md](plugin-patterns.md#mcp-orchestration) for the
implementation pattern using the official `mcp` SDK.
