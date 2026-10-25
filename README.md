# FundVoiceAI — Mutual Fund Portfolio Voice Reporter

FundVoiceAI is a Python-based project designed to help investors understand their mutual fund portfolios through portfolio valuation, Net Asset Value (NAV) verification, scenario analysis, and AI-assisted voice reporting.

The project combines portfolio calculations, NAV data retrieval, verification safeguards, and a Streamlit dashboard to make mutual fund portfolio information easier to understand.

> **Development status:** Active development. The automated test suite currently passes 94 tests. Full end-to-end validation with real portfolio data and voice playback.

## Key Features

- **Portfolio valuation:** Calculate portfolio value using mutual fund units and NAV data.
- **NAV retrieval:** Retrieve and process NAV information, including CSV parsing.
- **NAV verification:** Compare portfolio valuation inputs against available NAV data.
- **Scenario handling:** Route supported user requests through scenario calculation and handling services.
- **Safety checks:** Apply request-safety logic to supported portfolio-related workflows.
- **Dashboard:** Provide a Streamlit interface for interacting with the portfolio reporter.
- **Voice reporting:** Generate portfolio reports intended for voice-based delivery.
- **Workflow orchestration:** Organize processing through agent and workflow components.
- **Audit storage:** Provide a repository component for storing audit-related records.
- **Automated tests:** Test core calculations, verification, routing, dashboard behavior, safety logic, workflows, and voice-report components.

Feature availability and completeness may vary as development continues.

## Technology Stack

- Python
- Streamlit
- pytest
- Git and GitHub

Additional dependencies are defined by the project's dependency files, where available.

## Project Structure

```text
FundVoiceAI/
├── app/
│   ├── agents/
│   │   ├── graph.py
│   │   ├── nodes.py
│   │   ├── state.py
│   │   ├── workflow.py
│   │   └── test_workflow.py
│   ├── models/
│   │   └── portfolio.py
│   ├── services/
│   │   ├── nav_retriever.py
│   │   ├── portfolio_valuation.py
│   │   ├── request_safety.py
│   │   ├── scenario_calculations.py
│   │   ├── scenario_router.py
│   │   ├── unified_scenario_handler.py
│   │   ├── valuation_display.py
│   │   └── voice_report.py
│   ├── storage/
│   │   └── audit_repository.py
│   ├── ui/
│   │   └── dashboard.py
│   ├── verification/
│   │   └── engine.py
│   └── main.py
├── tests/
├── evidence/
├── .gitignore
├── README.md
└── requirements.txt
```

*This is a representative overview. The exact files and folders depend on the current checkout.*

## Prerequisites

Before running FundVoiceAI, install:

- Python compatible with the project's dependencies
- Git
- pip, Python's package installer

Use a virtual environment to isolate project dependencies.

## Installation

### 1. Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd FundVoiceAI
```

Replace `<YOUR_GITHUB_REPOSITORY_URL>` with the HTTPS or SSH URL of your GitHub repository.

### 2. Create a virtual environment

**Windows PowerShell:**

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use an approved environment-specific workaround or activate the environment through your IDE.

### 3. Install dependencies

If the repository contains `requirements.txt`, run:

```powershell
python -m pip install -r requirements.txt
```

If the project uses another dependency manager, follow the corresponding project configuration instead.

## Running the Application

The Streamlit dashboard is located at `app/ui/dashboard.py`.

With the virtual environment activated and dependencies installed, run:

```powershell
python -m streamlit run app/ui/dashboard.py
```

Streamlit normally prints a local URL in the terminal. Open that URL in your browser to access the dashboard.

The exact interface and available functionality depend on the current implementation and configuration.

## Running the Tests

Run the complete test suite from the project root:

```powershell
python -m pytest -v
```

For a concise summary:

```powershell
python -m pytest -q
```

### Latest verified result

```text
94 passed in 1.46s
```

This result was observed in the current development environment. Test results can differ after dependency changes or when running in another environment.

## How the Project Works

At a high level, FundVoiceAI follows this processing flow:

1. **Request input:** The user interacts with the application through its supported interface.
2. **Request handling:** Application and workflow components process the request.
3. **Portfolio modelling:** Portfolio data is represented using the project's data models.
4. **NAV retrieval:** The relevant service retrieves or parses available NAV information.
5. **Valuation:** The valuation service calculates portfolio values using supported inputs.
6. **Verification:** Verification components check the relevant portfolio and NAV information.
7. **Scenario handling:** Supported scenarios are routed to their corresponding processing components.
8. **Report generation:** The application prepares a portfolio report.
9. **Voice delivery:** The voice-report component supports the intended voice-reporting functionality.

The precise execution path depends on the request type and the current implementation. This overview describes the intended architecture rather than guaranteeing that every step has been validated end to end.

## Data and Financial Accuracy

FundVoiceAI is a development project, not a substitute for official mutual fund statements or professional financial advice.

- NAV availability and dates can affect valuation results.
- Portfolio calculations depend on the correctness of the supplied units, NAV values, and other inputs.
- Historical data and corporate actions may require additional validation.
- Missing, stale, or inconsistent data should not be treated as verified information.
- Users should independently confirm important values against official fund-house or other authoritative records.

The application should not be assumed to provide investment recommendations or guaranteed returns.

## Security and Privacy

Before uploading the repository to GitHub:

- Never commit API keys, access tokens, passwords, or credentials.
- Keep `.env` files and Streamlit secrets out of version control.
- Do not commit real investor statements, account numbers, or personally identifiable financial information.
- Use synthetic or anonymized portfolio data in examples and tests.
- Review the contents of the `evidence/` directory before publishing.
- Exclude temporary backup files and local environment directories.

A private repository is recommended during active development, but private visibility does not replace proper secret and data handling.

## Current Limitations and Future Work

Planned or pending validation areas include:

- End-to-end testing with representative portfolio data
- Verification of NAV retrieval across different dates and data sources
- Additional handling for historical corporate actions, such as unit splits, where supported data is available
- Full validation of voice playback from generated reports
- Broader error handling and data-quality checks
- Integration testing of the dashboard, workflow, valuation, and verification components
- Documentation of configuration, supported inputs, and known limitations

These items should be marked complete only after their corresponding implementation and tests have been verified.

## Development Workflow

To contribute or continue development:

1. Create a feature branch for substantial changes.
2. Make the required code changes.
3. Add or update automated tests.
4. Run `python -m pytest -q`.
5. Review the changes with `git diff`.
6. Commit the changes with a descriptive message.
7. Push the branch to GitHub and review the changes before merging.

## License

No license has been specified yet. Add a `LICENSE` file before distributing the project under an open-source license.

## Project Goal

The long-term goal of FundVoiceAI is to make mutual fund portfolio information more accessible by combining reliable portfolio calculations, NAV verification, clear reporting, and voice-based interaction.
