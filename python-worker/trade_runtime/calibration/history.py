"""拉取并缓存 Binance USD-M 永续的历史序列。

用途是给触发阈值做离线校准，所以取数原则和实时路径不同：实时路径只需要
「现在」，这里需要一段**对齐到同一时间轴**的多源序列，且必须可复现——
校准结论只有在数据可重放时才有意义，因此结果落盘缓存，重跑不再打网络。

四条序列都来自公开免鉴权端点：

===========================  ============================================
``/fapi/v1/klines``          成交价 K 线，1m 为主序列
``/fapi/v1/markPriceKlines`` 标记价 K 线，用于复刻 ``mark_price_deviation_pct``
``/futures/data/openInterestHist``  持仓量名义值，5m 粒度
``/fapi/v1/fundingRate``     资金费率结算历史，8h 一条
===========================  ============================================

三个限制必须写在这里，否则读校准报告的人会高估结论的适用范围：

1. **没有历史爆仓数据。** 全市场爆仓只有 ``!forceOrder@arr`` 这个 websocket
   实时流，没有任何 REST 历史接口。所以 ``liquidationNotional*`` 系列阈值
   **无法校准**，本模块也不会用持仓量骤降去合成假的爆仓事件。
2. **持仓量历史只保留约 30 天**，且最细 5m。跨度超过 30 天的窗口，OI 序列
   会从头部开始缺失，``replay`` 会把缺失段的 ``oi_change_pct`` 记为 0。
3. **资金费率是结算值，不是实时预测值。** 实时路径读的 ``premiumIndex``
   给的是下一次结算的预测费率，历史只能拿到已结算值。两者在结算时刻收敛，
   窗口内则是阶梯而非连续曲线——校准 ``fundingRateAbs`` 时这是保守方向
   （阶梯值波动小于预测值，得到的阈值偏松而非偏紧）。
"""

from __future__ import annotations

import json
import logging
import time
from bisect import bisect_right
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests

from ..ingestion.binance_rest import normalize_binance_symbol

logger = logging.getLogger(__name__)

_BASE_URL = "https://fapi.binance.com"
# klines 单次上限 1500；openInterestHist 上限 500。
_KLINE_PAGE_LIMIT = 1500
_OI_PAGE_LIMIT = 500
_MINUTE_MS = 60_000


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


@dataclass
class HistoryBundle:
    """一段时间窗口内、对齐到 1 分钟轴的多源历史。

    ``candles`` 是主序列，其余按时间就近对齐（见 ``replay``）。所有时间戳是
    K 线的 open_time，单位毫秒 UTC。
    """

    symbol: str
    start_ms: int
    end_ms: int
    candles: list[dict[str, Any]] = field(default_factory=list)
    mark_candles: list[dict[str, Any]] = field(default_factory=list)
    open_interest: list[dict[str, Any]] = field(default_factory=list)
    funding_rates: list[dict[str, Any]] = field(default_factory=list)

    @property
    def minutes(self) -> int:
        return len(self.candles)

    def coverage(self) -> dict[str, Any]:
        """各序列的实际覆盖情况，用于在报告里说明数据完整度。"""
        expected = max(0, (self.end_ms - self.start_ms) // _MINUTE_MS)
        oi_span_ms = 0
        if len(self.open_interest) >= 2:
            oi_span_ms = int(self.open_interest[-1]["timestamp"]) - int(self.open_interest[0]["timestamp"])
        return {
            "symbol": self.symbol,
            "expected_minutes": expected,
            "candle_minutes": len(self.candles),
            "mark_candle_minutes": len(self.mark_candles),
            "open_interest_samples": len(self.open_interest),
            "open_interest_span_hours": round(oi_span_ms / 3_600_000, 2),
            "funding_settlements": len(self.funding_rates),
            # 爆仓维度没有公开历史来源，这里显式标注而不是留空,
            # 免得报告读者以为「0 次触发」等于「阈值合适」。
            "liquidation_history": "unavailable_public_rest",
        }


class _Fetcher:
    def __init__(self, *, base_url: str = _BASE_URL, timeout: int = 20, sleep_seconds: float = 0.25):
        self.base_url = base_url.rstrip("/")
        self.timeout = int(timeout)
        self.sleep_seconds = float(sleep_seconds)

    def get(self, path: str, params: dict[str, Any]) -> Any:
        response = requests.get(f"{self.base_url}{path}", params=params, timeout=self.timeout)
        response.raise_for_status()
        # 分页拉取会连续打同一权重端点，留一点间隔避免撞到限频。
        time.sleep(self.sleep_seconds)
        return response.json()

    def paged_klines(self, path: str, symbol: str, interval: str, start_ms: int, end_ms: int) -> list[list[Any]]:
        rows: list[list[Any]] = []
        cursor = start_ms
        while cursor < end_ms:
            payload = self.get(
                path,
                {
                    "symbol": symbol,
                    "interval": interval,
                    "startTime": cursor,
                    "endTime": end_ms,
                    "limit": _KLINE_PAGE_LIMIT,
                },
            )
            if not isinstance(payload, list) or not payload:
                break
            rows.extend(row for row in payload if isinstance(row, list) and len(row) >= 8)
            last_open = int(payload[-1][0])
            if last_open <= cursor:
                # 游标没有前进说明区间已经走完，再请求会无限循环。
                break
            cursor = last_open + _MINUTE_MS
            if len(payload) < _KLINE_PAGE_LIMIT:
                break
        return rows


def _candle_from_row(row: list[Any], symbol: str, interval: str) -> dict[str, Any]:
    """与 ``BinanceRestMarketClient.fetch_candles`` 完全一致的字段形状。

    形状必须一致——``kline_indicators`` 的指标函数直接读这些键，
    差一个字段名就会静默算出 0。
    """
    return {
        "event_type": "market_kline",
        "symbol": symbol,
        "exchange": "binance",
        "interval": interval,
        "open_time": str(row[0] or ""),
        "close_time": str(row[6] or ""),
        "open": _safe_float(row[1]),
        "high": _safe_float(row[2]),
        "low": _safe_float(row[3]),
        "close": _safe_float(row[4]),
        "volume": _safe_float(row[5]),
        "quote_volume": _safe_float(row[7]),
        "event_time": str(row[0] or ""),
    }


def _fetch_open_interest_hist(
    fetcher: _Fetcher, symbol: str, start_ms: int, end_ms: int, *, period: str = "5m"
) -> list[dict[str, Any]]:
    """持仓量名义值序列。

    币安只保留约 30 天，超出部分直接返回空数组——这不是错误，调用方按
    「该时段无 OI 数据」处理即可。

    分页必须**逐页收窄 endTime**：当 ``endTime - startTime`` 超过
    ``limit × period`` 时，这个端点会忽略 ``startTime``，直接返回贴着
    ``endTime`` 的最后 500 条。若整段窗口只传一次，拿到的是窗口末尾而非
    开头，游标随即越界、循环提前结束——症状是「30 天窗口只有 41 小时数据」。
    """
    period_ms = {"5m": 300_000, "15m": 900_000, "30m": 1_800_000, "1h": 3_600_000}.get(period, 300_000)
    rows: list[dict[str, Any]] = []
    cursor = start_ms
    empty_pages = 0
    while cursor < end_ms:
        page_end = min(end_ms, cursor + _OI_PAGE_LIMIT * period_ms)
        payload = fetcher.get(
            "/futures/data/openInterestHist",
            {
                "symbol": symbol,
                "period": period,
                "startTime": cursor,
                "endTime": page_end,
                "limit": _OI_PAGE_LIMIT,
            },
        )
        batch = (
            [item for item in payload if isinstance(item, dict) and item.get("timestamp")]
            if isinstance(payload, list)
            else []
        )
        if not batch:
            # 超出保留期的页是空的，但更近的页仍有数据，所以不能见空就停。
            # 连空两页才认为确实到头了。
            empty_pages += 1
            if empty_pages >= 2:
                break
            cursor = page_end
            continue
        empty_pages = 0
        rows.extend(
            {
                "timestamp": int(item["timestamp"]),
                "open_interest": _safe_float(item.get("sumOpenInterest")),
                "open_interest_value": _safe_float(item.get("sumOpenInterestValue")),
            }
            for item in batch
        )
        last_ts = int(batch[-1]["timestamp"])
        # startTime 是**排他**的：一页的首样本落在 startTime + period 上。
        # 因此游标推进到 last_ts 本身而不是 last_ts + period——后者会在每个
        # 分页边界上漏掉一根。重叠取到的那根由末尾去重处理。
        # last_ts 不大于游标时说明该页没有前进，退到 page_end 保证循环收敛。
        cursor = last_ts if last_ts > cursor else page_end
    # 分页边界可能重复取到同一根，去重后再返回。
    deduped: dict[int, dict[str, Any]] = {int(row["timestamp"]): row for row in rows}
    return [deduped[key] for key in sorted(deduped)]


def _fetch_funding_rates(fetcher: _Fetcher, symbol: str, start_ms: int, end_ms: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    cursor = start_ms
    while cursor < end_ms:
        payload = fetcher.get(
            "/fapi/v1/fundingRate",
            {"symbol": symbol, "startTime": cursor, "endTime": end_ms, "limit": 1000},
        )
        if not isinstance(payload, list) or not payload:
            break
        batch = [item for item in payload if isinstance(item, dict) and item.get("fundingTime")]
        if not batch:
            break
        rows.extend(
            {
                "timestamp": int(item["fundingTime"]),
                "funding_rate": _safe_float(item.get("fundingRate")),
                "mark_price": _safe_float(item.get("markPrice")),
            }
            for item in batch
        )
        last_ts = int(batch[-1]["fundingTime"])
        if last_ts <= cursor:
            break
        cursor = last_ts + 1
        if len(batch) < 1000:
            break
    return rows


def _cache_path(cache_dir: Path, symbol: str, start_ms: int, end_ms: int) -> Path:
    return cache_dir / f"{symbol}_{start_ms}_{end_ms}.json"


def load_history(
    symbol: str,
    *,
    start_ms: int,
    end_ms: int,
    cache_dir: str | Path | None = None,
    fetcher: _Fetcher | None = None,
    refresh: bool = False,
) -> HistoryBundle:
    """加载一段历史，优先读缓存。

    Args:
        symbol: 交易对，会被归一化成币安格式（BTCUSDT）
        start_ms / end_ms: UTC 毫秒时间戳，左闭右开
        cache_dir: 缓存目录；None 表示不缓存（测试用）
        fetcher: 注入用，测试时替换掉网络
        refresh: True 则忽略已有缓存重新拉取

    Returns:
        HistoryBundle: 四条序列，按时间升序
    """
    normalized = normalize_binance_symbol(symbol)
    start_ms = int(start_ms)
    end_ms = int(end_ms)
    if end_ms <= start_ms:
        raise ValueError(f"end_ms must be after start_ms (got {start_ms} .. {end_ms})")

    cache_file: Path | None = None
    if cache_dir is not None:
        cache_file = _cache_path(Path(cache_dir), normalized, start_ms, end_ms)
        if cache_file.exists() and not refresh:
            payload = json.loads(cache_file.read_text(encoding="utf-8"))
            logger.info("calibration history cache hit %s", cache_file.name)
            return HistoryBundle(
                symbol=payload["symbol"],
                start_ms=payload["start_ms"],
                end_ms=payload["end_ms"],
                candles=payload["candles"],
                mark_candles=payload["mark_candles"],
                open_interest=payload["open_interest"],
                funding_rates=payload["funding_rates"],
            )

    active = fetcher or _Fetcher()
    logger.info("fetching calibration history %s %s..%s", normalized, start_ms, end_ms)

    candles = [
        _candle_from_row(row, normalized, "1m")
        for row in active.paged_klines("/fapi/v1/klines", normalized, "1m", start_ms, end_ms)
    ]
    mark_candles = [
        _candle_from_row(row, normalized, "1m")
        for row in active.paged_klines("/fapi/v1/markPriceKlines", normalized, "1m", start_ms, end_ms)
    ]
    open_interest = _fetch_open_interest_hist(active, normalized, start_ms, end_ms)
    # 资金费率往前多取 8 小时，保证窗口第一分钟就有一条「上一次结算」可用，
    # 否则序列开头会被当成无资金费率数据。
    funding_rates = _fetch_funding_rates(active, normalized, start_ms - 8 * 3_600_000, end_ms)

    bundle = HistoryBundle(
        symbol=normalized,
        start_ms=start_ms,
        end_ms=end_ms,
        candles=candles,
        mark_candles=mark_candles,
        open_interest=open_interest,
        funding_rates=funding_rates,
    )

    if cache_file is not None:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(
            json.dumps(
                {
                    "symbol": bundle.symbol,
                    "start_ms": bundle.start_ms,
                    "end_ms": bundle.end_ms,
                    "candles": bundle.candles,
                    "mark_candles": bundle.mark_candles,
                    "open_interest": bundle.open_interest,
                    "funding_rates": bundle.funding_rates,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        logger.info("cached calibration history to %s", cache_file)

    return bundle


class TimeAlignedSeries:
    """把稀疏序列对齐到主时间轴：取「不晚于 t 的最后一个样本」。

    这是刻意的选择——校准的每一步都只能看到那一刻真实可得的数据。
    用线性插值或就近取值都会把未来信息漏进当前步，让阈值在回测里
    显得比实盘更灵敏。
    """

    def __init__(self, rows: list[dict[str, Any]], *, key: str = "timestamp"):
        self.rows = sorted(rows, key=lambda item: int(item.get(key, 0)))
        self.stamps = [int(item.get(key, 0)) for item in self.rows]

    def at(self, timestamp_ms: int) -> dict[str, Any] | None:
        if not self.stamps:
            return None
        index = bisect_right(self.stamps, int(timestamp_ms)) - 1
        if index < 0:
            return None
        return self.rows[index]
