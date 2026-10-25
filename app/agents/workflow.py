
"""Compatibility wrapper for the FundVoiceAI portfolio workflow."""

from app.agents.graph import build_graph


def build_workflow():
    """Build and return the compiled portfolio workflow."""
    return build_graph()
