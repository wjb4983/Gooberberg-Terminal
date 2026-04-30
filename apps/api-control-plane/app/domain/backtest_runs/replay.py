from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ReplayValidationResult:
    replay: dict[str, Any]
    validation: dict[str, Any]


def _position_event(symbol: str, quantity: float, average_price: float, fill: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_type": "PositionEvent",
        "symbol": symbol,
        "quantity": round(quantity, 8),
        "average_price": round(average_price, 8),
        "source_order_id": fill.get("order_id"),
        "source_fill_id": fill.get("fill_id"),
        "source_event_ts": fill.get("timestamp"),
    }


def _pnl_event(
    *,
    cash: float,
    realized_pnl: float,
    unrealized_pnl: float,
    fees_total: float,
    slippage_total: float,
    inventory_ok: bool,
    cash_ok: bool,
    fill: dict[str, Any],
) -> dict[str, Any]:
    return {
        "event_type": "PnLEvent",
        "realized_pnl": round(realized_pnl, 8),
        "unrealized_pnl": round(unrealized_pnl, 8),
        "cash": round(cash, 8),
        "fees_total": round(fees_total, 8),
        "slippage_total": round(slippage_total, 8),
        "inventory_conservation_ok": inventory_ok,
        "cash_consistency_ok": cash_ok,
        "source_order_id": fill.get("order_id"),
        "source_fill_id": fill.get("fill_id"),
        "source_event_ts": fill.get("timestamp"),
    }


def replay_backtest(events: list[dict[str, Any]]) -> dict[str, Any]:
    decisions: list[dict[str, Any]] = []
    orders: dict[str, dict[str, Any]] = {}
    positions: dict[str, float] = defaultdict(float)
    avg_price_by_symbol: dict[str, float] = defaultdict(float)
    cash = 0.0
    realized_pnl = 0.0
    unrealized_pnl = 0.0
    fees_total = 0.0
    slippage_total = 0.0
    position_events: list[dict[str, Any]] = []
    pnl_events: list[dict[str, Any]] = []

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

            prior_position = positions[symbol]
            prior_avg = avg_price_by_symbol[symbol]
            new_position = prior_position + signed_fill_qty
            if abs(new_position) < 1e-12:
                avg_price_by_symbol[symbol] = 0.0
            elif prior_position == 0 or (prior_position > 0) == (signed_fill_qty > 0):
                total_abs = abs(prior_position) + abs(signed_fill_qty)
                avg_price_by_symbol[symbol] = ((abs(prior_position) * prior_avg) + (abs(signed_fill_qty) * fill_px)) / total_abs
            positions[symbol] = new_position

            fee_component = fee
            expected_px = float(order.get("limit_price", fill_px) or fill_px)
            slippage_component = abs(fill_qty) * abs(fill_px - expected_px)
            fees_total += fee_component
            slippage_total += slippage_component

            cash += -(signed_fill_qty * fill_px) - fee_component
            realized_pnl -= fee_component + slippage_component

            inventory_before = sum(o["signed_quantity"] for o in orders.values())
            inventory_after = sum(positions.values())
            filled_inventory = sum(
                (f["quantity"] if o["side"] == "buy" else -f["quantity"])
                for o in orders.values()
                for f in o["fills"]
            )
            inventory_ok = abs(inventory_after - filled_inventory) < 1e-9

            expected_cash = -sum(
                (f["quantity"] if o["side"] == "buy" else -f["quantity"]) * f["price"] + f["fee"]
                for o in orders.values()
                for f in o["fills"]
            )
            cash_ok = abs(cash - expected_cash) < 1e-9

            position_events.append(_position_event(symbol, positions[symbol], avg_price_by_symbol[symbol], event))
            pnl_events.append(
                _pnl_event(
                    cash=cash,
                    realized_pnl=realized_pnl,
                    unrealized_pnl=unrealized_pnl,
                    fees_total=fees_total,
                    slippage_total=slippage_total,
                    inventory_ok=inventory_ok,
                    cash_ok=cash_ok,
                    fill=event,
                )
            )

    return {
        "decisions": decisions,
        "orders": list(orders.values()),
        "positions": [{"symbol": symbol, "quantity": qty} for symbol, qty in sorted(positions.items())],
        "position_events": position_events,
        "pnl_events": pnl_events,
        "pnl_state": {
            "cash": round(cash, 8),
            "realized": round(realized_pnl, 8),
            "unrealized": round(unrealized_pnl, 8),
            "total": round(cash + realized_pnl + unrealized_pnl, 8),
            "fees": round(fees_total, 8),
            "slippage": round(slippage_total, 8),
        },
        "reconciliation": {
            "inventory_conservation_ok": all(e["inventory_conservation_ok"] for e in pnl_events) if pnl_events else True,
            "cash_consistency_ok": all(e["cash_consistency_ok"] for e in pnl_events) if pnl_events else True,
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
