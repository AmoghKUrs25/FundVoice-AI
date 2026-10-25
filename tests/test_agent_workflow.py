

from datetime import date, datetime, timezone
from decimal import Decimal

from app.agents import nodes
from app.agents.graph import build_graph
from app.agents.nodes import verify_nav_node
from app.models.nav import NAVEvidence, NAVRecord
from app.models.portfolio import Holding, PortfolioStatement
from app.models.verification import VerificationStatus
from app.services.nav_retriever import NAVRetrievalError


# =========================================================
# TEST FIXTURES AND HELPERS
# =========================================================

VALUATION_DATE = date(2026, 10, 16)
OTHER_DATE = date(2026, 10, 17)


def create_portfolio():
    """Create a valid portfolio for workflow tests."""
    return PortfolioStatement(
        portfolio_id="P001",
        valuation_date=VALUATION_DATE,
        holdings=[
            Holding(
                holding_id="H001",
                scheme_name="Example Equity Fund",
                units=Decimal("10"),
            )
        ],
    )


def create_nav_record(
    nav_date=VALUATION_DATE,
    scheme_name="Example Equity Fund",
    nav=Decimal("100"),
):
    """Create a NAV record with supporting evidence."""
    evidence = NAVEvidence(
        evidence_id="E001",
        source_url="https://example.com/nav",
        retrieved_at=datetime.now(timezone.utc),
        evidence_text=(
            f"{scheme_name} NAV: {nav} "
            f"dated {nav_date.strftime('%d-%b-%Y')}"
        ),
    )

    return NAVRecord(
        scheme_name=scheme_name,
        nav_date=nav_date,
        nav=nav,
        evidence=evidence,
    )


def create_initial_state(nav_records=None):
    """Create the initial state passed to the workflow."""
    return {
        "portfolio": create_portfolio(),
        "nav_records": nav_records or [],
        "errors": [],
        "audit_events": [],
        "retry_count": 0,
        "human_review_required": False,
    }


def mock_fund_house_resolver(monkeypatch):
    """Use a deterministic fund-house ID for mocked workflow tests."""
    monkeypatch.setattr(
        nodes,
        "get_fund_house_id",
        lambda scheme_name: "9",
    )


# =========================================================
# TEST 1: Verified portfolio generates a report
# =========================================================

def test_verified_portfolio_generates_report():
    graph = build_graph()

    result = graph.invoke(
        create_initial_state([create_nav_record()])
    )

    assert result["human_review_required"] is False
    assert result["verification"].status == VerificationStatus.VERIFIED
    assert result["valuation"]["total_value"] == Decimal("1000.00")
    assert "Portfolio valuation" in result["report"]
    assert "1,000.00" in result["report"]


# =========================================================
# TEST 2: NAV date mismatch requires human review
# =========================================================

def test_date_mismatch_routes_to_human_review():
    graph = build_graph()
    wrong_date_record = create_nav_record(nav_date=OTHER_DATE)

    result = graph.invoke(
        create_initial_state([wrong_date_record])
    )

    assert result["human_review_required"] is True
    assert result["verification"].status == (
        VerificationStatus.REVIEW_REQUIRED
    )
    assert result["valuation"] is None
    assert "Human review required" in result["report"]

    assert any(
        issue.code == "NAV_DATE_MISMATCH"
        for issue in result["verification"].issues
    )


# =========================================================
# TEST 3: Missing NAV requires human review
# =========================================================

def test_missing_nav_routes_to_human_review():
    graph = build_graph()

    unrelated_record = create_nav_record(
        scheme_name="Different Equity Fund"
    )

    result = graph.invoke(
        create_initial_state([unrelated_record])
    )

    assert result["human_review_required"] is True
    assert result["verification"].status == (
        VerificationStatus.REVIEW_REQUIRED
    )
    assert result["valuation"] is None
    assert "Human review required" in result["report"]

    assert any(
        issue.code == "NAV_NOT_FOUND"
        for issue in result["verification"].issues
    )


# =========================================================
# TEST 4: First NAV retrieval failure requests a retry
# =========================================================

def test_nav_retrieval_failure_requests_retry(monkeypatch):
    mock_fund_house_resolver(monkeypatch)

    async def failing_fetch(*args, **kwargs):
        raise NAVRetrievalError("Temporary source failure")

    monkeypatch.setattr(
        nodes,
        "fetch_nav_history",
        failing_fetch,
    )

    result = nodes.retrieve_nav_node(create_initial_state())

    assert result["next_action"] == "retry_nav"
    assert result["retry_count"] == 1
    assert result["human_review_required"] is False

    assert any(
        "Temporary source failure" in error
        for error in result["errors"]
    )


# =========================================================
# TEST 5: Second NAV retrieval failure requires review
# =========================================================

def test_nav_retrieval_failure_after_retry_requires_review(
    monkeypatch,
):
    mock_fund_house_resolver(monkeypatch)

    async def failing_fetch(*args, **kwargs):
        raise NAVRetrievalError("Source unavailable")

    monkeypatch.setattr(
        nodes,
        "fetch_nav_history",
        failing_fetch,
    )

    state = create_initial_state()
    state["retry_count"] = 1

    result = nodes.retrieve_nav_node(state)

    assert result["next_action"] == "human_review"
    assert result["retry_count"] == 2
    assert result["human_review_required"] is True

    assert any(
        "Source unavailable" in error
        for error in result["errors"]
    )


# =========================================================
# TEST 6: Complete graph retries and generates a report
# =========================================================

def test_complete_graph_retries_and_generates_report(monkeypatch):
    mock_fund_house_resolver(monkeypatch)

    attempts = {"count": 0}

    async def fetch_with_one_failure(*args, **kwargs):
        attempts["count"] += 1

        if attempts["count"] == 1:
            raise NAVRetrievalError("Temporary failure")

        return (
            "Scheme Code;ISIN Div Payout/ISIN Growth;"
            "ISIN Div Reinvestment;Scheme Name;NAV;Date\n"
            "100;INE000A01000;INE000A01001;"
            "Example Equity Fund;100.00;16-Oct-2026\n"
        )

    monkeypatch.setattr(
        nodes,
        "fetch_nav_history",
        fetch_with_one_failure,
    )

    graph = build_graph()
    result = graph.invoke(create_initial_state())

    assert attempts["count"] == 2
    assert result["retry_count"] == 1
    assert result["human_review_required"] is False
    assert result["verification"].status == VerificationStatus.VERIFIED
    assert result["valuation"]["total_value"] == Decimal("1000.00")
    assert "Portfolio valuation" in result["report"]


# =========================================================
# TEST 7: Two retrieval failures route to human review
# =========================================================

def test_complete_graph_routes_to_review_after_two_failures(
    monkeypatch,
):
    mock_fund_house_resolver(monkeypatch)

    attempts = {"count": 0}

    async def always_failing_fetch(*args, **kwargs):
        attempts["count"] += 1
        raise NAVRetrievalError("NAV source unavailable")

    monkeypatch.setattr(
        nodes,
        "fetch_nav_history",
        always_failing_fetch,
    )

    graph = build_graph()
    result = graph.invoke(create_initial_state())

    # Confirm that both retrieval attempts occurred.
    assert attempts["count"] == 2
    assert result["retry_count"] == 2

    # Failed retrieval must not be treated as verified.
    assert result.get("verification") is None

    # No valuation is allowed after both attempts fail.
    assert result["valuation"] is None

    # The workflow must explicitly request human review.
    assert result["human_review_required"] is True
    assert "Human review required" in result["report"]

    print("\nAUDIT EVENTS AFTER NAV FAILURE:")
    for event in result.get("audit_events", []):
        print(event)

    # The failure reason must remain available.
    assert any(
        "NAV source unavailable" in error
        for error in result["errors"]
    )
    
    # Check that failure-related events are recorded.
    event_types = {
        event["event_type"]
        for event in result.get("audit_events", [])
    }

    assert "nav_retrieval_retry" in event_types
    assert "nav_retrieval_failed" in event_types
    assert "human_review_required" in event_types

    # Check that the failure event explains what happened.
    failure_events = [
        event
        for event in result["audit_events"]
        if event["event_type"] == "nav_retrieval_failed"
    ]

    assert len(failure_events) == 1
    assert "NAV retrieval failed" in failure_events[0]["details"]["reason"]

    # Check that the human-review event has a reason.
    review_events = [
        event
        for event in result["audit_events"]
        if event["event_type"] == "human_review_required"
    ]

    assert len(review_events) == 1
    assert review_events[0]["details"]["reasons"]




# =========================================================
# TEST 8: Supplied NAV records remain in the audit trail
# =========================================================

def test_supplied_nav_records_are_preserved_in_audit_trail():
    graph = build_graph()
    supplied_record = create_nav_record()

    result = graph.invoke(
        create_initial_state([supplied_record])
    )

    assert result["nav_records"] == [supplied_record]

    event_types = {
        event["event_type"]
        for event in result["audit_events"]
    }

    assert "nav_records_reused" in event_types
    assert "portfolio_validation_passed" in event_types
    assert "portfolio_verification_completed" in event_types
    assert "portfolio_valuation_completed" in event_types
    assert "report_generated" in event_types

    assert result["human_review_required"] is False


# =========================================================
# TEST 9: Successful verification is recorded
# =========================================================

def test_verification_success_is_recorded_in_audit_trail():
    state = create_initial_state()
    state["nav_records"] = [create_nav_record()]

    result = verify_nav_node(state)

    verification_events = [
        event
        for event in result["audit_events"]
        if event["event_type"] == "portfolio_verification_completed"
    ]

    assert len(verification_events) == 1

    details = verification_events[0]["details"]

    assert details["status"] == "VERIFIED"
    assert details["checks_passed"]
    assert details["checks_failed"] == []
    assert details["human_review_required"] is False


# =========================================================
# TEST 10: Failed verification is recorded in the audit trail
# =========================================================

def test_verification_failure_is_recorded_in_audit_trail():
    state = create_initial_state()
    state["nav_records"] = [
        create_nav_record(nav_date=OTHER_DATE)
    ]

    result = verify_nav_node(state)

    review_events = [
        event
        for event in result["audit_events"]
        if event["event_type"] == "verification_requires_review"
    ]

    assert len(review_events) == 1

    details = review_events[0]["details"]

    assert details["status"] == "REVIEW_REQUIRED"
    assert details["checks_failed"]
    assert details["human_review_required"] is True

    assert any(
        issue["code"] == "NAV_DATE_MISMATCH"
        for issue in details["checks_failed"]
    )


def test_complete_graph_preserves_verification_audit_event():
    state = create_initial_state()
    state["nav_records"] = [create_nav_record()]

    result = build_graph().invoke(state)

    verification_events = [
        event
        for event in result["audit_events"]
        if event["event_type"] == "portfolio_verification_completed"
    ]

    assert len(verification_events) == 1

    details = verification_events[0]["details"]
    assert details["status"] == "VERIFIED"
    assert details["checks_passed"]
    assert details["checks_failed"] == []
    assert details["human_review_required"] is False

    # A verified workflow should produce a valuation and report.
    assert result.get("valuation") is not None
    assert result.get("report")


def test_complete_graph_preserves_review_reason_in_audit():
    state = create_initial_state()
    state["nav_records"] = [
        create_nav_record(nav_date=date(2026, 10, 17))
    ]

    result = build_graph().invoke(state)

    review_events = [
        event
        for event in result["audit_events"]
        if event["event_type"] == "verification_requires_review"
    ]
    details = review_events[0]["details"]

    assert len(review_events) == 1

    details = review_events[0]["details"]
    assert details["status"] == "REVIEW_REQUIRED"
    assert details["human_review_required"] is True
    assert any(
        issue["code"] == "NAV_DATE_MISMATCH"
        for issue in details["checks_failed"]
    )

    # The workflow must not calculate a valuation from unverified NAV.
    assert result.get("valuation") is None
    assert result["human_review_required"] is True

    
def test_unrelated_fund_nav_never_produces_valuation():
    state = create_initial_state(
        [
            create_nav_record(
                scheme_name="Different Equity Fund",
            )
        ]
    )

    result = build_graph().invoke(state)

    assert result["human_review_required"] is True
    assert result["verification"].status == (
        VerificationStatus.REVIEW_REQUIRED
    )
    assert result["valuation"] is None

    assert any(
        issue.code == "NAV_NOT_FOUND"
        for issue in result["verification"].issues
    )

    assert "Human review required" in result["report"]

    
    event_types = {
        event["event_type"]
        for event in result["audit_events"]
    }

    assert "verification_requires_review" in event_types
    assert "human_review_required" in event_types
    assert "report_generated" not in event_types
    
def test_two_funds_with_different_nav_dates_block_combined_valuation():
    graph = build_graph()

    portfolio = PortfolioStatement(
        portfolio_id="TC2-P001",
        valuation_date=date(2026, 10, 22),
        holdings=[
            Holding(
                holding_id="H001",
                scheme_name="Synthetic Fund A",
                units=Decimal("10"),
            ),
            Holding(
                holding_id="H002",
                scheme_name="Synthetic Fund B",
                units=Decimal("20"),
            ),
        ],
    )

    nav_records = [
        create_nav_record(
            nav_date=date(2026, 10, 22),
            scheme_name="Synthetic Fund A",
            nav=Decimal("100"),
        ),
        create_nav_record(
            nav_date=date(2026, 10, 21),
            scheme_name="Synthetic Fund B",
            nav=Decimal("50"),
        ),
    ]

    state = create_initial_state(nav_records)
    state["portfolio"] = portfolio

    result = graph.invoke(state)

    assert result["verification"].status == (
        VerificationStatus.REVIEW_REQUIRED
    )
    assert result["human_review_required"] is True
    assert result["valuation"] is None
    assert "Human review required" in result["report"]

    assert any(
        issue.code == "NAV_DATE_MISMATCH"
        and issue.holding_id == "H002"
        for issue in result["verification"].issues
    )

    assert any(
        event["event_type"] == "verification_requires_review"
        for event in result["audit_events"]
    )
    assert any(
        event["event_type"] == "human_review_required"
        for event in result["audit_events"]
    )




