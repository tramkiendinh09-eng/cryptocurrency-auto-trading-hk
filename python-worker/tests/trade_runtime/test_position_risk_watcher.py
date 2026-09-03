from datetime import datetime, timezone

from trade_runtime.position_risk_watcher import PositionRiskWatcher, evaluate_position_risk


def test_position_risk_watcher_ignores_flat_account():
    result = evaluate_position_risk(
        account_context={"current_position_side": "flat", "current_position_quantity": 0},
        feature_snapshot={"effective_price": 100.0},
        event_bundle=[],
        runtime_config={},
        strategy_context={},
        now=datetime(2026, 5, 8, 8, 0, tzinfo=timezone.utc),
    )

    assert result["triggered"] is False
    assert result["has_position"] is False


def test_position_risk_watcher_triggers_review_on_long_adverse_move():
    result = evaluate_position_risk(
        account_context={"current_position_side": "long", "current_position_quantity": 1.5, "entry_price": 100.0},
        feature_snapshot={"effective_price": 99.4, "effective_price_source": "mark_price"},
        event_bundle=[],
        runtime_config={"runtime_flags_json": "{\"positionRiskWatcher\":{\"reviewAdverseMovePct\":0.5}}"},
        strategy_context={},
        now=datetime(2026, 5, 8, 8, 0, tzinfo=timezone.utc),
    )

    assert result["triggered"] is True
    assert result["severity"] == "review"
    assert result["action"] == "REVIEW"
    assert result["position_risk_context"]["current_price"] == 99.4
    assert result["position_risk_event"]["event_type"] == "position_risk"
    # review 只越过噪声冷却，不抢占 LLM 预算——见下面那一组测试
    assert result["bypass_trigger_guards"] is False
    assert result["bypass_dispatch_cooldown"] is True


def test_position_risk_watcher_uses_effective_price_when_trade_tick_is_stale():
    result = evaluate_position_risk(
        account_context={"current_position_side": "long", "current_position_quantity": 1.0, "entry_price": 100.0},
        feature_snapshot={
            "latest_trade_price": 100.0,
            "effective_price": 98.8,
            "effective_price_source": "mark_price",
            "market_tick_staleness_seconds": 600.0,
        },
        event_bundle=[{"event_type": "market_tick", "price": 100.0}],
        runtime_config={"runtime_flags_json": "{\"positionRiskWatcher\":{\"reviewAdverseMovePct\":0.5}}"},
        strategy_context={},
        now=datetime(2026, 5, 8, 8, 0, tzinfo=timezone.utc),
    )

    assert result["triggered"] is True
    assert result["position_risk_context"]["current_price"] == 98.8
    assert result["position_risk_context"]["price_source"] == "mark_price"
    assert result["position_risk_context"]["trade_tick_stale"] is True


def test_position_risk_watcher_escalates_to_hard_close_only_when_enabled():
    disabled = evaluate_position_risk(
        account_context={"current_position_side": "short", "current_position_quantity": 2.0, "entry_price": 100.0},
        feature_snapshot={"effective_price": 102.0},
        event_bundle=[],
        runtime_config={"runtime_flags_json": "{\"positionRiskWatcher\":{\"closeAdverseMovePct\":1.0,\"hardCloseEnabled\":false}}"},
        strategy_context={},
        now=datetime(2026, 5, 8, 8, 0, tzinfo=timezone.utc),
    )
    enabled = evaluate_position_risk(
        account_context={"current_position_side": "short", "current_position_quantity": 2.0, "entry_price": 100.0},
        feature_snapshot={"effective_price": 102.0},
        event_bundle=[],
        runtime_config={"runtime_flags_json": "{\"positionRiskWatcher\":{\"closeAdverseMovePct\":1.0,\"hardCloseEnabled\":true}}"},
        strategy_context={},
        now=datetime(2026, 5, 8, 8, 0, tzinfo=timezone.utc),
    )

    assert disabled["severity"] == "close"
    assert disabled["action"] == "REVIEW"
    assert enabled["severity"] == "close"
    assert enabled["action"] == "CLOSE"


def test_position_risk_watcher_cooldown_suppresses_duplicate_triggers():
    watcher = PositionRiskWatcher()
    runtime_config = {"runtime_flags_json": "{\"positionRiskWatcher\":{\"reviewAdverseMovePct\":0.5,\"cooldownSeconds\":60}}"}

    first = watcher.evaluate(
        account_context={"current_position_side": "long", "current_position_quantity": 1.0, "entry_price": 100.0},
        feature_snapshot={"effective_price": 99.0},
        event_bundle=[],
        runtime_config=runtime_config,
        strategy_context={},
        now=datetime(2026, 5, 8, 8, 0, tzinfo=timezone.utc),
    )
    second = watcher.evaluate(
        account_context={"current_position_side": "long", "current_position_quantity": 1.0, "entry_price": 100.0},
        feature_snapshot={"effective_price": 98.9},
        event_bundle=[],
        runtime_config=runtime_config,
        strategy_context={},
        now=datetime(2026, 5, 8, 8, 0, 30, tzinfo=timezone.utc),
    )

    assert first["triggered"] is True
    assert second["triggered"] is False
    assert second["suppressed_by_cooldown"] is True


def test_position_risk_watcher_triggers_on_profit_giveback():
    result = evaluate_position_risk(
        account_context={
            "current_position_side": "long",
            "current_position_quantity": 1.0,
            "entry_price": 100.0,
            "peak_unrealized_pnl_pct": 1.2,
        },
        feature_snapshot={"effective_price": 100.6},
        event_bundle=[],
        runtime_config={"runtime_flags_json": "{\"positionRiskWatcher\":{\"profitGivebackPct\":0.4}}"},
        strategy_context={},
        now=datetime(2026, 5, 8, 8, 0, tzinfo=timezone.utc),
    )

    assert result["triggered"] is True
    assert result["reason"] == "profit_giveback"
    assert result["position_risk_context"]["profit_giveback_pct"] == 0.6


def _watch(watcher, price, now, flags, entry=100.0):
    return watcher.evaluate(
        account_context={"current_position_side": "long", "current_position_quantity": 1.0, "entry_price": entry},
        feature_snapshot={"effective_price": price},
        event_bundle=[],
        runtime_config={"runtime_flags_json": flags},
        strategy_context={},
        now=now,
    )


def _at(second, minute=0):
    return datetime(2026, 5, 8, 8, minute, second, tzinfo=timezone.utc)


class TestOnlyUrgentSeveritiesPreemptTheLlmBudget:
    """review 级此前也在绕过 LLM 预算，于是一笔浮亏持仓可以无上限地把预算
    吃光：线上实测 position_risk 占了全部 LLM 派发的六成，把中转网关打到
    503，连带把真正紧急的那次问询一起打掉。风控要能抢占预算，但看一眼这
    一级不该有这个特权。
    """

    FLAGS = '{"positionRiskWatcher":{"reviewAdverseMovePct":0.3,"reduceAdverseMovePct":0.7,"closeAdverseMovePct":1.2}}'

    def _severity(self, price):
        return evaluate_position_risk(
            account_context={"current_position_side": "long", "current_position_quantity": 1.0, "entry_price": 100.0},
            feature_snapshot={"effective_price": price},
            event_bundle=[],
            runtime_config={"runtime_flags_json": self.FLAGS},
            strategy_context={},
            now=_at(0),
        )

    def test_review_does_not_preempt_the_budget(self):
        result = self._severity(99.5)
        assert result["severity"] == "review"
        assert result["bypass_trigger_guards"] is False

    def test_reduce_and_close_do_preempt_the_budget(self):
        reduce = self._severity(99.2)
        close = self._severity(98.5)
        assert reduce["severity"] == "reduce"
        assert close["severity"] == "close"
        assert reduce["bypass_trigger_guards"] is True
        assert close["bypass_trigger_guards"] is True

    def test_every_severity_still_bypasses_the_noise_cooldown(self):
        """派发冷却是按同标的同方向同来源设的噪声闸门，持仓风险与它无关。"""
        for price in (99.5, 99.2, 98.5):
            assert self._severity(price)["bypass_dispatch_cooldown"] is True


class TestSeverityTieredCooldown:
    """三级共用一个 30 秒冷却时，浮亏刚过 review 线的持仓每 30 秒就把同一个
    问题重问一遍。review 是看一眼，close 才是要动手，冷却时长应当分开。
    """

    FLAGS = (
        '{"positionRiskWatcher":{"reviewAdverseMovePct":0.3,"reduceAdverseMovePct":0.7,'
        '"closeAdverseMovePct":1.2,"cooldownSecondsBySeverity":{"review":900,"reduce":300,"close":60},'
        '"rearmDeltaPct":0}}'
    )

    def test_review_is_silenced_far_longer_than_close(self):
        watcher = PositionRiskWatcher()
        assert _watch(watcher, 99.5, _at(0), self.FLAGS)["triggered"] is True
        # 5 分钟后仍在 review 的 900 秒冷却内
        assert _watch(watcher, 99.5, _at(0, 5), self.FLAGS)["triggered"] is False
        # 16 分钟后冷却过了
        assert _watch(watcher, 99.5, _at(0, 16), self.FLAGS)["triggered"] is True

    def test_close_rearms_quickly(self):
        watcher = PositionRiskWatcher()
        assert _watch(watcher, 98.5, _at(0), self.FLAGS)["triggered"] is True
        assert _watch(watcher, 98.5, _at(30), self.FLAGS)["triggered"] is False
        assert _watch(watcher, 98.5, _at(0, 2), self.FLAGS)["triggered"] is True

    def test_escalation_is_never_delayed_by_cooldown(self):
        """严重级升高是新信息，任何时候都该立刻放行。"""
        watcher = PositionRiskWatcher()
        assert _watch(watcher, 99.5, _at(0), self.FLAGS)["severity"] == "review"
        escalated = _watch(watcher, 98.5, _at(1), self.FLAGS)
        assert escalated["severity"] == "close"
        assert escalated["triggered"] is True

    def test_a_missing_level_falls_back_to_the_flat_cooldown(self):
        flags = (
            '{"positionRiskWatcher":{"reviewAdverseMovePct":0.3,"cooldownSeconds":600,'
            '"cooldownSecondsBySeverity":{"close":60},"rearmDeltaPct":0}}'
        )
        watcher = PositionRiskWatcher()
        assert _watch(watcher, 99.5, _at(0), flags)["triggered"] is True
        assert _watch(watcher, 99.5, _at(0, 5), flags)["triggered"] is False


class TestRearmNeedsAMaterialChange:
    """冷却一到期就拿着几乎一样的数字重问，答案也几乎一定一样——线上正是
    这样对同一笔 MU 多头问了上百次，模型每次都答 HOLD。
    """

    FLAGS = (
        '{"positionRiskWatcher":{"reviewAdverseMovePct":0.3,"reduceAdverseMovePct":5,'
        '"closeAdverseMovePct":9,"cooldownSecondsBySeverity":{"review":60},"rearmDeltaPct":0.15}}'
    )

    def test_cooldown_expired_but_nothing_moved_stays_silent(self):
        watcher = PositionRiskWatcher()
        assert _watch(watcher, 99.5, _at(0), self.FLAGS)["triggered"] is True
        # 冷却已过，但浮亏从 0.50% 只走到 0.55%
        second = _watch(watcher, 99.45, _at(0, 2), self.FLAGS)
        assert second["triggered"] is False
        assert second["suppressed_by_cooldown"] is True

    def test_a_real_move_rearms(self):
        watcher = PositionRiskWatcher()
        assert _watch(watcher, 99.5, _at(0), self.FLAGS)["triggered"] is True
        # 浮亏从 0.50% 走到 0.80%，超过 0.15 个百分点
        assert _watch(watcher, 99.2, _at(0, 2), self.FLAGS)["triggered"] is True

    def test_a_move_inside_the_cooldown_still_waits(self):
        """两条是与的关系：变化够大也要等冷却过。"""
        watcher = PositionRiskWatcher()
        assert _watch(watcher, 99.5, _at(0), self.FLAGS)["triggered"] is True
        assert _watch(watcher, 99.2, _at(10), self.FLAGS)["triggered"] is False

    def test_structure_reversal_is_not_silenced_forever(self):
        """结构反转是个布尔判定，值恒为 1.0；拿它去比差值会让这一级在第一次
        派发之后被永久静音。变化门槛只适用于连续量。
        """
        flags = (
            '{"positionRiskWatcher":{"reviewAdverseMovePct":9,"reduceAdverseMovePct":9,'
            '"closeAdverseMovePct":9,"profitGivebackPct":9,'
            '"cooldownSecondsBySeverity":{"review":60},"rearmDeltaPct":0.15}}'
        )
        watcher = PositionRiskWatcher()
        snapshot = {
            "effective_price": 100.0,
            "wyckoff_shortterm": {"trade_readiness": "ready", "entry_bias": "bearish"},
        }

        def run(now):
            return watcher.evaluate(
                account_context={
                    "current_position_side": "long",
                    "current_position_quantity": 1.0,
                    "entry_price": 100.0,
                },
                feature_snapshot=snapshot,
                event_bundle=[],
                runtime_config={"runtime_flags_json": flags},
                strategy_context={},
                now=now,
            )

        first = run(_at(0))
        assert first["reason"] == "structure_reversal"
        assert first["triggered"] is True
        assert run(_at(30))["triggered"] is False
        assert run(_at(0, 2))["triggered"] is True
