
from langgraph.graph import StateGraph, START, END

from app.agents.state import FundVoiceState
from app.agents.nodes import (
    validate_portfolio_node,
    retrieve_nav_node,
    verify_nav_node,
    calculate_valuation_node,
    generate_report_node,
    human_review_node,
)


def route_after_validation(state: FundVoiceState) -> str:
    if state.get("human_review_required", False):
        return "human_review"
    return "retrieve_nav"


def route_after_retrieval(state: FundVoiceState) -> str:
    if state.get("human_review_required", False):
        return "human_review"
    return "verify_nav"


def route_after_verification(state: FundVoiceState) -> str:
    if state.get("human_review_required", False):
        return "human_review"
    return "calculate_valuation"


def route_after_valuation(state: FundVoiceState) -> str:
    if state.get("human_review_required", False):
        return "human_review"
    return "generate_report"


def build_fundvoice_graph():
    """Build and compile the FundVoice AI portfolio workflow."""
    builder = StateGraph(FundVoiceState)

    builder.add_node("validate_portfolio", validate_portfolio_node)
    builder.add_node("retrieve_nav", retrieve_nav_node)
    builder.add_node("verify_nav", verify_nav_node)
    builder.add_node("calculate_valuation", calculate_valuation_node)
    builder.add_node("generate_report", generate_report_node)
    builder.add_node("human_review", human_review_node)

    builder.add_edge(START, "validate_portfolio")

    builder.add_conditional_edges(
        "validate_portfolio",
        route_after_validation,
        {
            "retrieve_nav": "retrieve_nav",
            "human_review": "human_review",
        },
    )

    builder.add_conditional_edges(
        "retrieve_nav",
        route_after_retrieval,
        {
            "verify_nav": "verify_nav",
            "human_review": "human_review",
        },
    )

    builder.add_conditional_edges(
        "verify_nav",
        route_after_verification,
        {
            "calculate_valuation": "calculate_valuation",
            "human_review": "human_review",
        },
    )

    builder.add_conditional_edges(
        "calculate_valuation",
        route_after_valuation,
        {
            "generate_report": "generate_report",
            "human_review": "human_review",
        },
    )

    builder.add_edge("generate_report", END)
    builder.add_edge("human_review", END)

    return builder.compile()


fundvoice_graph = build_fundvoice_graph()
