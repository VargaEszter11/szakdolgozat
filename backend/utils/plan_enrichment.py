"""Merge Amadeus-backed validation details into the LLM draft plan for API responses."""

from __future__ import annotations

import copy
from typing import Any, Dict, Optional


def normalize_planner_response(plan: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Random-mode LLM output uses a ``trips`` array; the UI expects one object with ``plan``."""
    if not plan or not isinstance(plan, dict):
        return plan
    if isinstance(plan.get("plan"), list):
        return plan
    trips = plan.get("trips")
    if isinstance(trips, list) and trips:
        inner = copy.deepcopy(trips[0])
        for key in ("startDate", "endDate", "tripLengthDays"):
            if key in plan and plan[key] is not None:
                inner.setdefault(key, plan[key])
        return inner
    return plan


def merge_validation_into_plan(
    plan: Optional[Dict[str, Any]], validation: Optional[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """Attach per-stop pricing, flight schedule, hotel, and activity summaries to ``plan``."""
    if not plan or not isinstance(plan, dict) or validation is None:
        return plan
    out = copy.deepcopy(plan)
    stops = out.get("plan")
    if not isinstance(stops, list):
        return out
    vsegs = validation.get("segments") or []
    for i, stop in enumerate(stops):
        if i >= len(vsegs):
            break
        v = vsegs[i]
        stop["cost_detail"] = {
            "transport_eur": v.get("transport_price") or 0,
            "hotel_eur": v.get("hotel_price") or 0,
            "activities_eur": v.get("activity_price") or 0,
            "segment_total_eur": v.get("price") or 0,
        }
        if v.get("flight_booking"):
            stop["flight_booking"] = v["flight_booking"]
        if v.get("hotel_booking"):
            stop["hotel_booking"] = v["hotel_booking"]
        if v.get("activity_booking"):
            stop["activity_booking"] = v["activity_booking"]
        if v.get("origin_airport"):
            stop["origin_airport_iata"] = v["origin_airport"]
        if v.get("destination_airport"):
            stop["destination_airport_iata"] = v["destination_airport"]
    out["trip_pricing"] = {
        "grand_total_eur": validation.get("total_price"),
        "budget_eur": validation.get("budget"),
        "remaining_budget_eur": validation.get("remaining_budget"),
        "within_budget": validation.get("valid"),
        "breakdown_eur": validation.get("cost_breakdown") or {},
        "validation_score": validation.get("score"),
        "validation_reason": validation.get("reason"),
    }
    return out
