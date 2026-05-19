"""Helpers for shaping planner responses for the frontend."""

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

