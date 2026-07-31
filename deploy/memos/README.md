# Official ModelScope MemOS MCP for trade memory

The self-hosted MemOS deployment has been removed. The trade runtime can use the official ModelScope/MemTensor MCP server through stdio, while the local project database remains the audit source of truth.

## Runtime mode

Use `hybrid` mode so local `agent_memory` stays primary and the official MCP is a best-effort semantic memory enhancement:

```env
TRADE_RUNTIME_MEMORY_STORE=hybrid
TRADE_RUNTIME_MEMOS_MCP_TRANSPORT=stdio
TRADE_RUNTIME_MEMOS_MCP_COMMAND=npx
TRADE_RUNTIME_MEMOS_MCP_ARGS_JSON=["-y","@memtensor/memos-api-mcp@latest"]
TRADE_RUNTIME_MEMOS_API_KEY=replace-with-official-modelscope-memos-key
TRADE_RUNTIME_MEMOS_USER_ID=trade-runtime
TRADE_RUNTIME_MEMOS_CHANNEL=MODELSCOPE
TRADE_RUNTIME_MEMOS_TIMEOUT_SECONDS=20
TRADE_RUNTIME_MEMOS_WRITE_ENABLED=true
TRADE_RUNTIME_MEMOS_SEARCH_ENABLED=true
```

Do not commit `TRADE_RUNTIME_MEMOS_API_KEY`. Put it in the runtime environment only.

## Notes

- This no longer needs `/opt/trade-memos`, Qdrant, Neo4j, Docker Compose, or systemd services.
- The official MCP is launched on demand by `npx`; install Node.js/npm where the Python worker runs.
- First `npx` startup may exceed `20s` while the package cache is populated. Pre-warm with `npx -y @memtensor/memos-api-mcp@latest` if needed.
- The trading system still passes normalized `long_term_memory_json` to the supervisor agent; the supervisor does not directly call tools.

## Official page

- https://www.modelscope.cn/mcp/servers/MemTensor/MemoryOperatingSystem
