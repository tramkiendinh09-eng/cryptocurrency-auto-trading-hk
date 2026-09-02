"""阈值校准的命令行入口。

    # 拉一段历史（结果落盘缓存，重跑不再打网络）
    python -m trade_runtime.calibration.cli fetch --symbol BTCUSDT --days 30

    # 看这段历史长什么样：波动分位、基准方向率
    python -m trade_runtime.calibration.cli describe --symbol BTCUSDT --days 30

    # 扫一个阈值
    python -m trade_runtime.calibration.cli sweep --symbol BTCUSDT --days 30 \
        --key markPriceDeviationPct --values 0.03,0.05,0.08,0.12 \
        --signal-type mark_price_deviation

读扫描结果前务必先看 ``describe`` 给出的 ``base_rate``：一个 0.55 的
hit_rate 在 P(up)=0.53 的窗口里几乎没有信息量。
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

from .history import load_history
from .replay import build_frames, summarize_window
from .sweep import recommend, sweep_threshold

_DEFAULT_CACHE = Path("/opt/dca/calibration-cache")


def _window_ms(days: float) -> tuple[int, int]:
    end_ms = int(time.time() // 60 * 60 * 1000)
    return end_ms - int(days * 24 * 3600 * 1000), end_ms


def _load(args) -> object:
    start_ms, end_ms = _window_ms(args.days)
    return load_history(
        args.symbol,
        start_ms=start_ms,
        end_ms=end_ms,
        cache_dir=args.cache_dir,
        refresh=getattr(args, "refresh", False),
    )


def _base_rate(bundle, horizons=(15, 60, 240)) -> dict[str, dict[str, float]]:
    """无条件持有的方向基准率。

    这是解读 hit_rate 的必要参照：趋势行情里「猜涨」本身就有超过 50% 的
    命中率，不减掉它就会把行情方向误读成信号质量。
    """
    candles = sorted(bundle.candles, key=lambda item: int(item.get("open_time") or 0))
    closes = [float(item.get("close") or 0.0) for item in candles]
    closes = [value for value in closes if value > 0]
    out: dict[str, dict[str, float]] = {}
    for horizon in horizons:
        returns = [
            (closes[i + horizon] - closes[i]) / closes[i] * 100.0
            for i in range(len(closes) - horizon)
            if closes[i] > 0
        ]
        if not returns:
            continue
        ups = sum(1 for value in returns if value > 0)
        out[f"{horizon}m"] = {
            "p_up": round(ups / len(returns), 4),
            "mean_pct": round(sum(returns) / len(returns), 4),
            "mean_abs_pct": round(sum(abs(value) for value in returns) / len(returns), 4),
            "samples": len(returns),
        }
    return out


def _cmd_fetch(args) -> int:
    bundle = _load(args)
    print(json.dumps(bundle.coverage(), ensure_ascii=False, indent=2))
    return 0


def _cmd_describe(args) -> int:
    bundle = _load(args)
    payload = {
        "coverage": bundle.coverage(),
        "window": summarize_window(bundle),
        # 解读 hit_rate 必须对照这个
        "base_rate": _base_rate(bundle),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _cmd_sweep(args) -> int:
    bundle = _load(args)
    values = [float(item) for item in str(args.values).split(",") if item.strip()]
    if not values:
        print("--values 不能为空", file=sys.stderr)
        return 2

    base_config = json.loads(args.base_config) if args.base_config else {"marketTrigger": {}}
    frames = build_frames(bundle, warmup_bars=args.warmup_bars)
    outcome = sweep_threshold(
        bundle,
        threshold_key=args.key,
        values=values,
        base_config=base_config,
        horizon_minutes=args.horizon,
        signal_type_filter=args.signal_type,
        frames=frames,
        isolate=not args.no_isolate,
    )
    payload = {
        "outcome": outcome.as_dict(),
        "recommendation": recommend(outcome),
        "base_rate": _base_rate(bundle),
        "window": summarize_window(bundle),
    }
    if args.out:
        Path(args.out).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"written to {args.out}")
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trade_runtime.calibration.cli",
        description="用历史数据校准触发阈值（判定复用生产的 trigger_policy）",
    )
    parser.add_argument("--log-level", default="INFO")
    sub = parser.add_subparsers(dest="command", required=True)

    def common(target):
        target.add_argument("--symbol", default="BTCUSDT")
        target.add_argument("--days", type=float, default=30.0, help="窗口天数；OI 历史只保留约 30 天")
        target.add_argument("--cache-dir", default=str(_DEFAULT_CACHE))
        target.add_argument("--refresh", action="store_true", help="忽略缓存重新拉取")

    fetch = sub.add_parser("fetch", help="拉取并缓存历史")
    common(fetch)
    fetch.set_defaults(func=_cmd_fetch)

    describe = sub.add_parser("describe", help="窗口统计与方向基准率")
    common(describe)
    describe.set_defaults(func=_cmd_describe)

    sweep = sub.add_parser("sweep", help="扫描一个阈值")
    common(sweep)
    sweep.add_argument("--key", required=True, help="marketTrigger 下的键名")
    sweep.add_argument("--values", required=True, help="逗号分隔的候选取值")
    sweep.add_argument("--signal-type", default="", help="只统计该 signal_type 的触发")
    sweep.add_argument("--horizon", type=int, default=60, help="前瞻分钟数")
    sweep.add_argument("--warmup-bars", type=int, default=500)
    sweep.add_argument("--base-config", default="", help="JSON 字符串，基线配置")
    sweep.add_argument(
        "--no-isolate",
        action="store_true",
        help="不关闭其他行情维度（看整套阈值的合计频次时用）",
    )
    sweep.add_argument("--out", default="", help="结果写入该文件")
    sweep.set_defaults(func=_cmd_sweep)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=getattr(logging, str(args.log_level).upper(), logging.INFO), format="%(asctime)s %(message)s")
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
