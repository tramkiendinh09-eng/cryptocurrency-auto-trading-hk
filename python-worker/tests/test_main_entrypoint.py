import main as worker_main


def test_main_defaults_to_trade_runtime_profile(monkeypatch):
    captured = {}

    def fake_runtime_main(env=None):
        captured["runtime_env"] = env
        return {"profile": "trade_runtime"}

    monkeypatch.delenv("WORKER_PROFILE", raising=False)
    monkeypatch.setattr("trade_runtime.app.main", fake_runtime_main)

    result = worker_main.main()

    assert captured["runtime_env"] is None
    assert result["profile"] == "trade_runtime"


def test_main_dispatches_trade_runtime_profile(monkeypatch):
    captured = {}

    def fake_runtime_main(env=None):
        captured["env"] = env
        return {"profile": "trade_runtime"}

    monkeypatch.setenv("WORKER_PROFILE", "trade_runtime")
    monkeypatch.setattr("trade_runtime.app.main", fake_runtime_main)

    result = worker_main.main()

    assert captured["env"] is None
    assert result["profile"] == "trade_runtime"


def test_main_forces_trade_runtime_even_when_legacy_profile_requested(monkeypatch):
    captured = {}

    def fake_runtime_main(env=None):
        captured["runtime_env"] = env
        return {"profile": "trade_runtime"}

    monkeypatch.setenv("WORKER_PROFILE", "legacy")
    monkeypatch.setattr("trade_runtime.app.main", fake_runtime_main)

    result = worker_main.main()

    assert captured["runtime_env"] is None
    assert result["profile"] == "trade_runtime"
