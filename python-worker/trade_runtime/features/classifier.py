from trade_runtime.trigger_policy import classify_event_strength_from_policy


class EventStrengthClassifier:
    def classify(
        self,
        *,
        price_change_pct: float,
        liquidation_notional: float,
        news_score: float,
        social_score: float = 0.0,
        onchain_flow_bias: float = 0.0,
        runtime_config: dict | None = None,
        strategy_context: dict | None = None,
    ) -> str:
        event_bundle = []
        if liquidation_notional > 0:
            event_bundle.append(
                {
                    "event_type": "liquidation",
                    "symbol": "LEGACY",
                    "exchange": "legacy",
                    "notionalUsd": liquidation_notional,
                    "side": "BUY" if price_change_pct > 0 else "SELL",
                }
            )
        return classify_event_strength_from_policy(
            event_bundle=event_bundle,
            feature_snapshot={
                "symbol": "LEGACY",
                "price_change_pct": price_change_pct,
                "news_score": news_score,
                "social_score": social_score,
                "onchain_flow_bias": onchain_flow_bias,
            },
            runtime_config=runtime_config,
            strategy_context=strategy_context,
        )
