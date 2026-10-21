# FundVoiceAI

## Mutual Fund Portfolio Voice Reporter

FundVoiceAI is a project designed to help investors understand their mutual fund portfolios through portfolio valuation, Net Asset Value (NAV) retrieval and verification, and AI-powered voice reporting.

The project uses a workflow-based architecture to validate portfolio data, retrieve NAV information from the Association of Mutual Funds in India (AMFI), verify the data and supporting evidence, calculate portfolio valuation, and generate a report. When verification or processing fails, the workflow can route the result for human review rather than treating it as a confirmed report.

The voice interface, user interface, and persistent audit history are intended to build on this core workflow.

## Project Objectives

- Validate mutual fund portfolio data before processing.
- Retrieve NAV records from AMFI's NAV history data.
- Verify NAV values, dates, scheme matches, and supporting evidence.
- Calculate individual holding values and total portfolio value.
- Generate a portfolio report from verified valuation results.
- Route invalid, incomplete, or unverified results for human review.
- Provide a consistent workflow interface for application integration.
- Support future voice reporting and run-history tracking.

## Current Progress

### 1. Portfolio Data Models

Portfolio and NAV data models provide structured data for portfolio holdings and NAV records.

Portfolio validation helps prevent invalid inputs from proceeding through the valuation workflow.

### 2. NAV Retrieval

The NAV retrieval service obtains historical NAV data from AMFI's NAV history endpoint.

Current functionality includes:

- Parsing the current AMFI-style eight-column NAV format.
- Supporting the legacy six-column format.
- Matching fund schemes and NAV dates.
- Handling missing, duplicate, and invalid NAV records.
- Retaining source information and evidence for verification.

### 3. NAV Verification Engine

The verification engine checks whether portfolio data and retrieved NAV records are suitable for valuation.

Checks include:

- Portfolio and holdings validity.
- Non-negative and finite unit quantities.
- NAV availability for the required scheme and date.
- Duplicate NAV matches.
- Positive and finite NAV values.
- Supporting source URL and evidence text.

Results that cannot be verified are not treated as successfully verified valuations.

### 4. Portfolio Valuation

The valuation service calculates individual holding values using the relevant verified NAV and unit quantity.

**Holding value = Units held × NAV per unit**

The service also calculates the total portfolio value from the individual holding values and checks that NAV records match the required scheme and valuation date.

### 5. Agentic Workflow

The project uses LangGraph to coordinate the main processing stages.

The workflow follows this sequence:

1. Validate the portfolio.
2. Retrieve NAV data.
3. Verify NAV data and evidence.
4. Calculate portfolio valuation.
5. Generate the portfolio report.
6. Route cases requiring intervention to human review.

The workflow's nodes and routing logic are implemented in `app/agents/`.

### 6. Workflow Runner

The public workflow entry point is implemented in:

`app/services/workflow_runner.py`

It exposes the function:

```python
from app.services.workflow_runner import run_portfolio_report

result = run_portfolio_report(portfolio)
```

The function accepts a validated `PortfolioStatement` object and invokes the existing LangGraph workflow.

The returned dictionary includes:

- `portfolio_id`
- `status`
- `report`
- `valuation`
- `verification_status`
- `human_review_required`
- `errors`
- `audit_events`

The runner provides a consistent integration interface for the application UI. Its tests use a mocked workflow graph to verify the returned results and human-review handling.

## Workflow Architecture

```text
Portfolio Input
      |
      v
Validate Portfolio
      |
      v
Retrieve NAV
      |
      v
Verify NAV and Evidence
      |
      +---- Verification / processing issue
      |                 |
      |                 v
      |            Human Review
      |
      v
Calculate Valuation
      |
      v
Generate Report
      |
      v
Return Workflow Result
```

The diagram illustrates the intended processing flow. Actual routing depends on the workflow state and verification results.

## Automated Testing

The project includes automated tests for portfolio calculations, NAV retrieval and parsing, verification rules, valuation safeguards, and workflow behavior.

Test coverage includes:

- Portfolio valuation calculations.
- Fractional units and rounding.
- Invalid units and NAV values.
- Current and legacy NAV CSV formats.
- Missing and duplicate NAV records.
- NAV date and scheme mismatches.
- Missing verification evidence.
- Human-review routing.
- Workflow runner success and failure outcomes.

### Current Test Status

**Latest reported result: 52 automated tests passed.**

```text
52 passed
```

This result reflects the latest reported development-environment test run. The complete application still requires end-to-end testing after integration.

### Run the Tests

Activate your Python virtual environment, then run:

```bash
python -m pytest -v
```

To run the complete test suite with concise output:

```bash
python -m pytest -q
```

To run the workflow runner tests:

```bash
python -m pytest tests/test_workflow_runner.py -q
```

## Technology Stack

The current implementation uses:

- **Python** — application logic and data processing.
- **Pydantic** — structured data validation.
- **LangGraph** — workflow orchestration.
- **pytest** — automated testing.
- **httpx** — HTTP requests for NAV retrieval.

Streamlit, voice generation, and SQLite audit-history integration are planned or being developed as part of the broader application.

## Project Structure

The following are the main relevant modules:

```text
FundVoice-AI/
├── app/
│   ├── agents/
│   │   ├── graph.py
│   │   ├── nodes.py
│   │   └── state.py
│   ├── models/
│   ├── services/
│   │   ├── nav_retriever.py
│   │   ├── portfolio_valuation.py
│   │   └── workflow_runner.py
│   └── verification/
│       └── engine.py
├── tests/
│   ├── test_agent_workflow.py
│   ├── test_nav_retriever.py
│   ├── test_portfolio_calculator.py
│   ├── test_portfolio_valuation.py
│   ├── test_verification.py
│   ├── test_workflow_runner.py
│   └── test_workflow_smoke.py
├── README.md
└── INTEGRATION_CONTRACT.md
```

This is a summary of the principal files; additional modules and tests may exist in the repository.

## Application Integration Status

The core workflow and supporting tests have been implemented. The workflow runner provides an entry point for the application interface.

The following items remain subject to team integration and end-to-end verification:

- Streamlit portfolio input and report display.
- Voice playback generated from the workflow's report.
- SQLite persistence for run history and audit events.
- Complete application testing with representative portfolio data.
- Verification that unverified valuation figures are not presented as confirmed results.

## Data Reliability and Safety

FundVoiceAI is a portfolio reporting project, not a guarantee of investment performance or a recommendation to buy or sell mutual funds.

NAV data and valuation results depend on the correctness, availability, and date of the underlying records. A successful automated test suite does not by itself establish the accuracy of every live data retrieval or integrated application run.

The workflow is designed to flag verification and processing issues for human review instead of treating unsupported results as verified.

## Development Status

The core portfolio processing workflow, NAV retrieval, verification, valuation, report generation, workflow runner, and associated automated tests are implemented.

**Next milestone:** Integrate the core workflow with the user interface, voice reporting, and SQLite audit history, then validate the complete application end to end.
