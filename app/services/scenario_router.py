"""Route FundVoice requests to safety checks or test scenarios."""

from app.services.request_safety import classify_request


def classify_scenario(request: str) -> dict:
    """Identify the scenario without executing trades or valuing a portfolio."""

    safety = classify_request(request)

    # Trading safety always takes priority.
    if safety["status"] != "ALLOWED":
        return {
            "scenario": "TC4",
            "status": safety["status"],
            "reason": safety["reason"],
        }

    text = request.strip().lower()

    if not text:
        return {
            "scenario": "NEEDS_INPUT",
            "status": "REJECTED",
            "reason": "Please enter a request or portfolio scenario.",
        }

    # TC3: unit-split scenario.
    split_terms = (
        "split",
        "unit split",
        "before and after",
        "before split",
        "after split",
    )
    if any(term in text for term in split_terms):
        return {
            "scenario": "TC3",
            "status": "NEEDS_TEST_DATA",
            "reason": (
                "Unit-split scenario detected. Before-and-after units "
                "and NAV values are required."
            ),
        }

    # TC2: different NAV dates.
    date_terms = (
        "different nav dates",
        "different dates",
        "mixed nav dates",
        "date mismatch",
    )
    if any(term in text for term in date_terms):
        return {
            "scenario": "TC2",
            "status": "NEEDS_TEST_DATA",
            "reason": (
                "Each holding needs units, NAV, and its NAV date."
            ),
        }

    # TC1: arithmetic scenario.
    arithmetic_terms = (
        "units x nav",
        "units * nav",
        "arithmetic",
        "calculate holding value",
        "calculate nav value",
    )
    if any(term in text for term in arithmetic_terms):
        return {
            "scenario": "TC1",
            "status": "NEEDS_TEST_DATA",
            "reason": "Units and NAV per unit are required.",
        }

    return {
        "scenario": "PORTFOLIO",
        "status": "CONTINUE",
        "reason": (
            "Continue with normal portfolio verification."
        ),
    }
