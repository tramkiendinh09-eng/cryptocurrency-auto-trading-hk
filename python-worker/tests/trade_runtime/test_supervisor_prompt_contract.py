"""指令段与模板路径的契约测试。

这套系统反复出现同一种故障：某个参数从提示词里消失了，而调用照样成功、
决策照样产出，只是产出的东西是模型猜的。切模板路径把这个风险放大一倍——
内联与模板是两条独立的组装链路，任何一条掉了东西都不会报错。

所以这里钉三样：
1. 输出契约里每一条下游会读的数值约定都还在（压缩措辞不等于可以丢约定）；
2. 两个常量里没有字面花括号（渲染器的正则会把它们连同内容一起吃掉）；
3. 模板渲染上下文带得出 sizing_constraints，且与内联用的是同一份实现。
"""

import json

import pytest

from trade_runtime.decision.nodes.supervisor_agent import (
    _build_supervisor_prompt,
    _sizing_constraints,
)
from trade_runtime.decision.sizing import sizing_constraints
from trade_runtime.prompting.render_context_builder import build_supervisor_render_context
from trade_runtime.prompting.renderers import render_template_content
from trade_runtime.prompting.supervisor_template import (
    SUPERVISOR_EMPTY_MEMORY_NOTE,
    SUPERVISOR_METHODOLOGY,
    SUPERVISOR_OUTPUT_CONTRACT,
    SUPERVISOR_TEMPLATE_CODE,
    supervisor_template_content,
    supervisor_template_placeholders,
)


def _state():
    return {
        "symbol": "ETHUSDT",
        "exchange": "binance",
        "mode": "paper",
        "account_equity": 100.0,
        "feature_snapshot": {
            "effective_price": 2400.0,
            "wyckoff_shortterm": {
                "trade_readiness": "ready",
                "entry_bias": "bullish",
                "config": {"maxReadyExtensionPct": 0.9, "requireRetestForReady": True},
            },
        },
        "runtime_config": {"max_position_ratio": 0.8, "maxLeverage": 12},
        "strategy_context": {
            "strategy_key": "major-crypto",
            "news_api_config": {"api_url": "http://x"},
            "onchain_api_config": {"api_url": "http://y"},
            "social_api_config": {"api_url": "http://z"},
            "market_data_config": {"collect_onchain": True},
            "market_api_config": {
                "api_url": "https://fapi.binance.com",
                "ws_base_url": "wss://fstream.binance.com",
                "ws_ping_interval_seconds": 20,
                "doc_reference_url": "https://binance-docs.github.io",
            },
        },
    }


class TestOutputContractKeepsEveryDownstreamConvention:
    """措辞可以压缩，约定不能丢。每一条都对应下游一个真实的读取点。"""

    @pytest.mark.parametrize(
        "fragment",
        [
            # JSON 形状：解析器按键名取值
            "action, side, confidence, size_hint, leverage_hint, holding_window, invalidation, summary_reason",
            # action 枚举：执行层按它分支
            "OPEN_LONG, OPEN_SHORT, ADD_LONG, ADD_SHORT, REDUCE, CLOSE, HOLD, SKIP",
            "no_action",
            "no_trade_condition",
            # 字段取值范围
            "side is one of long, short, flat",
            "confidence is an integer from 0 to 100",
            "holding_window is a concrete duration",
            # 仓位口径：改一个字都会让风控和下单算出不同的敞口
            "account_equity * size_hint * leverage_hint",
            "sizing_constraints.min_size_hint and max_size_hint",
            "cap margin and not exposure",
            "min_viable_size_hint",
            "min_viable_size_hint_at_max_leverage",
            "min_order_notional_usdt",
            "notional_step_usdt",
            "any_size_tradeable",
            "sizing_constraints.min_leverage and max_leverage",
            "default_leverage",
            # 证据来源：这段是专门为"模型拿 24h 累计量当成 K 线量"加的
            "kline_context.period_summaries",
            "quote_volume_ratio",
            "Ticker 24h cumulative volume is not bar volume confirmation",
            # 持仓管理：不加严，但也不能悄悄消失
            "avoid frequent ADD_LONG, ADD_SHORT, REDUCE or CLOSE",
            "prefer HOLD",
            "the referee review is advisory",
        ],
    )
    def test_fragment_survives_the_rewrite(self, fragment):
        assert fragment in SUPERVISOR_OUTPUT_CONTRACT

    def test_contract_does_not_invent_a_confidence_threshold(self):
        """交接稿给"已有持仓时再开仓"加了 confidence>=70。那是新增约定，
        不是压缩措辞——没有任何回测支持这个数字，不能写死进去。"""
        assert "70" not in SUPERVISOR_OUTPUT_CONTRACT


class TestPriorityRuleIsPresent:
    """复盘里 5 笔入场每一笔都是"看见 RSI 高就把仓位减半"。"""

    def test_reduced_size_is_redirected_to_skip(self):
        text = SUPERVISOR_METHODOLOGY.lower()
        assert "reduced size because" in text
        for token in ("rsi", "overbought", "extended", "chasing", "empty memory"):
            assert token in text
        assert "skip" in text

    def test_no_half_conviction_size(self):
        assert "half-conviction size" in SUPERVISOR_METHODOLOGY

    def test_gates_that_lack_data_are_not_baked_in(self):
        """位置分位、regime、风险收益比三条都还没有数据支撑，不该进提示词。

        30 天 163 个 ready 信号分桶显示 24h 高分位桶是第二好的（+0.617%），
        与"高位不开多"相反；RR 阈值从未量化过。写进去等于把没验证的假设
        固化成教条。
        """
        combined = (SUPERVISOR_METHODOLOGY + SUPERVISOR_OUTPUT_CONTRACT).lower()
        assert "range_position_pct_24h" not in combined
        assert "reward_pct" not in combined
        assert "regime" not in combined


class TestEmptyMemoryNoteNoLongerAsksForSmallerSize:
    def test_it_forbids_shrinking_instead_of_recommending_it(self):
        text = SUPERVISOR_EMPTY_MEMORY_NOTE.lower()
        assert "do not compensate by shrinking size or confidence" in text
        assert "skip on any ambiguity" in text

    def test_it_is_attached_only_when_memory_is_empty(self):
        with_memory = _build_supervisor_prompt(
            {**_state(), "long_term_memory": {"items": [{"lesson": "x"}]}}, {}
        )
        without_memory = _build_supervisor_prompt(_state(), {})
        assert SUPERVISOR_EMPTY_MEMORY_NOTE.strip() in without_memory
        assert SUPERVISOR_EMPTY_MEMORY_NOTE.strip() not in with_memory


class TestTemplateSafety:
    r"""渲染器的正则是 \{([^}]+)\}：正文里任何字面花括号都会被替换成空串。"""

    @pytest.mark.parametrize(
        "name,text",
        [
            ("methodology", SUPERVISOR_METHODOLOGY),
            ("contract", SUPERVISOR_OUTPUT_CONTRACT),
            ("empty_memory_note", SUPERVISOR_EMPTY_MEMORY_NOTE),
        ],
    )
    def test_no_literal_braces(self, name, text):
        assert "{" not in text and "}" not in text

    def test_text_survives_the_real_renderer_unchanged(self):
        combined = SUPERVISOR_METHODOLOGY + "\n\n" + SUPERVISOR_OUTPUT_CONTRACT
        assert render_template_content(combined, {}) == combined


class TestRenderContextCarriesSizingConstraints:
    """模板路径此前没有这一段，切过去会整段丢失。"""

    def test_sizing_constraints_json_is_present_and_not_empty(self):
        context = build_supervisor_render_context(_state())
        assert "sizing_constraints_json" in context
        payload = json.loads(context["sizing_constraints_json"])
        assert payload["max_size_hint"] == 0.8
        assert payload["min_leverage"] >= 1
        assert payload["min_order_notional_usdt"] > 0

    def test_it_is_the_same_implementation_as_the_inline_prompt(self):
        state = _state()
        from_context = json.loads(build_supervisor_render_context(state)["sizing_constraints_json"])
        inline = _sizing_constraints(state, state["runtime_config"])
        shared = sizing_constraints(state, state["runtime_config"])
        assert from_context == json.loads(json.dumps(inline, sort_keys=True))
        assert inline == shared

    def test_rendering_the_placeholder_does_not_produce_an_empty_string(self):
        context = build_supervisor_render_context(_state())
        rendered = render_template_content("sizing_constraints: {sizing_constraints_json}", context)
        assert rendered != "sizing_constraints: "
        assert "max_size_hint" in rendered


class TestPromptNoiseIsPruned:
    """约占提示词 10%，下游解析器、风控、trigger_policy 都不读。"""

    def test_inline_prompt_drops_detector_and_transport_internals(self):
        prompt = _build_supervisor_prompt(_state(), {})
        assert "maxReadyExtensionPct" not in prompt
        assert "ws_ping_interval_seconds" not in prompt
        assert "doc_reference_url" not in prompt
        assert "news_api_config" not in prompt
        assert "onchain_api_config" not in prompt
        assert "social_api_config" not in prompt
        assert "market_data_config" not in prompt

    def test_template_path_drops_the_same_things(self):
        context = build_supervisor_render_context(_state())
        blob = context["market_context_json"] + context["strategy_context_json"]
        assert "maxReadyExtensionPct" not in blob
        assert "ws_ping_interval_seconds" not in blob
        assert "doc_reference_url" not in blob
        assert "news_api_config" not in blob
        assert "market_data_config" not in blob

    def test_the_signal_itself_is_kept(self):
        """删的是阈值，不是判定。模型仍然要看到 trade_readiness。"""
        prompt = _build_supervisor_prompt(_state(), {})
        assert "trade_readiness" in prompt
        assert "market_api_config" in prompt  # 整块保留，只剪掉传输层调参

class TestTemplateBodyMatchesTheRenderContext:
    """占位符写错一个键名不会报错，只会让那一段内容凭空消失。

    这正是这套系统反复出现的故障形态：调用成功、决策产出，只是产出的东西
    是模型猜的。所以逐个核对，而不是"渲染没抛异常就算过"。
    """

    def test_every_placeholder_exists_in_the_render_context(self):
        context = build_supervisor_render_context(_state())
        missing = [name for name in supervisor_template_placeholders() if name not in context]
        assert missing == []

    def test_template_body_carries_the_same_instruction_text_as_the_inline_prompt(self):
        content = supervisor_template_content()
        assert SUPERVISOR_METHODOLOGY in content
        assert SUPERVISOR_OUTPUT_CONTRACT in content

    def test_rendered_template_has_no_leftover_placeholders(self):
        import re

        rendered = render_template_content(supervisor_template_content(), build_supervisor_render_context(_state()))
        # 残留的 {name} 说明模板正文里写了一个渲染上下文没有的键。
        leftovers = re.findall(r"\{([a-z_]+)\}", rendered)
        assert leftovers == []

    def test_sizing_block_is_not_rendered_empty(self):
        """README 标注的第二个坑：模板路径丢掉仓位约束。"""
        rendered = render_template_content(supervisor_template_content(), build_supervisor_render_context(_state()))
        marker = "sizing_constraints: "
        start = rendered.index(marker) + len(marker)
        line = rendered[start:rendered.index("\n", start)]
        assert line.strip(), "sizing_constraints 渲染成了空串"
        assert "max_size_hint" in line

    def test_template_code_is_stable(self):
        assert SUPERVISOR_TEMPLATE_CODE == "SUPERVISOR_ENTRY_DISCIPLINE_V1"
