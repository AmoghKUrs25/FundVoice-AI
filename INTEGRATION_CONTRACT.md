# FundVoice AI — Integration Contract

## 1. Purpose

Define how the three modules communicate: agent orchestration, financial processing, and voice/UI.

## 2. Team responsibilities

- **Friend 1 — Agent orchestration:** Coordinates validation, NAV retrieval, verification, valuation, report generation, and human review.
- **Friend 2 — Financial engine:** Provides NAV retrieval, verification, and portfolio valuation services.
- **Friend 3 — Voice/UI:** Collects portfolio input and presents the report or human-review outcome.

## 3. Workflow input

The workflow accepts a `FundVoiceState` dictionary. Its primary input is:

- `portfolio`: a `PortfolioStatement`.
- `nav_records`: an optional list of `NAVRecord` objects, useful for testing or when records are already available.
- `errors`: an optional list of error messages.
- `audit_events`: an optional initial audit-event list.

## 4. Successful workflow output

On success, the result is expected to include:

- `report`: human-readable portfolio report.
- `human_review_required`: `False`.
- `next_action`: `"complete"`.
- `valuation`: structured portfolio valuation.
- `verification`: verification result.
- `errors`: error list.
- `audit_events`: workflow event history.

## 5. Human-review output

When a required check fails, the result should include:

- `human_review_required`: `True`.
- `next_action`: `"human_review"`.
- `errors`: reasons the workflow stopped.
- `audit_events`: workflow event history.

A report must not be generated when verification has not passed or valuation is missing.

## 6. Financial safety rules

- Require an exact scheme match and exact valuation-date match.
- Never silently substitute a NAV from another date.
- Require exactly one matching NAV record per holding.
- Preserve NAV evidence identifiers and source URLs in valuation output.
- Route missing, mismatched, ambiguous, or otherwise unsafe data to human review.
- Do not execute trades or provide personalized buy/sell instructions.

## 7. Testing

Run the full test suite from the repository root:

```powershell
python -m pytest -v
```

Use mocked NAV data for deterministic integration tests. Test live NAV retrieval separately.

## 8. Implementation note

This document describes the intended interface. Verify the actual fields returned by each workflow node against the implementation and tests before the UI depends on them.
