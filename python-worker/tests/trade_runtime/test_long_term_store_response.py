"""HttpLongTermMemoryStore 对后端响应的解读。

线上事故：add 端点漏标 @Anonymous，每一次记忆写入都被拒，而
`agent_memory` 表从部署起一行都没有——却没人看得出来。原因是两层掩盖：
RuoYi 认证失败返回 **HTTP 200**（401 装在 body 的 code 里），
`raise_for_status()` 不抛；这里再静静 return {}，上层只报一句笼统的
`memory_store_create_failed`。
"""
from __future__ import annotations

import pytest

from trade_runtime.memory.long_term import HttpLongTermMemoryStore

MEMORY = {"memory_key": "k", "agent_code": "market", "symbol": "SOLUSDT",
          "memory_type": "lesson", "lesson_text": "x"}


class _Response:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


@pytest.fixture
def store(monkeypatch):
    s = HttpLongTermMemoryStore(base_url="http://backend", bearer_token="t")

    def _post(payload):
        monkeypatch.setattr(
            "trade_runtime.memory.long_term.requests.post",
            lambda *a, **k: _Response(payload),
        )
    return s, _post


def test_toajax_success_without_data_is_not_a_failure(store):
    """RuoYi 的 toAjax() 成功时只返回 {code,msg}，不带 data。

    按 data 判成败会把成功的写入报成失败。
    """
    s, post = store
    post({"msg": "操作成功", "code": 200})
    assert s.create_memory(MEMORY) != {}, "toAjax 成功不带 data，不该判成失败"


def test_auth_failure_disguised_as_http_200_is_reported(store, caplog):
    """认证失败走的是 HTTP 200 + body code=401，必须判出来并记下 code。"""
    s, post = store
    post({"msg": "请求访问：/dca/agent-memory，认证失败，无法访问系统资源", "code": 401})
    with caplog.at_level("ERROR"):
        assert s.create_memory(MEMORY) == {}
    assert "401" in caplog.text, "鉴权失败必须在日志里留下 code，不能只报通用失败"


def test_explicit_data_object_still_wins(store):
    """后端若返回了完整对象，仍以它为准。"""
    s, post = store
    post({"code": 200, "data": {"id": 7, "lesson_text": "from backend"}})
    assert s.create_memory(MEMORY)["id"] == 7


def test_insert_row_count_still_accepted(store):
    """有的端点返回受影响行数。"""
    s, post = store
    post({"code": 200, "data": 1})
    assert s.create_memory(MEMORY) != {}
