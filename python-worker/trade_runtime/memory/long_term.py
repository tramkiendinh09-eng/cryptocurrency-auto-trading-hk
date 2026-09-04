"""
长期记忆存储模块 - 存储和检索历史决策记忆

实现交易系统的长期记忆功能，用于存储和检索历史决策、交易结果等。

长期记忆的作用:
1. 为Agent提供历史决策参考
2. 存储成功/失败案例供后续学习
3. 支持基于标签的记忆检索
4. 记录记忆使用情况用于分析

记忆存储实现:
- NullLongTermMemoryStore: 空实现，不存储任何记忆
- InMemoryLongTermMemoryStore: 内存存储，用于测试
- HttpLongTermMemoryStore: HTTP存储，连接后端服务

记忆数据结构:
```
{
    "id": 123,                        # 记忆ID
    "agent_code": "market_agent",     # Agent代码
    "symbol": "BTCUSDT",              # 交易品种
    "event_tags": ["breakout", "volume"],  # 事件标签
    "quality_score": 0.85,            # 质量得分
    "content": {...},                 # 记忆内容
    "created_at": "2024-01-01T00:00:00Z",  # 创建时间
}
```

使用流程:
```
1. 检索记忆
   memory_store.search(
       agent_code="market_agent",
       symbol="BTCUSDT",
       tags=["breakout"],
       limit=5
   )

2. 记录使用
   memory_store.record_usage(
       trace_id="abc123",
       symbol="BTCUSDT",
       memory_ids=[1, 2, 3]
   )

3. 创建记忆
   memory_store.create_memory({
       "agent_code": "market_agent",
       "symbol": "BTCUSDT",
       "event_tags": ["breakout"],
       "content": {...}
   })
```
"""

from __future__ import annotations

from typing import Any, Protocol

import json
import logging
import os
import subprocess

import requests

logger = logging.getLogger(__name__)


class LongTermMemoryStore(Protocol):
    """长期记忆存储协议

    定义长期记忆存储的接口规范。
    """

    def search(
        self,
        *,
        agent_code: str,
        symbol: str,
        tags: list[str],
        limit: int,
    ) -> list[dict[str, Any]]:
        """搜索记忆

        Args:
            agent_code: Agent代码
            symbol: 交易品种
            tags: 标签列表
            limit: 返回数量限制

        Returns:
            list[dict[str, Any]]: 匹配的记忆列表
        """
        ...

    def record_usage(self, *, trace_id: str, symbol: str, memory_ids: list[int | str]) -> None:
        """记录记忆使用情况

        Args:
            trace_id: 追踪ID
            symbol: 交易品种
            memory_ids: 使用的记忆ID列表
        """
        ...

    def create_memory(self, memory: dict[str, Any]) -> dict[str, Any]:
        """创建新记忆

        Args:
            memory: 记忆数据

        Returns:
            dict[str, Any]: 创建的记忆(包含ID)
        """
        ...


class NullLongTermMemoryStore:
    """空长期记忆存储

    不存储任何记忆，用于禁用记忆功能的场景。
    """

    def search(
        self,
        *,
        agent_code: str,
        symbol: str,
        tags: list[str],
        limit: int,
    ) -> list[dict[str, Any]]:
        return []

    def record_usage(self, *, trace_id: str, symbol: str, memory_ids: list[int | str]) -> None:
        return None

    def create_memory(self, memory: dict[str, Any]) -> dict[str, Any]:
        return {}


class InMemoryLongTermMemoryStore:
    """内存长期记忆存储

    将记忆存储在内存中，用于测试和开发环境。
    """

    def __init__(self, items: list[dict[str, Any]] | None = None):
        """初始化内存存储

        Args:
            items: 初始记忆列表
        """
        self.items = [dict(item) for item in (items or [])]
        self.usages: list[dict[str, Any]] = []

    def search(
        self,
        *,
        agent_code: str,
        symbol: str,
        tags: list[str],
        limit: int,
    ) -> list[dict[str, Any]]:
        """搜索记忆

        根据Agent代码、交易品种和标签搜索记忆，
        按标签匹配数和质量得分排序。

        Args:
            agent_code: Agent代码
            symbol: 交易品种
            tags: 标签列表
            limit: 返回数量限制

        Returns:
            list[dict[str, Any]]: 匹配的记忆列表
        """
        normalized_agent = str(agent_code or "").strip()
        normalized_symbol = str(symbol or "").strip().upper()
        tag_set = {str(tag).strip().lower() for tag in tags if str(tag).strip()}

        def score(item: dict[str, Any]) -> tuple[float, float]:
            """计算记忆得分

            Args:
                item: 记忆项

            Returns:
                tuple[float, float]: (标签匹配得分, 质量得分)
            """
            item_tags = {str(tag).strip().lower() for tag in item.get("event_tags") or []}
            tag_score = len(tag_set & item_tags)
            quality = float(item.get("quality_score") or 0.0)
            return (float(tag_score), quality)

        filtered = [
            item
            for item in self.items
            if str(item.get("agent_code") or "").strip() == normalized_agent
            and str(item.get("symbol") or "").strip().upper() == normalized_symbol
        ]
        filtered.sort(key=score, reverse=True)
        return [dict(item) for item in filtered[: max(0, int(limit))]]

    def record_usage(self, *, trace_id: str, symbol: str, memory_ids: list[int | str]) -> None:
        """记录记忆使用情况

        Args:
            trace_id: 追踪ID
            symbol: 交易品种
            memory_ids: 使用的记忆ID列表
        """
        self.usages.append({"trace_id": trace_id, "symbol": symbol, "memory_ids": list(memory_ids)})

    def create_memory(self, memory: dict[str, Any]) -> dict[str, Any]:
        """创建新记忆

        Args:
            memory: 记忆数据

        Returns:
            dict[str, Any]: 创建的记忆(包含自动生成的ID)
        """
        created = dict(memory)
        created.setdefault("id", len(self.items) + 1)
        self.items.append(created)
        return dict(created)


class HttpLongTermMemoryStore:
    """HTTP长期记忆存储

    通过HTTP API连接后端服务存储记忆。
    """

    def __init__(self, *, base_url: str, bearer_token: str = "", timeout: int = 5):
        """初始化HTTP存储

        Args:
            base_url: API基础URL
            bearer_token: 认证令牌
            timeout: 请求超时时间(秒)
        """
        self.base_url = str(base_url or "").rstrip("/")
        self.bearer_token = bearer_token
        self.timeout = timeout
        self._memory_agents_by_id: dict[str, str] = {}

    def _headers(self) -> dict[str, str]:
        """构建请求头

        Returns:
            dict[str, str]: 请求头字典
        """
        headers = {"Accept": "application/json"}
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        return headers

    def search(
        self,
        *,
        agent_code: str,
        symbol: str,
        tags: list[str],
        limit: int,
    ) -> list[dict[str, Any]]:
        if not self.base_url:
            return []
        normalized_tags = [str(tag).strip() for tag in tags if str(tag).strip()]
        response = requests.get(
            f"{self.base_url}/dca/agent-memory/list",
            params={"agentCode": agent_code, "symbol": symbol, "limit": limit, "tags": normalized_tags},
            headers=self._headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        rows = payload.get("data") if isinstance(payload, dict) else payload
        if not isinstance(rows, list):
            return []
        normalized_rows = [self._normalize_item(row) for row in rows if isinstance(row, dict)]
        for item in normalized_rows:
            memory_id = item.get("id")
            agent = str(item.get("agent_code") or "").strip()
            if memory_id is not None and agent:
                self._memory_agents_by_id[str(memory_id)] = agent
        return normalized_rows

    def record_usage(self, *, trace_id: str, symbol: str, memory_ids: list[int | str]) -> None:
        if not self.base_url:
            return None
        for memory_id in memory_ids:
            payload = {"traceId": trace_id, "symbol": symbol, "memoryId": memory_id, "usageContextJson": "{}"}
            agent_code = self._memory_agents_by_id.get(str(memory_id), "")
            if agent_code:
                payload["agentCode"] = agent_code
            response = requests.post(
                f"{self.base_url}/dca/agent-memory/usage",
                json=payload,
                headers=self._headers(),
                timeout=self.timeout,
            )
            response.raise_for_status()
        return None


    def create_memory(self, memory: dict[str, Any]) -> dict[str, Any]:
        if not self.base_url:
            return {}
        response = requests.post(
            f"{self.base_url}/dca/agent-memory",
            json=self._to_camel_payload(memory),
            headers=self._headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()

        # RuoYi 的认证失败返回 **HTTP 200**，把 401 装在 body 的 code 里，
        # 所以上面的 raise_for_status() 不会抛。之前 add 端点漏标 @Anonymous，
        # 每一次写入都被拒，而这里只是静静地 return {}，上层归成笼统的
        # memory_store_create_failed——agent_memory 表从部署起一行都没有，
        # 而日志里看不出是鉴权问题。这里必须把 code 单独判出来并记下来。
        code = payload.get("code") if isinstance(payload, dict) else None
        if code is not None and str(code) not in {"200", "0"}:
            logger.error(
                "agent memory create rejected code=%s msg=%s",
                code,
                (payload or {}).get("msg"),
            )
            return {}

        data = payload.get("data") if isinstance(payload, dict) else payload
        if isinstance(data, dict) and data:
            return data
        if isinstance(data, int) and not isinstance(data, bool) and data > 0:
            created = dict(memory)
            created.setdefault("id", None)
            return created

        # RuoYi 的 toAjax() 成功时只返回 {"code":200,"msg":"操作成功"}，**不带 data**。
        # 按 data 判成败会把成功的写入也报成失败。
        if code is not None and str(code) in {"200", "0"}:
            created = dict(memory)
            created.setdefault("id", None)
            return created
        return {}

    def _to_camel_payload(self, memory: dict[str, Any]) -> dict[str, Any]:
        event_tags = memory.get("event_tags") or []
        event_tags_json = memory.get("event_tags_json") or json.dumps(event_tags, ensure_ascii=False)
        evidence_json = memory.get("evidence_json")
        if isinstance(evidence_json, (dict, list)):
            evidence_json = json.dumps(evidence_json, ensure_ascii=False)
        outcome_json = memory.get("outcome_json")
        if isinstance(outcome_json, (dict, list)):
            outcome_json = json.dumps(outcome_json, ensure_ascii=False)
        return {
            "memoryKey": memory.get("memory_key"),
            "agentCode": memory.get("agent_code") or memory.get("agentCode"),
            "symbol": memory.get("symbol"),
            "memoryType": memory.get("memory_type") or memory.get("memoryType"),
            "marketRegime": memory.get("market_regime") or memory.get("marketRegime"),
            "eventTagsJson": event_tags_json,
            "direction": memory.get("direction"),
            "action": memory.get("action"),
            "lessonText": memory.get("lesson_text") or memory.get("lessonText"),
            "evidenceJson": evidence_json,
            "outcomeJson": outcome_json,
            "qualityScore": memory.get("quality_score") or memory.get("qualityScore") or 0.0,
            "confidence": memory.get("confidence") or 0.0,
            "sourceTraceId": memory.get("source_trace_id") or memory.get("sourceTraceId"),
            "enabled": memory.get("enabled", True),
        }

    def _normalize_item(self, row: dict[str, Any]) -> dict[str, Any]:
        event_tags = row.get("event_tags") or row.get("eventTags") or []
        event_tags_json = row.get("eventTagsJson") or row.get("event_tags_json")
        if not event_tags and event_tags_json:
            try:
                parsed = json.loads(event_tags_json)
                if isinstance(parsed, list):
                    event_tags = parsed
            except (TypeError, ValueError):
                event_tags = []
        return {
            "id": row.get("id"),
            "agent_code": row.get("agentCode") or row.get("agent_code") or "",
            "symbol": row.get("symbol") or "",
            "memory_type": row.get("memoryType") or row.get("memory_type") or "",
            "market_regime": row.get("marketRegime") or row.get("market_regime") or "",
            "event_tags": event_tags,
            "direction": row.get("direction") or "",
            "action": row.get("action") or "",
            "lesson_text": row.get("lessonText") or row.get("lesson_text") or "",
            "evidence_json": row.get("evidenceJson") or row.get("evidence_json") or "",
            "outcome_json": row.get("outcomeJson") or row.get("outcome_json") or "",
            "quality_score": float(row.get("qualityScore") or row.get("quality_score") or 0.0),
            "confidence": float(row.get("confidence") or 0.0),
            "source_trace_id": row.get("sourceTraceId") or row.get("source_trace_id") or "",
            "created_at": row.get("createdAt") or row.get("created_at") or "",
        }


class McpLongTermMemoryStore:
    """Long-term memory store backed by an HTTP MCP memory service."""

    def __init__(
        self,
        *,
        mcp_url: str = "",
        user_id: str = "trade-runtime",
        channel: str = "production",
        bearer_token: str = "",
        timeout: int = 20,
        search_tool: str = "search_memories",
        add_tool: str = "add_memory",
        search_enabled: bool = True,
        write_enabled: bool = True,
        transport: str = "http",
        command: str = "",
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
    ):
        self.mcp_url = str(mcp_url or "").strip()
        self.user_id = str(user_id or "trade-runtime").strip() or "trade-runtime"
        self.channel = str(channel or "production").strip() or "production"
        self.bearer_token = str(bearer_token or "")
        self.timeout = int(timeout or 20)
        self.search_tool = str(search_tool or "search_memories").strip() or "search_memories"
        self.add_tool = str(add_tool or "add_memory").strip() or "add_memory"
        self.search_enabled = bool(search_enabled)
        self.write_enabled = bool(write_enabled)
        transport_value = transport or ("stdio" if command and not mcp_url else "http")
        self.transport = str(transport_value).strip().lower()
        self.command = str(command or "").strip()
        self.args = [str(arg) for arg in (args or [])]
        self.env = {str(key): str(value) for key, value in (env or {}).items() if value not in (None, "")}
        self._session_id = ""

    def _has_backend(self) -> bool:
        return bool(self.mcp_url) or (self.transport == "stdio" and bool(self.command))

    def _headers(self, *, include_session: bool = True) -> dict[str, str]:
        headers = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        if include_session and self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
        return headers

    def _ensure_session(self) -> None:
        if self._session_id or not self.mcp_url:
            return
        payload = {
            "jsonrpc": "2.0",
            "id": "trade-memory-initialize",
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "trade-runtime", "version": "1.0.0"},
            },
        }
        response = requests.post(self.mcp_url, json=payload, headers=self._headers(include_session=False), timeout=self.timeout)
        response.raise_for_status()
        session_id = self._response_header(response, "mcp-session-id")
        if session_id:
            self._session_id = session_id
            initialized_payload = {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}
            initialized_response = requests.post(
                self.mcp_url,
                json=initialized_payload,
                headers=self._headers(),
                timeout=self.timeout,
            )
            initialized_response.raise_for_status()

    def _response_header(self, response: Any, name: str) -> str:
        headers = getattr(response, "headers", {}) or {}
        if hasattr(headers, "get"):
            return str(headers.get(name) or headers.get(name.lower()) or headers.get(name.upper()) or "")
        return ""

    def _parse_response_payload(self, response: Any) -> dict[str, Any]:
        content_type = self._response_header(response, "content-type").lower()
        if "text/event-stream" in content_type:
            text = str(getattr(response, "text", "") or "")
            for line in text.splitlines():
                if not line.startswith("data:"):
                    continue
                data = line.split(":", 1)[1].strip()
                if not data:
                    continue
                try:
                    parsed = json.loads(data)
                except (TypeError, ValueError):
                    continue
                return parsed if isinstance(parsed, dict) else {}
            return {}
        parsed = response.json()
        return parsed if isinstance(parsed, dict) else {}

    def _call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if self.transport == "stdio":
            return self._call_stdio_tool(tool_name, arguments)
        if not self.mcp_url:
            return {}
        self._ensure_session()
        payload = {
            "jsonrpc": "2.0",
            "id": f"trade-memory-{tool_name}",
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }
        response = requests.post(self.mcp_url, json=payload, headers=self._headers(), timeout=self.timeout)
        response.raise_for_status()
        return self._parse_response_payload(response)

    def _call_stdio_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if not self.command:
            return {}
        call_id = f"trade-memory-{tool_name}"
        messages = [
            {
                "jsonrpc": "2.0",
                "id": "trade-memory-initialize",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "trade-runtime", "version": "1.0.0"},
                },
            },
            {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
            {
                "jsonrpc": "2.0",
                "id": call_id,
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments},
            },
        ]
        process_env = os.environ.copy()
        process_env.update(self.env)
        input_bytes = b"".join(self._encode_stdio_message(message) for message in messages)
        try:
            completed = subprocess.run(
                [self.command, *self.args],
                input=input_bytes,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=process_env,
                timeout=self.timeout,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            logger.warning("stdio MCP tool call failed: %s", exc.__class__.__name__)
            return {}
        if completed.returncode not in (0, None) and not completed.stdout:
            logger.warning("stdio MCP tool call exited with code %s", completed.returncode)
            return {}
        responses = self._parse_stdio_messages(completed.stdout or b"")
        for response in responses:
            if response.get("id") == call_id:
                return response
        return responses[-1] if responses else {}

    def _encode_stdio_message(self, message: dict[str, Any]) -> bytes:
        body = json.dumps(message, ensure_ascii=False).encode("utf-8")
        return f"Content-Length: {len(body)}\r\n\r\n".encode("ascii") + body

    def _parse_stdio_messages(self, data: bytes) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        index = 0
        crlf_separator = bytes([13, 10, 13, 10])
        lf_separator = bytes([10, 10])
        while index < len(data):
            header_start = data.find(b"Content-Length:", index)
            if header_start < 0:
                break
            header_end = data.find(crlf_separator, header_start)
            separator_length = len(crlf_separator)
            if header_end < 0:
                header_end = data.find(lf_separator, header_start)
                separator_length = len(lf_separator)
            if header_end < 0:
                break
            header = data[header_start:header_end].decode("ascii", errors="ignore")
            content_length = 0
            for line in header.splitlines():
                if line.lower().startswith("content-length:"):
                    try:
                        content_length = int(line.split(":", 1)[1].strip())
                    except ValueError:
                        content_length = 0
                    break
            body_start = header_end + separator_length
            body_end = body_start + content_length
            if content_length <= 0 or body_end > len(data):
                break
            try:
                parsed = json.loads(data[body_start:body_end].decode("utf-8"))
            except (TypeError, ValueError, UnicodeDecodeError):
                parsed = None
            if isinstance(parsed, dict):
                messages.append(parsed)
            index = body_end
        return messages

    def search(
        self,
        *,
        agent_code: str,
        symbol: str,
        tags: list[str],
        limit: int,
    ) -> list[dict[str, Any]]:
        if not self.search_enabled or not self._has_backend():
            return []
        result_limit = max(0, int(limit or 0))
        if result_limit <= 0:
            return []
        normalized_tags = [str(tag).strip() for tag in tags if str(tag).strip()]
        query_parts = [str(symbol or "").strip().upper(), str(agent_code or "").strip(), *normalized_tags]
        query = " ".join(part for part in query_parts if part)
        if self.search_tool == "search_memories":
            arguments = {"query": query, "user_id": self.user_id, "cube_ids": self.channel}
        else:
            arguments = {
                "query": query,
                "limit": result_limit,
                "user_id": self.user_id,
                "channel": self.channel,
                "metadata": {
                    "agent_code": str(agent_code or "").strip(),
                    "symbol": str(symbol or "").strip().upper(),
                    "event_tags": normalized_tags,
                },
            }
        payload = self._call_tool(self.search_tool, arguments)
        if self._payload_has_error(payload):
            return []
        memories = self._extract_memories(payload)
        return [self._normalize_memory_item(item, agent_code=agent_code, symbol=symbol) for item in memories][:result_limit]

    def record_usage(self, *, trace_id: str, symbol: str, memory_ids: list[int | str]) -> None:
        return None

    def create_memory(self, memory: dict[str, Any]) -> dict[str, Any]:
        if not self.write_enabled or not self._has_backend():
            return {}
        sanitized = self._sanitize_memory(memory)
        message = self._memory_message(sanitized)
        if self.add_tool == "add_memory":
            arguments = {"memory_content": message, "user_id": self.user_id, "cube_id": self.channel}
        else:
            arguments = {
                "message": message,
                "user_id": self.user_id,
                "channel": self.channel,
                "metadata": sanitized,
            }
        payload = self._call_tool(self.add_tool, arguments)
        if self._payload_has_error(payload):
            return {}
        memory_id = self._extract_created_id(payload)
        if not memory_id:
            memory_id = sanitized.get("memory_key") or sanitized.get("source_trace_id")
        if not memory_id:
            return {}
        return {"id": memory_id, **sanitized}

    def _sanitize_memory(self, memory: dict[str, Any]) -> dict[str, Any]:
        allowed_keys = {
            "memory_key",
            "agent_code",
            "symbol",
            "memory_type",
            "market_regime",
            "event_tags",
            "direction",
            "action",
            "lesson_text",
            "evidence_json",
            "outcome_json",
            "quality_score",
            "confidence",
            "source_trace_id",
            "created_at",
        }
        return {key: value for key, value in dict(memory or {}).items() if key in allowed_keys}

    def _memory_message(self, memory: dict[str, Any]) -> str:
        lesson = str(memory.get("lesson_text") or "").strip()
        symbol = str(memory.get("symbol") or "").strip().upper()
        agent_code = str(memory.get("agent_code") or "").strip()
        tags = ", ".join(str(tag).strip() for tag in (memory.get("event_tags") or []) if str(tag).strip())
        parts = [
            part
            for part in [
                f"symbol={symbol}" if symbol else "",
                f"agent={agent_code}" if agent_code else "",
                lesson,
                f"tags={tags}" if tags else "",
            ]
            if part
        ]
        return " | ".join(parts)

    def _extract_memories(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        candidates: list[Any] = []
        for container in (payload, payload.get("result") if isinstance(payload, dict) else None):
            if not isinstance(container, dict):
                continue
            self._collect_memory_candidates(container, candidates)
            content = container.get("content")
            if isinstance(content, list):
                for content_item in content:
                    if not isinstance(content_item, dict):
                        continue
                    parsed = self._parse_text_json(content_item.get("text"))
                    if isinstance(parsed, dict):
                        self._collect_memory_candidates(parsed, candidates)
                    elif isinstance(parsed, list):
                        candidates.extend(parsed)
        return [dict(item) for item in candidates if isinstance(item, dict)]

    def _collect_memory_candidates(self, container: dict[str, Any], candidates: list[Any]) -> None:
        for key in ("memories", "memory", "data", "items", "results"):
            value = container.get(key)
            if isinstance(value, list):
                candidates.extend(value)
            elif isinstance(value, dict):
                candidates.append(value)
        for key in ("text_mem", "act_mem", "para_mem", "pref_mem", "tool_mem", "skill_mem"):
            groups = container.get(key)
            if not isinstance(groups, list):
                continue
            for group in groups:
                if not isinstance(group, dict):
                    continue
                memories = group.get("memories")
                if isinstance(memories, list):
                    candidates.extend(memories)
                elif isinstance(memories, dict):
                    candidates.append(memories)

    def _parse_text_json(self, value: Any) -> Any:
        text = str(value or "").strip()
        if not text:
            return None
        try:
            return json.loads(text)
        except (TypeError, ValueError):
            return {"memory": text}

    def _normalize_memory_item(self, item: dict[str, Any], *, agent_code: str, symbol: str) -> dict[str, Any]:
        metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        lesson = item.get("lesson_text") or item.get("lessonText") or item.get("memory") or item.get("content") or item.get("text") or ""
        quality_score = item.get("quality_score") or item.get("qualityScore") or item.get("score") or item.get("similarity") or 0.0
        confidence = item.get("confidence") or quality_score or 0.0
        return {
            "id": item.get("id") or item.get("memory_id") or item.get("memoryId") or item.get("memory_key") or item.get("memoryKey"),
            "agent_code": metadata.get("agent_code") or item.get("agent_code") or item.get("agentCode") or str(agent_code or ""),
            "symbol": metadata.get("symbol") or item.get("symbol") or str(symbol or "").strip().upper(),
            "memory_type": metadata.get("memory_type") or item.get("memory_type") or item.get("memoryType") or "mcp_lesson",
            "market_regime": metadata.get("market_regime") or item.get("market_regime") or item.get("marketRegime") or "",
            "event_tags": metadata.get("event_tags") or item.get("event_tags") or item.get("eventTags") or [],
            "direction": metadata.get("direction") or item.get("direction") or "",
            "action": metadata.get("action") or item.get("action") or "",
            "lesson_text": str(lesson or "").strip(),
            "evidence_json": metadata.get("evidence_json") or item.get("evidence_json") or item.get("evidenceJson") or {},
            "outcome_json": metadata.get("outcome_json") or item.get("outcome_json") or item.get("outcomeJson") or {},
            "quality_score": float(quality_score or 0.0),
            "confidence": float(confidence or 0.0),
            "source_trace_id": metadata.get("source_trace_id") or item.get("source_trace_id") or item.get("sourceTraceId") or "",
            "created_at": item.get("created_at") or item.get("createdAt") or "",
        }

    def _payload_has_error(self, payload: dict[str, Any]) -> bool:
        if not isinstance(payload, dict):
            return False
        if payload.get("error"):
            return True
        result = payload.get("result")
        if not isinstance(result, dict):
            return False
        if result.get("isError"):
            return True
        content = result.get("content")
        if not isinstance(content, list):
            return False
        for item in content:
            if not isinstance(item, dict):
                continue
            text = str(item.get("text") or "").strip().lower()
            if text.startswith("error:") or text.startswith("failed:"):
                return True
        return False

    def _extract_created_id(self, payload: dict[str, Any]) -> Any:
        for container in (
            payload,
            payload.get("result") if isinstance(payload, dict) else None,
            payload.get("data") if isinstance(payload, dict) else None,
        ):
            if not isinstance(container, dict):
                continue
            for key in ("memory_id", "memoryId", "id", "message_id", "messageId"):
                if container.get(key) not in (None, ""):
                    return container.get(key)
        return None


class HybridLongTermMemoryStore:
    """Primary local memory store with best-effort secondary MCP memory."""

    def __init__(self, *, primary: Any, secondary: Any | None = None):
        self.primary = primary
        self.secondary = secondary

    def search(
        self,
        *,
        agent_code: str,
        symbol: str,
        tags: list[str],
        limit: int,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        rows.extend(self._safe_search(self.primary, agent_code=agent_code, symbol=symbol, tags=tags, limit=limit))
        rows.extend(self._safe_search(self.secondary, agent_code=agent_code, symbol=symbol, tags=tags, limit=limit))
        deduped: list[dict[str, Any]] = []
        seen: set[str] = set()
        for row in rows:
            key = str(
                row.get("id")
                or row.get("memory_key")
                or row.get("memoryKey")
                or row.get("lesson_text")
                or row.get("lessonText")
                or ""
            )
            if key and key in seen:
                continue
            if key:
                seen.add(key)
            deduped.append(dict(row))
        deduped.sort(key=lambda item: float(item.get("quality_score") or item.get("qualityScore") or 0.0), reverse=True)
        return deduped[: max(0, int(limit or 0))]

    def record_usage(self, *, trace_id: str, symbol: str, memory_ids: list[int | str]) -> None:
        for store in (self.primary, self.secondary):
            if store is None:
                continue
            try:
                store.record_usage(trace_id=trace_id, symbol=symbol, memory_ids=memory_ids)
            except Exception as exc:
                logger.debug("memory usage recording failed for %s: %s", store.__class__.__name__, exc)
        return None

    def create_memory(self, memory: dict[str, Any]) -> dict[str, Any]:
        created: dict[str, Any] = {}
        if self.primary is not None:
            created = self.primary.create_memory(memory)
        if self.secondary is not None:
            try:
                self.secondary.create_memory(memory)
            except Exception as exc:
                logger.warning("secondary memory store create failed: %s", exc)
        return created if isinstance(created, dict) else {}

    def _safe_search(self, store: Any, *, agent_code: str, symbol: str, tags: list[str], limit: int) -> list[dict[str, Any]]:
        if store is None:
            return []
        try:
            rows = store.search(agent_code=agent_code, symbol=symbol, tags=tags, limit=limit)
        except Exception as exc:
            logger.warning("memory store search failed for %s: %s", store.__class__.__name__, exc)
            return []
        return [dict(row) for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []
