from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ReplayValidationResult:
    replay: dict[str, Any]
    validation: dict[str, Any]


def replay_backtest(events: list[dict[str, Any]]) -> dict[str, Any]:
    decisions: list[dict[str, Any]] = []
    orders: dict[str, dict[str, Any]] = {}
    positions: dict[str, float] = defaultdict(float)
    cash_pnl = 0.0
    realized_pnl = 0.0

    for event in events:
        event_type = str(event.get("type", "")).lower()
        if event_type == "decision":
            decisions.append(event)
            continue

        if event_type == "order":
            order_id = str(event.get("order_id") or f"order-{len(orders)+1}")
            qty = float(event.get("quantity", 0.0))
            price = float(event.get("price", 0.0))
            side = str(event.get("side", "buy")).lower()
            signed_qty = qty if side == "buy" else -qty
            orders[order_id] = {
                "order_id": order_id,
                "symbol": event.get("symbol"),
                "side": side,
                "quantity": qty,
                "limit_price": price,
                "status": "accepted",
                "filled_quantity": 0.0,
                "avg_fill_price": 0.0,
                "fills": [],
                "signed_quantity": signed_qty,
            }
            continue

        if event_type == "fill":
            order_id = str(event.get("order_id") or "")
            if order_id not in orders:
                continue
            fill_qty = float(event.get("quantity", 0.0))
            fill_px = float(event.get("price", 0.0))
            fee = float(event.get("fee", 0.0))
            order = orders[order_id]
            symbol = str(order.get("symbol") or event.get("symbol") or "UNKNOWN")
            signed_fill_qty = fill_qty if order["side"] == "buy" else -fill_qty
            prior_fill_qty = float(order["filled_quantity"])
            order["filled_quantity"] = prior_fill_qty + fill_qty
            order["fills"].append({"quantity": fill_qty, "price": fill_px, "fee": fee})
            if order["filled_quantity"] > 0:
                total_notional = sum(f["quantity"] * f["price"] for f in order["fills"])
                order["avg_fill_price"] = total_notional / order["filled_quantity"]
            order["status"] = "filled" if abs(order["filled_quantity"] - order["quantity"]) < 1e-9 else "partial"
            positions[symbol] += signed_fill_qty
            cash_pnl += -(signed_fill_qty * fill_px) - fee
            realized_pnl -= fee

    return {
        "decisions": decisions,
        "orders": list(orders.values()),
        "positions": [{"symbol": symbol, "quantity": qty} for symbol, qty in sorted(positions.items())],
        "pnl_state": {
            "cash": round(cash_pnl, 8),
            "realized": round(realized_pnl, 8),
            "unrealized": 0.0,
            "total": round(cash_pnl + realized_pnl, 8),
        },
    }


def validate_replay(
    replay: dict[str, Any],
    expected: dict[str, Any],
    *,
    run_strategy_version: str,
    run_config_hash: str,
    requested_strategy_version: str,
    requested_config_hash: str,
) -> ReplayValidationResult:
    pin_matches = (
        run_strategy_version == requested_strategy_version
        and run_config_hash == requested_config_hash
    )

    mismatches: list[dict[str, Any]] = []
    for key in ("decisions", "orders", "positions", "pnl_state"):
        if expected.get(key) != replay.get(key):
            mismatches.append(
                {
                    "component": key,
                    "expected": expected.get(key),
                    "actual": replay.get(key),
                }
            )

    return ReplayValidationResult(
        replay=replay,
        validation={
            "pinning": {
                "requested": {
                    "strategy_version": requested_strategy_version,
                    "config_hash": requested_config_hash,
                },
                "run": {
                    "strategy_version": run_strategy_version,
                    "config_hash": run_config_hash,
                },
                "matches": pin_matches,
            },
            "status": "ok" if pin_matches and not mismatches else "diverged",
            "mismatch_count": len(mismatches),
            "mismatches": mismatches,
        },
    )
