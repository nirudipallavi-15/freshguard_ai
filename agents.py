"""
FreshGuard AI - Python Multi-Agent Architecture
"""

import math
from typing import List, Dict, Any, Optional

class DemandAgent:
    """
    Transparent baseline forecast:
    Uses 7-day weighted moving average giving higher weight to recent days.
    Clearly marked as a transparent baseline forecast, NOT a trained ML model.
    """
    @staticmethod
    def analyze(item: Dict[str, Any], demand_multiplier: float = 1.0) -> Dict[str, Any]:
        sales = item.get("history_sales", [10, 10, 10, 10, 10, 10, 10])
        weights = [0.05, 0.08, 0.10, 0.12, 0.15, 0.22, 0.28]
        n = len(sales)

        weighted_sum = sum(sales[i] * (weights[i] if i < len(weights) else 1.0 / n) for i in range(n))
        weight_total = sum(weights[:n]) if n <= len(weights) else 1.0

        baseline_daily = (weighted_sum / weight_total) * demand_multiplier

        # Volatility
        mean_sales = sum(sales) / n
        variance = sum((s - mean_sales) ** 2 for s in sales) / n
        std_dev = math.sqrt(variance)

        lead_time = item.get("lead_time_days", 2)
        shelf_life = max(0, item.get("days_to_expiry", 0))

        lead_time_demand = baseline_daily * lead_time
        shelf_life_demand = baseline_daily * shelf_life

        return {
            "agent": "Demand Agent",
            "daily_forecast": round(baseline_daily, 1),
            "lead_time_demand": round(lead_time_demand, 1),
            "shelf_life_demand": round(shelf_life_demand, 1),
            "volatility_std": round(std_dev, 2),
            "method": "Transparent 7-Day Weighted Moving Average (Baseline Forecast)",
            "is_ml_model": False,
            "note": "Transparent baseline heuristic; accounts for recent sales momentum without black-box ML.",
        }

class FreshnessAgent:
    """
    Evaluates perishability risk index:
    Compares current inventory against expected sales before expiry date.
    """
    @staticmethod
    def analyze(item: Dict[str, Any], demand_forecast: Dict[str, Any], shelf_life_delta: int = 0) -> Dict[str, Any]:
        effective_days = item.get("days_to_expiry", 0) + shelf_life_delta
        current_stock = item.get("current_stock", 0)
        daily_demand = max(0.1, demand_forecast.get("daily_forecast", 1.0))

        if effective_days <= 0:
            return {
                "agent": "Freshness Agent",
                "risk_level": "EXPIRED",
                "risk_score": 100,
                "effective_days": effective_days,
                "surplus_units": current_stock,
                "expected_sales_before_expiry": 0,
                "explanation": f"Product has reached or exceeded its expiration date ({effective_days} days). Unsafe for retail sale.",
            }

        expected_sales = math.floor(daily_demand * effective_days)
        surplus_units = max(0, current_stock - expected_sales)

        risk_ratio = surplus_units / max(1, current_stock)
        risk_score = min(100, int(risk_ratio * 100))

        if effective_days <= 1 and surplus_units > 0:
            risk_level = "CRITICAL"
            risk_score = max(85, risk_score)
        elif effective_days <= 2 and surplus_units > 0:
            risk_level = "CRITICAL"
            risk_score = max(75, risk_score)
        elif effective_days <= 3 and surplus_units > 0:
            risk_level = "HIGH"
            risk_score = max(60, risk_score)
        elif surplus_units > 0:
            risk_level = "MEDIUM"
            risk_score = max(40, risk_score)
        else:
            risk_level = "LOW"
            risk_score = min(25, risk_score)

        return {
            "agent": "Freshness Agent",
            "risk_level": risk_level,
            "risk_score": risk_score,
            "effective_days": effective_days,
            "surplus_units": surplus_units,
            "expected_sales_before_expiry": expected_sales,
            "explanation": (
                f"Surplus of {surplus_units} units projected to expire within {effective_days} days."
                if surplus_units > 0
                else f"Stock velocity is healthy. All {current_stock} units expected to sell before expiry."
            ),
        }

class ReplenishmentAgent:
    """
    Identifies stockouts and excess inventory.
    Guardrail: Avoid replenishing items when current stock already exceeds forecast demand.
    """
    @staticmethod
    def analyze(item: Dict[str, Any], demand_forecast: Dict[str, Any], freshness: Dict[str, Any]) -> Dict[str, Any]:
        net_available = item.get("current_stock", 0) + item.get("incoming_shipment", 0)
        lead_time_demand = demand_forecast.get("lead_time_demand", 0)
        lead_time = item.get("lead_time_days", 2)
        volatility = demand_forecast.get("volatility_std", 2.0)

        safety_stock = math.ceil(1.5 * math.sqrt(lead_time) * volatility)
        reorder_point = math.ceil(lead_time_demand + safety_stock)
        target_max_stock = math.ceil(reorder_point * 1.8)

        is_stockout_risk = net_available < reorder_point
        is_excess = freshness.get("surplus_units", 0) > (item.get("current_stock", 0) * 0.4) and item.get("current_stock", 0) > 20

        suggested_order = 0
        recommendation = "NO_ORDER"
        reasoning = ""

        if freshness.get("risk_level") in ("EXPIRED", "CRITICAL"):
            suggested_order = 0
            recommendation = "FREEZE_REORDERS"
            reasoning = "Perishability risk is critical. Supplier reorders suspended to prevent incoming inventory compounding waste."
        elif is_stockout_risk:
            suggested_order = max(0, target_max_stock - net_available)
            suggested_order = math.ceil(suggested_order / 5) * 5
            recommendation = "REORDER"
            reasoning = f"Stock ({net_available}) is below reorder point ({reorder_point}). Projected stockout in {lead_time} days."
        elif is_excess:
            suggested_order = 0
            recommendation = "EXCESS_HOLD"
            reasoning = f"Inventory ({item.get('current_stock')}) exceeds forecast demand by {freshness.get('surplus_units')} units. Hold replenishment."
        else:
            suggested_order = 0
            recommendation = "MAINTAIN"
            reasoning = f"Inventory optimal. Net stock ({net_available}) safely covers reorder point ({reorder_point})."

        return {
            "agent": "Replenishment Agent",
            "recommendation": recommendation,
            "suggested_order_qty": suggested_order,
            "reorder_point": reorder_point,
            "safety_stock": safety_stock,
            "net_available": net_available,
            "is_stockout_risk": is_stockout_risk,
            "is_excess_inventory": is_excess,
            "reasoning": reasoning,
        }

class MarkdownAgent:
    """
    Suggests illustrative discounts for near-expiry items using configurable business rules.
    """
    @staticmethod
    def analyze(item: Dict[str, Any], freshness: Dict[str, Any]) -> Dict[str, Any]:
        if freshness.get("risk_level") == "EXPIRED":
            return {
                "agent": "Markdown Agent",
                "suggested_discount_pct": 0,
                "markdown_tier": "NONE",
                "simulated_demand_lift": 1.0,
                "expected_units_cleared": 0,
                "salvage_value": 0.0,
                "reasoning": "Expired items cannot be sold at any discount due to food safety regulations.",
            }

        effective_days = freshness.get("effective_days", 0)
        surplus_units = freshness.get("surplus_units", 0)

        discount_pct = 0
        tier = "NONE"
        elasticity_lift = 1.0

        if effective_days <= 1 and surplus_units > 0:
            discount_pct = 50
            tier = "CLEARANCE_50"
            elasticity_lift = 2.4
        elif effective_days <= 2 and surplus_units > 0:
            discount_pct = 30
            tier = "FRESH_PICK_30"
            elasticity_lift = 1.7
        elif effective_days <= 3 and surplus_units > 0:
            discount_pct = 20
            tier = "SAVER_20"
            elasticity_lift = 1.35
        else:
            discount_pct = 0
            tier = "REGULAR_PRICE"
            elasticity_lift = 1.0

        expected_rescued = min(surplus_units, int(surplus_units * (elasticity_lift - 1.0) * 0.85))
        discounted_price = item.get("unit_price", 0.0) * (1 - discount_pct / 100.0)
        salvage_value = round(expected_rescued * discounted_price, 2)

        return {
            "agent": "Markdown Agent",
            "suggested_discount_pct": discount_pct,
            "markdown_tier": tier,
            "simulated_demand_lift": elasticity_lift,
            "expected_units_cleared": expected_rescued,
            "discounted_price": round(discounted_price, 2),
            "salvage_value": salvage_value,
            "reasoning": (
                f"Recommend {discount_pct}% dynamic markdown. Simulated elasticity indicates {int((elasticity_lift - 1) * 100)}% lift, rescuing ~{expected_rescued} surplus units."
                if discount_pct > 0
                else "No markdown required. Current regular price will clear inventory safely."
            ),
        }

class CoordinatorAgent:
    """
    Synthesizes multi-agent recommendations, evaluates inter-store transfers,
    and enforces constraints and human approvals.
    """
    @staticmethod
    def synthesize(inventory_list: List[Dict[str, Any]], demand_multiplier: float = 1.0, shelf_life_delta: int = 0) -> List[Dict[str, Any]]:
        analyzed_items = []
        for item in inventory_list:
            demand = DemandAgent.analyze(item, demand_multiplier)
            freshness = FreshnessAgent.analyze(item, demand, shelf_life_delta)
            replenishment = ReplenishmentAgent.analyze(item, demand, freshness)
            markdown = MarkdownAgent.analyze(item, freshness)
            analyzed_items.append({
                "item": item,
                "demand": demand,
                "freshness": freshness,
                "replenishment": replenishment,
                "markdown": markdown,
            })

        # Inter-Store Transfer Matching
        transfer_opportunities = []
        for source in analyzed_items:
            s_fresh = source["freshness"]
            s_item = source["item"]
            if s_fresh.get("surplus_units", 0) >= 5 and s_fresh.get("effective_days", 0) >= 2:
                for target in analyzed_items:
                    t_item = target["item"]
                    t_replenish = target["replenishment"]
                    if (
                        t_item.get("sku") == s_item.get("sku")
                        and t_item.get("store") != s_item.get("store")
                        and (t_replenish.get("is_stockout_risk") or t_item.get("current_stock", 0) < 12)
                    ):
                        qty = min(
                            s_fresh.get("surplus_units", 0),
                            max(5, t_replenish.get("suggested_order_qty", 15)),
                        )
                        if qty >= 5:
                            transfer_opportunities.append({
                                "source_id": s_item.get("id"),
                                "target_id": t_item.get("id"),
                                "source_store": s_item.get("store"),
                                "target_store": t_item.get("store"),
                                "transfer_qty": qty,
                            })

        final_recommendations = []
        for record in analyzed_items:
            item = record["item"]
            demand = record["demand"]
            freshness = record["freshness"]
            replenishment = record["replenishment"]
            markdown = record["markdown"]

            action = "MAINTAIN"
            action_label = "Maintain Routine"
            qty = 0
            discount_pct = 0
            confidence = 85
            rationale = ""
            expected_effect = {}

            # Rule 1: Expired Food Safety Guardrail
            if freshness.get("risk_level") == "EXPIRED":
                action = "CULL_EXPIRED"
                action_label = "Food Safety Cull"
                qty = item.get("current_stock", 0)
                confidence = 99
                rationale = f"CRITICAL SAFETY GUARDRAIL: {qty} units expired ({freshness.get('effective_days')} days). Strictly barred from sale or transfer. Dispose & compost."
                expected_effect = {
                    "waste_units": qty,
                    "simulated_benefit": "Zero health code violations; regulatory compliance ensured.",
                }
            else:
                transfer_as_source = next((t for t in transfer_opportunities if t["source_id"] == item.get("id")), None)
                transfer_as_target = next((t for t in transfer_opportunities if t["target_id"] == item.get("id")), None)

                if transfer_as_source:
                    action = "TRANSFER_OUT"
                    action_label = f"Inter-Store Transfer to {transfer_as_source['target_store']}"
                    qty = transfer_as_source["transfer_qty"]
                    confidence = 90
                    rationale = f"CROSS-STORE BALANCING: {freshness.get('surplus_units')} surplus units expiring in {freshness.get('effective_days')} days. Transferring {qty} units to {transfer_as_source['target_store']} saves waste at 100% full retail price."
                    expected_effect = {
                        "waste_prevented_units": qty,
                        "salvaged_revenue": round(qty * item.get("unit_price", 0.0), 2),
                        "simulated_benefit": f"Avoids ${round(qty * item.get('unit_cost', 0.0), 2)} write-off and fulfills sister store demand.",
                    }
                elif transfer_as_target:
                    action = "TRANSFER_IN"
                    action_label = f"Receive Transfer from {transfer_as_target['source_store']}"
                    qty = transfer_as_target["transfer_qty"]
                    confidence = 90
                    rationale = f"SUPPLY CHAIN OPTIMIZATION: Incoming shuttle transfer of {qty} units from {transfer_as_target['source_store']} avoids placing external purchase order."
                    expected_effect = {
                        "stockout_prevented_units": qty,
                        "salvaged_revenue": round(qty * item.get("unit_price", 0.0), 2),
                        "simulated_benefit": "Fulfills impending stockout without supplier reorder minimums.",
                    }
                elif freshness.get("risk_level") in ("CRITICAL", "HIGH") and markdown.get("suggested_discount_pct", 0) > 0:
                    action = "DYNAMIC_MARKDOWN"
                    discount_pct = markdown.get("suggested_discount_pct", 0)
                    action_label = f"Apply {discount_pct}% Dynamic Markdown"
                    qty = freshness.get("surplus_units", 0)
                    confidence = 88
                    rationale = f"FRESHNESS INTERVENTION: {qty} units at high waste risk ({freshness.get('effective_days')} days left). Propose {discount_pct}% discount to accelerate velocity by {int((markdown.get('simulated_demand_lift', 1) - 1) * 100)}%."
                    expected_effect = {
                        "waste_prevented_units": markdown.get("expected_units_cleared", 0),
                        "salvaged_revenue": markdown.get("salvage_value", 0.0),
                        "simulated_benefit": f"Rescues ~{markdown.get('expected_units_cleared', 0)} units from landfill; recovers ${markdown.get('salvage_value', 0.0)}.",
                    }
                elif replenishment.get("is_stockout_risk") and replenishment.get("suggested_order_qty", 0) > 0:
                    action = "REPLENISH"
                    qty = replenishment.get("suggested_order_qty", 0)
                    action_label = f"Purchase Order (+{qty} units)"
                    confidence = 85
                    rationale = f"STOCKOUT PREVENTION: Stock ({replenishment.get('net_available')}) breached reorder point ({replenishment.get('reorder_point')}). Place supplier replenishment."
                    expected_effect = {
                        "stockout_prevented_units": qty,
                        "simulated_benefit": f"Maintains 98% on-shelf availability; secures ~${round(qty * item.get('unit_price', 0.0), 2)} demand.",
                    }
                elif replenishment.get("is_excess_inventory"):
                    action = "HOLD_REORDERS"
                    action_label = "Pause Reorders (Overstocked)"
                    confidence = 92
                    rationale = f"OVERSTOCK GUARDRAIL: Current inventory ({item.get('current_stock')}) covers demand. Avoid new replenishment to reduce perishability risk."
                    expected_effect = {
                        "simulated_benefit": "Conserves working capital and frees storage space.",
                    }
                else:
                    action = "MAINTAIN"
                    action_label = "Monitor (Stock Healthy)"
                    confidence = 95
                    rationale = f"EQUILIBRIUM: Daily demand ({demand.get('daily_forecast')} units/day) matches inventory runway ({freshness.get('effective_days')} days). Stock will clear organically at full price."
                    expected_effect = {
                        "simulated_benefit": "Operating at optimal target turnover.",
                    }

            final_recommendations.append({
                "id": item.get("id"),
                "sku": item.get("sku"),
                "name": item.get("name"),
                "category": item.get("category"),
                "store": item.get("store"),
                "current_stock": item.get("current_stock"),
                "unit_price": item.get("unit_price"),
                "unit_cost": item.get("unit_cost"),
                "days_to_expiry": item.get("days_to_expiry"),
                "effective_days": freshness.get("effective_days"),
                "daily_forecast": demand.get("daily_forecast"),
                "risk_level": freshness.get("risk_level"),
                "risk_score": freshness.get("risk_score"),
                "surplus_units": freshness.get("surplus_units"),
                "action": action,
                "action_label": action_label,
                "proposed_quantity": qty,
                "proposed_discount_pct": discount_pct,
                "confidence": confidence,
                "rationale": rationale,
                "expected_effect": expected_effect,
                "agent_breakdown": {
                    "demand": demand,
                    "freshness": freshness,
                    "replenishment": replenishment,
                    "markdown": markdown,
                },
                "approval_status": "PENDING",
                "planner_notes": "",
            })

        return final_recommendations
