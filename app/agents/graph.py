from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.agents.nodes import (
    calculate_valuation_node,
    generate_report_node,
    human_review_node,
    retrieve_nav_node,
    validate_portfolio_node,
    verify_nav_node,
)

from app.agents.state import FundVoiceState


def route_after_validation(
    state: FundVoiceState,
) -> Literal["retrieve_nav", "human_review"]:
    """Route execution after portfolio validation."""

    if state.get("human_review_required", False):
        return "human_review"

    return "retrieve_nav"


def route_after_retrieval(
    state: FundVoiceState,
) -> Literal["verify_nav", "retry_nav", "human_review"]:
    """Route execution after NAV retrieval."""

    if state.get("human_review_required", False):
        return "human_review"

    if state.get("next_action") == "retry_nav":
        return "retry_nav"

    return "verify_nav"


def route_after_verification(
    state: FundVoiceState,
) -> Literal["calculate_valuation", "human_review"]:
    """Allow valuation only when verification succeeds."""

    if state.get("human_review_required", False):
        return "human_review"

    return "calculate_valuation"


def build_graph():
    """Build and compile the FundVoiceAI LangGraph workflow."""

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
            "retry_nav": "retrieve_nav",
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

    builder.add_edge("calculate_valuation", "generate_report")
    builder.add_edge("generate_report", END)
    builder.add_edge("human_review", END)

    return builder.compile()


fundvoice_graph = build_graph()