from feed_adapter.providers.social import RedditSocialProvider


def test_reddit_social_provider_filters_symbol_and_normalizes_score():
    reddit_payload = {
        "data": {
            "children": [
                {
                    "data": {
                        "title": "BTC breakout setup",
                        "selftext": "Bitcoin momentum discussion",
                        "author": "macro_anon",
                        "score": 920,
                        "num_comments": 180,
                        "created_utc": 1776776400,
                        "subreddit": "CryptoCurrency",
                    }
                },
                {
                    "data": {
                        "title": "Solana meme thread",
                        "selftext": "No BTC mention",
                        "author": "other_user",
                        "score": 20,
                        "num_comments": 1,
                        "created_utc": 1776776400,
                        "subreddit": "CryptoCurrency",
                    }
                },
            ]
        }
    }

    provider = RedditSocialProvider(
        listing_urls=["https://reddit.example/r/CryptoCurrency/new.json"],
        fetch_json=lambda url, timeout: reddit_payload,
    )

    items = provider.fetch("BTCUSDT")

    assert len(items) == 1
    assert items[0]["symbol"] == "BTCUSDT"
    assert items[0]["author"] == "macro_anon"
    assert items[0]["headline"] == "BTC breakout setup"
    assert items[0]["source"] == "reddit:r/CryptoCurrency"
    assert 0.8 <= items[0]["score"] <= 0.95

