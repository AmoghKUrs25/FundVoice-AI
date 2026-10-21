# FundVoice AI — Integration Contract

## 1. Purpose

Define how the three project modules communicate: agent orchestration, financial processing, and voice/UI.

## 2. Team responsibilities

- **Friend 1 — Agent orchestration:** Coordinates portfolio validation, NAV retrieval, verification, valuation, report generation, and human-review routing.
- **Friend 2 — Financial engine:** Owns NAV retrieval, NAV parsing, verification, and portfolio valuation services.
- **Friend 3 — Voice/UI and audit storage:** Collects portfolio input, presents reports or review outcomes, and persists audit records.

## 3. Workflow entry point

Import the compiled graph from the agent workflow module:

```python
from app.agents.graph import fundvoice_graph

result = fundvoice_graph.invoke({
    "portfolio": portfolio,
    "nav_records": nav_records,  # Optional for testing or pre-fetched data
    "errors": [],
    "audit_events": [],
})
```

`portfolio` must be a valid `PortfolioStatement`. When `nav_records` is omitted, the workflow may retrieve NAV data through its configured retrieval service.

Use the actual model definitions and tests to construct valid input objects. Do not pass unvalidated raw UI input directly into the graph.

## 4. Workflow result contract

The graph returns a state dictionary. Some fields are optional because the workflow uses partial state updates.

### Successful workflow

Expected fields include:

- `report`: human-readable portfolio report.
- `human_review_required`: `False`.
- `next_action`: `"complete"`.
- `valuation`: structured portfolio valuation, including holding-level values and evidence fields.
- `verification`: verification result.
- `audit_events`: workflow event history.

### Human-review workflow

Expected fields include:

- `human_review_required`: `True`.
- `next_action`: `"human_review"`.
- `errors`: reasons the workflow stopped, when available.
- `audit_events`: workflow event history.

The UI should use safe lookups for optional fields:

```python
report = result.get("report")
needs_review = result.get("human_review_required", True)
next_action = result.get("next_action", "human_review")
errors = result.get("errors", [])
audit_events = result.get("audit_events", [])
```

Defaulting to human review when the status is missing prevents the UI from treating an incomplete result as a successful report.

## 5. Financial safety rules

- Require an exact scheme match and exact valuation-date match.
- Never silently substitute a NAV from another date.
- Require exactly one matching NAV record per holding.
- Preserve NAV evidence identifiers and source URLs in valuation output.
- Route missing, mismatched, duplicate, ambiguous, or otherwise unsafe data to human review.
- Do not generate a report unless verification passes and valuation is available.
- Do not execute trades or provide personalized buy/sell instructions.
- Verification checks consistency and evidence fields; it does not independently authenticate the NAV source.

## 6. Module interface expectations

### Friend 2 — Financial engine

Provide the agreed model and service interfaces for:

- Fetching and parsing NAV records.
- Verifying portfolio holdings against NAV records.
- Calculating holding values and total portfolio value.
- Preserving the requested valuation date and source evidence.

Use the shared models rather than creating duplicate NAV or portfolio data structures.

### Friend 3 — Voice/UI and audit storage

- Collect and validate user input before invoking the graph.
- Invoke the graph through `fundvoice_graph.invoke(...)`.
- Present the report only when the workflow has completed successfully.
- Display a clear human-review message when `human_review_required` is true or the result is incomplete.
- Persist audit events without changing financial calculations.
- Keep credentials, personal data, and sensitive information out of unnecessary logs.

## 7. Testing

Run the complete test suite from the repository root:

```powershell
python -m pytest -v
```

Use mocked NAV data for deterministic integration tests. Test live NAV retrieval separately and clearly record whether live-source testing succeeded.

## 8. Implementation note

This document defines the intended integration contract. Before relying on it, confirm that actual graph outputs, model fields, and service signatures match the contract and tests. Update this document whenever a shared interface changes.
