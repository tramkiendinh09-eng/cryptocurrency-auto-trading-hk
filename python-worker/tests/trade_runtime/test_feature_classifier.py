from trade_runtime.features.classifier import EventStrengthClassifier


def test_classifier_marks_extreme_move_as_strong():
    classifier = EventStrengthClassifier()

    level = classifier.classify(price_change_pct=6.8, liquidation_notional=12_000_000, news_score=0)

    assert level == "strong"


def test_classifier_marks_high_news_score_as_normal():
    classifier = EventStrengthClassifier()

    level = classifier.classify(price_change_pct=0.4, liquidation_notional=0, news_score=0.7)

    assert level == "normal"


def test_classifier_marks_social_and_onchain_extremes_as_strong():
    classifier = EventStrengthClassifier()

    level = classifier.classify(
        price_change_pct=0.2,
        liquidation_notional=0,
        news_score=0.0,
        social_score=0.95,
        onchain_flow_bias=0.0,
    )

    assert level == "strong"


def test_classifier_uses_policy_default_market_rule_only_threshold_for_normal():
    classifier = EventStrengthClassifier()

    level = classifier.classify(
        price_change_pct=1.2,
        liquidation_notional=0,
        news_score=0.0,
        social_score=0.0,
        onchain_flow_bias=0.0,
    )

    assert level == "normal"
