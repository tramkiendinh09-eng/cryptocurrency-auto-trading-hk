from __future__ import annotations


def _pct(entry_price: float, price: float, side: str) -> float:
    if entry_price <= 0 or price <= 0:
        return 0.0
    raw = ((price - entry_price) / entry_price) * 100.0
    return raw if side == "long" else -raw


def calculate_outcome_metrics(
    *,
    entry_price: float,
    side: str,
    future_prices: list[float],
    realized_pnl: float = 0.0,
) -> dict[str, float]:
    normalized_side = str(side or "").strip().lower()
    moves = [_pct(float(entry_price or 0.0), float(price or 0.0), normalized_side) for price in future_prices if float(price or 0.0) > 0]
    if not moves:
        return {"final_move_pct": 0.0, "mfe_pct": 0.0, "mae_pct": 0.0, "realized_pnl": float(realized_pnl)}
    return {
        "final_move_pct": round(moves[-1], 6),
        "mfe_pct": round(max(moves), 6),
        "mae_pct": round(min(moves), 6),
        "realized_pnl": float(realized_pnl),
    }
