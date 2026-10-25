"""Unified routing and execution for FundVoice synthetic test scenarios."""

from app.services.scenario_router import classify_scenario
from app.services.scenario_calculations import (
    calculate_tc1,
    calculate_tc2,
    calculate_tc3,
)
from app.services.request_safety import audit_request_safety


def run_scenario(request, data=None):
    """Route a request to a synthetic test or audited safety decision."""
    data = data or {}
    classification = classify_scenario(request)
    name = classification["scenario"]

    if name == "TC4":
        return {
            "scenario": "TC4",
            "classification": classification,
            "result": audit_request_safety(request),
        }

    if name == "TC1":
        if "units" not in data or "nav" not in data:
            return {
                "scenario": name,
                "classification": classification,
                "result": None,
            }
        result = calculate_tc1(data["units"], data["nav"])
        return {
            "scenario": name,
            "classification": classification,
            "result": result,
        }

    if name == "TC2":
        if "holdings" not in data:
            return {
                "scenario": name,
                "classification": classification,
                "result": None,
            }
        result = calculate_tc2(data["holdings"])
        return {
            "scenario": name,
            "classification": classification,
            "result": result,
        }

    if name == "TC3":
        required = (
            "before_units",
            "before_nav",
            "after_units",
            "after_nav",
        )
        if not all(key in data for key in required):
            return {
                "scenario": name,
                "classification": classification,
                "result": None,
            }
        result = calculate_tc3(
            data["before_units"],
            data["before_nav"],
            data["after_units"],
            data["after_nav"],
        )
        return {
            "scenario": name,
            "classification": classification,
            "result": result,
        }

    return {
        "scenario": "PORTFOLIO",
        "classification": classification,
        "result": None,
    }
