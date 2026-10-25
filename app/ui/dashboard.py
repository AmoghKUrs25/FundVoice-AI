from datetime import date, timezone, datetime
from decimal import Decimal, InvalidOperation
from html import escape
import json

import streamlit as st
import streamlit.components.v1 as components
from pydantic import ValidationError
from app.storage.audit_repository import AuditRepository
from app.main import run_workflow
from app.models.portfolio import Holding, PortfolioStatement
from app.services.request_safety import audit_request_safety
from app.services.unified_scenario_handler import run_scenario
from app.services.scenario_router import classify_scenario
from app.services.scenario_calculations import calculate_tc1, calculate_tc2, calculate_tc3
from app.services.valuation_display import can_display_verified_valuation
from app.services.voice_report import prepare_voice_report_from_result


# =========================================================
# 1. PAGE CONFIGURATION AND STYLING
# =========================================================

st.set_page_config(
    page_title="FundVoice AI | Portfolio Intelligence",
    page_icon="F",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');

    :root {
        --fv-primary: #087f68;
        --fv-primary-dark: #065849;
        --fv-navy: #142d3a;
        --fv-muted: #718096;
        --fv-border: #e1e9ef;
        --fv-surface: #ffffff;
    }

    .stApp {
        background:
            radial-gradient(ellipse at 0% 0%,
                rgba(8,127,104,.10), transparent 32%),
            radial-gradient(ellipse at 100% 0%,
                rgba(70,110,190,.08), transparent 28%),
            #f4f7fb;
        color: #172b3a;
        font-family: 'DM Sans', sans-serif;
    }

    .block-container {
        max-width: 1500px;
        padding-top: 1.5rem;
        padding-bottom: 3rem;
    }

    h1, h2, h3 {
        font-family: 'Manrope', sans-serif;
        color: var(--fv-navy);
        letter-spacing: -0.035em;
    }

    h1 { font-weight: 800; }
    h2 { font-weight: 750; }
    h3 { font-weight: 700; }

    [data-testid="stMetric"] {
        background: var(--fv-surface);
        border: 1px solid var(--fv-border);
        border-radius: 18px;
        padding: 1.25rem 1.3rem;
        box-shadow: 0 5px 20px rgba(25,45,65,.045);
        transition: transform .18s ease, box-shadow .18s ease;
    }

    [data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 26px rgba(25,45,65,.08);
    }

    [data-testid="stMetricLabel"] p {
        color: var(--fv-muted);
        font-size: .86rem;
        font-weight: 600;
    }

    [data-testid="stMetricValue"] {
        color: var(--fv-navy);
        font-family: 'Manrope', sans-serif;
        font-size: 1.7rem;
        font-weight: 800;
    }

    div[data-testid="stForm"] {
        background: rgba(255,255,255,.97);
        border: 1px solid var(--fv-border);
        border-radius: 18px;
        padding: 1.25rem;
        box-shadow: 0 5px 22px rgba(25,45,65,.035);
    }

    div[data-testid="stExpander"] {
        background: rgba(255,255,255,.96);
        border: 1px solid var(--fv-border);
        border-radius: 15px;
        overflow: hidden;
    }

    div.stButton > button,
    div.stFormSubmitButton > button {
        background: var(--fv-primary);
        color: #fff;
        border: 1px solid var(--fv-primary);
        border-radius: 11px;
        min-height: 2.8rem;
        padding: .55rem 1.1rem;
        font-weight: 700;
        transition: all .18s ease;
    }

    div.stButton > button:hover,
    div.stFormSubmitButton > button:hover {
        background: var(--fv-primary-dark);
        border-color: var(--fv-primary-dark);
        color: #fff;
        box-shadow: 0 5px 14px rgba(8,127,104,.17);
    }

    [data-testid="stDataFrame"] {
        border: 1px solid var(--fv-border);
        border-radius: 14px;
        overflow: hidden;
        background: #fff;
    }

    [data-testid="stAlert"] {
        border-radius: 13px;
        border: 1px solid rgba(100,120,140,.12);
    }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #142d3a 0%, #193f48 100%);
        border-right: 1px solid rgba(255,255,255,.08);
    }

    section[data-testid="stSidebar"] * {
        color: #f3f8fb;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: 1px solid #dce6ed;
    }

    .stTabs [data-baseweb="tab"] {
        height: 45px;
        padding: 0 17px;
        border-radius: 10px 10px 0 0;
        font-weight: 650;
    }

    .stTabs [aria-selected="true"] {
        color: var(--fv-primary);
    }

    div[data-baseweb="input"],
    div[data-baseweb="select"] > div,
    div[data-baseweb="textarea"] {
        border-radius: 10px;
    }

    hr {
        border-color: #e1e9ef;
        margin-top: 1.5rem;
        margin-bottom: 1.5rem;
    }

    @media (max-width: 768px) {
        .block-container {
            padding: 1rem .8rem 2rem;
        }

        [data-testid="stMetric"] {
            padding: .85rem;
        }

        [data-testid="stMetricValue"] {
            font-size: 1.3rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# 2. DASHBOARD HEADER - SAFE STREAMLIT VERSION
# =========================================================
# 2. DASHBOARD HEADER - SAFE STREAMLIT VERSION
# =========================================================

st.markdown(
    """
    <style>
    .fundvoice-hero {
        background: linear-gradient(120deg, #142d3a, #155d52);
        padding: 2rem;
        border-radius: 22px;
        margin-bottom: 1.2rem;
        box-shadow: 0 12px 30px rgba(20, 45, 58, 0.12);
    }

    .fundvoice-eyebrow {
        color: #a7e7d1;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.16em;
        text-transform: uppercase;
    }

    .fundvoice-title {
        color: #ffffff !important;
        font-size: 2.5rem !important;
        font-weight: 800 !important;
        margin: 0.45rem 0 !important;
    }

    .fundvoice-subtitle {
        color: #e0efeb;
        font-size: 1.05rem;
        margin: 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.container():
    st.markdown(
        """
        <div class="fundvoice-hero">
            <div class="fundvoice-eyebrow">PORTFOLIO INTELLIGENCE</div>
            <h1 class="fundvoice-title">FundVoice AI</h1>
            <p class="fundvoice-subtitle">
                Your mutual fund portfolio, verified and explained aloud.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.caption(
    "Evidence-first reporting | Dated NAV verification | Safe voice summaries"
)


if "fundvoice_execution" not in st.session_state:
    st.session_state["fundvoice_execution"] = None

    
# =========================================================
# 5. PORTFOLIO INPUT
# =========================================================

st.header('Portfolio Input')

st.info(
    "Enter the exact mutual fund scheme names and units. "
    "A valuation is presented as verified only when the workflow's "
    "verification checks pass."
)

display_mode = st.radio(
    "Choose mode",
    ["Normal Portfolio Mode", "Demo/Test Mode"],
    horizontal=True,
    key="dashboard_mode",
)

if display_mode == "Demo/Test Mode":
    with st.expander("Test Cases (TC1-TC4)", expanded=False):
        st.caption(
            "Demonstration data only. These values do not represent "
            "live NAV evidence or a verified portfolio valuation."
        )

        st.markdown("**TC1 - Units x NAV**")
        tc1_units = st.number_input(
            "TC1 units", min_value=0.0, value=10.0,
            key="unified_tc1_units",
        )
        tc1_nav = st.number_input(
            "TC1 NAV per unit", min_value=0.0, value=100.0,
            key="unified_tc1_nav",
        )

        st.markdown("**TC2 - Different NAV Dates**")
        st.caption(
            "Different dates must not be combined into a "
            "single verified portfolio valuation."
        )
        tc2_a_units = st.number_input(
            "TC2 Fund A units", min_value=0.0, value=10.0,
            key="unified_tc2_a_units",
        )
        tc2_a_nav = st.number_input(
            "TC2 Fund A NAV", min_value=0.0, value=100.0,
            key="unified_tc2_a_nav",
        )
        tc2_a_date = st.date_input(
            "TC2 Fund A NAV date", value=date(2026, 10, 22),
            key="unified_tc2_a_date",
        )
        tc2_b_units = st.number_input(
            "TC2 Fund B units", min_value=0.0, value=20.0,
            key="unified_tc2_b_units",
        )
        tc2_b_nav = st.number_input(
            "TC2 Fund B NAV", min_value=0.0, value=50.0,
            key="unified_tc2_b_nav",
        )
        tc2_b_date = st.date_input(
            "TC2 Fund B NAV date", value=date(2026, 10, 21),
            key="unified_tc2_b_date",
        )

        st.markdown("**TC3 - Before and After Unit Split**")
        tc3_before_units = st.number_input(
            "TC3 units before split", min_value=0.0, value=10.0,
            key="unified_tc3_before_units",
        )
        tc3_before_nav = st.number_input(
            "TC3 NAV before split", min_value=0.0, value=100.0,
            key="unified_tc3_before_nav",
        )
        tc3_after_units = st.number_input(
            "TC3 units after split", min_value=0.0, value=20.0,
            key="unified_tc3_after_units",
        )
        tc3_after_nav = st.number_input(
            "TC3 NAV after split", min_value=0.0, value=50.0,
            key="unified_tc3_after_nav",
        )

with st.form("portfolio_input_form"):
    scenario_request = st.text_input(
        "Request or scenario (optional)",
        placeholder=(
            "Calculate holding value: units x NAV / "
            "Different NAV dates for two funds / "
            "Before split and after split / Sell this fund"
        ),
        help="Leave blank to run normal live portfolio analysis.",
    ).strip()

    portfolio_id = st.text_input(
        "Portfolio ID",
        value="PORT-001",
        help="A unique identifier for this portfolio.",
    ).strip()

    valuation_date = st.date_input(
        "Valuation date",
        value=date.today(),
        help="NAV must be available for this exact date.",
    )

    holding_count = st.number_input(
        "Number of mutual fund holdings",
        min_value=1,
        max_value=20,
        value=1,
        step=1,
    )

    holding_inputs = []

    for index in range(int(holding_count)):
        st.markdown(f"#### Holding {index + 1}")

        scheme_name = st.text_input(
            "Exact mutual fund scheme name",
            key=f"scheme_name_{index}",
            placeholder="Enter the full scheme name",
        ).strip()

        plan_choice = st.selectbox(
            "Plan",
            ["Not specified", "Direct", "Regular"],
            key=f"plan_{index}",
            help="Select this from your holding statement.",
        )

        option_choice = st.selectbox(
            "Option",
            ["Not specified", "Growth", "IDCW"],
            key=f"option_{index}",
            help="Select this from your holding statement.",
        )

        units_text = st.text_input(
            "Units held",
            key=f"units_{index}",
            placeholder="Example: 125.500",
        ).strip()

        holding_inputs.append(
            (
                scheme_name,
                units_text,
                None if plan_choice == "Not specified" else plan_choice,
                None if option_choice == "Not specified" else option_choice,
            )
        )

    submitted = st.form_submit_button(
        "Run Portfolio Analysis",
        type="primary",
        use_container_width=True,
    )


# =========================================================
# 6. VALIDATE INPUT AND RUN WORKFLOW
# =========================================================

if submitted:
    if scenario_request:
        try:
            from app.services.scenario_router import classify_scenario

            classification = classify_scenario(scenario_request)
            scenario_name = classification["scenario"]

            # TC4 must always pass through the safety audit handler.
            if scenario_name == "TC4":
                routed = run_scenario(scenario_request, {})
                scenario_result = routed["result"]
                st.warning("Request rejected or out of scope.")
                st.write("**Scenario:** TC4 - Request Safety")
                st.write("**Status:**", scenario_result["status"])
                st.write("**Reason:**", scenario_result["reason"])
                st.write("**Action:**", scenario_result["action"])
                st.write(
                    "**Trade executed by FundVoice:**",
                    scenario_result["trade_executed"],
                )
                st.write("**Audit saved:**", scenario_result["audit_saved"])
                st.caption(f"Audit run ID: {scenario_result['run_id']}")
                st.stop()

            # Synthetic test inputs are used only in Demo/Test Mode.
            if (
                scenario_name in ("TC1", "TC2", "TC3")
                and display_mode == "Demo/Test Mode"
            ):
                scenario_data = {}

                if scenario_name == "TC1":
                    scenario_data = {
                        "units": tc1_units,
                        "nav": tc1_nav,
                    }
                elif scenario_name == "TC2":
                    scenario_data = {
                        "holdings": [
                            {
                                "name": "Synthetic Fund A",
                                "units": tc2_a_units,
                                "nav": tc2_a_nav,
                                "nav_date": tc2_a_date.isoformat(),
                            },
                            {
                                "name": "Synthetic Fund B",
                                "units": tc2_b_units,
                                "nav": tc2_b_nav,
                                "nav_date": tc2_b_date.isoformat(),
                            },
                        ]
                    }
                elif scenario_name == "TC3":
                    scenario_data = {
                        "before_units": tc3_before_units,
                        "before_nav": tc3_before_nav,
                        "after_units": tc3_after_units,
                        "after_nav": tc3_after_nav,
                    }

                routed = run_scenario(scenario_request, scenario_data)
                scenario_result = routed["result"]

                st.subheader(f"{scenario_name} - Synthetic Scenario Result")
                st.caption(
                    "Synthetic demonstration only; this is not a verified "
                    "live portfolio valuation."
                )

                if scenario_result is None:
                    st.warning(classification["reason"])
                    st.stop()

                if scenario_name == "TC1":
                    st.write("**Calculation:**", scenario_result["calculation"])
                    st.metric(
                        "Holding value",
                        f'INR {Decimal(str(scenario_result["holding_value"])):,.2f}',
                    )
                elif scenario_name == "TC2":
                    st.dataframe(
                        [
                            {
                                "Holding": item["holding"],
                                "Units": item["units"],
                                "NAV": item["nav"],
                                "NAV Date": item["nav_date"],
                                "Holding Value": item["holding_value"],
                            }
                            for item in scenario_result["holdings"]
                        ],
                        use_container_width=True,
                        hide_index=True,
                    )
                    if scenario_result["dates_differ"]:
                        st.warning(
                            "REVIEW REQUIRED: different NAV dates must not be "
                            "combined into a verified portfolio valuation."
                        )
                    st.write("A verified portfolio value is not available.")
                elif scenario_name == "TC3":
                    st.write("**Value before split:**", scenario_result["before_value"])
                    st.write("**Value after split:**", scenario_result["after_value"])
                    st.write("**Difference:**", scenario_result["difference"])
                    if scenario_result["values_match"]:
                        st.success("Values match; no arithmetic loss is shown.")
                    else:
                        st.warning(scenario_result["interpretation"])
                st.stop()

            # Normal Mode TC1-TC3 fall through to the real portfolio workflow.
            if scenario_name in ("TC1", "TC2", "TC3"):
                st.session_state["fundvoice_scenario_name"] = scenario_name
            else:
                st.session_state["fundvoice_scenario_name"] = None

        except (ValueError, KeyError) as exc:
            st.error(f"Scenario could not be processed: {exc}")
            st.stop()
    try:
        if not portfolio_id:
            raise ValueError("Portfolio ID cannot be blank.")

        holdings = []

        for index, (scheme_name, units_text, plan, option) in enumerate(
            holding_inputs,
            start=1,
        ):
            if not scheme_name:
                raise ValueError(
                    f"Holding {index}: scheme name cannot be blank."
                )

            if not units_text:
                raise ValueError(
                    f"Holding {index}: units cannot be blank."
                )

            try:
                units = Decimal(units_text)
            except InvalidOperation as exc:
                raise ValueError(
                    f"Holding {index}: enter units as a valid number."
                ) from exc

            if not units.is_finite() or units < 0:
                raise ValueError(
                    f"Holding {index}: units must be a finite, "
                    "non-negative number."
                )

            holdings.append(
                Holding(
                    holding_id=f"H{index:03d}",
                    scheme_name=scheme_name,
                    units=units,
                    plan=plan,
                    option=option,
                )
            )

        portfolio = PortfolioStatement(
            portfolio_id=portfolio_id,
            valuation_date=valuation_date,
            holdings=holdings,
        )

        workflow_state = {
            "portfolio": portfolio,
            "nav_records": [],
            "audit_events": [],
            "errors": [],
            "retry_count": 0,
            "human_review_required": False,
        }

        with st.spinner(
            "Retrieving NAV evidence and running verification..."
        ):
            execution = run_workflow(state=workflow_state)

        st.session_state["fundvoice_execution"] = execution

    except (ValueError, ValidationError) as exc:
        st.error(f"Please correct the portfolio input: {exc}")

    except Exception as exc:
        st.error(f"Portfolio analysis could not be completed: {exc}")


# =========================================================
# 7. LOAD WORKFLOW RESULTS
# =========================================================

execution = st.session_state["fundvoice_execution"]

if execution is None:
    st.caption("Submit your portfolio above to start the analysis.")
    st.stop()

result = execution["result"]

st.divider()
st.header('Portfolio Dashboard')

verification = result.get("verification")
verification_status = None

if verification is not None:
    verification_status = getattr(
        verification.status,
        "value",
        verification.status,
    )

human_review_required = result.get("human_review_required", False)
valuation = result.get("valuation")

verified = can_display_verified_valuation(
    valuation=valuation,
    verification_status=verification_status,
    human_review_required=human_review_required,
)

# Explain normal-mode TC1-TC3 using actual evidence.
normal_scenario = st.session_state.get("fundvoice_scenario_name")
if normal_scenario in ("TC1", "TC2", "TC3"):
    st.subheader(f"{normal_scenario} - Portfolio Evidence Review")
    scenario_nav_records = result.get("nav_records", [])

    if normal_scenario == "TC1":
        if verified:
            st.success("The real portfolio workflow verified this valuation. See the holding-wise evidence below.")
        else:
            st.warning("A verified holding value is unavailable. Review the actual dated NAV observations below. Synthetic test values were not used.")

    elif normal_scenario == "TC2":
        if len(scenario_nav_records) < len(result["portfolio"].holdings):
            st.warning("Insufficient retrieved NAV records to compare every holding date. No mixed-date verified total is asserted.")
        else:
            scenario_dates = {str(record.nav_date) for record in scenario_nav_records}
            if len(scenario_dates) > 1:
                st.warning("Actual retrieved NAV records contain different dates. Do not combine these observations into a verified valuation.")
                st.write("**Observed NAV dates:**", ", ".join(sorted(scenario_dates)))
            else:
                st.info("The retrieved NAV records do not show differing dates. The workflow verification status still controls whether a total is verified.")

    elif normal_scenario == "TC3":
        st.warning("The current portfolio model does not store unit-split history. A split cannot be confirmed from the current inputs alone; no synthetic split values were used.")


if verified:
    total_value = Decimal(str(valuation["total_value"]))
else:
    total_value = Decimal("0")

metric_cols = st.columns(4)

metric_cols[0].metric(
    "Portfolio Holdings",
    len(result["portfolio"].holdings),
)

metric_cols[1].metric(
    "Verification Status",
    str(verification_status or "Pending").replace("_", " ").title(),
)

metric_cols[2].metric(
    "Valuation Date",
    result["portfolio"].valuation_date.strftime("%d %b %Y"),
)

metric_cols[3].metric(
    "Review Status",
    "Review Needed" if human_review_required or not verified else "Verified",
)

st.write(f"**Run ID:** `{execution['run_id']}`")
st.write(f"**Portfolio ID:** {result['portfolio'].portfolio_id}")

if verified:
    st.success(
        "Verification passed. The workflow permits a verified valuation."
    )
    st.metric(
        "Verified portfolio value",
        f"INR {total_value:,.2f}",
    )
else:
    st.warning(
        "A verified portfolio value is not available. "
        "Do not rely on an unverified valuation."
    )

    # =========================================================
# 8. NAV OBSERVATIONS WHEN VERIFICATION IS INCOMPLETE
# =========================================================

if not verified:
    nav_records = result.get("nav_records", [])

    if nav_records:
        st.subheader("Dated NAV Observations")

        st.caption(
            "These observations are informational only. NAVs from different "
            "dates must not be combined into a verified valuation."
        )

        nav_rows = []

        for holding in result["portfolio"].holdings:
            matching_records = [
                record
                for record in nav_records
                if record.scheme_name.strip().casefold()
                == holding.scheme_name.strip().casefold()
            ]

            if not matching_records:
                nav_rows.append(
                    {
                        "Scheme Name": holding.scheme_name,
                        "Units Held": str(holding.units),
                        "NAV": "Unavailable",
                        "NAV Date": "Unavailable",
                        "Evidence ID": "Unavailable",
                        "Source URL": "Unavailable",
                        "Retrieved At (UTC)": "Unavailable",
                    }
                )
                continue

            for record in matching_records:
                retrieved_at = record.evidence.retrieved_at

                # Normalize the timestamp for consistent UTC display.
                if retrieved_at.tzinfo is None:
                    retrieved_at = retrieved_at.replace(
                        tzinfo=timezone.utc
                    )
                else:
                    retrieved_at = retrieved_at.astimezone(
                        timezone.utc
                    )

                nav_rows.append(
                    {
                        "Scheme Name": holding.scheme_name,
                        "Units Held": str(holding.units),
                        "NAV": str(record.nav),
                        "NAV Date": str(record.nav_date),
                        "Evidence ID": record.evidence.evidence_id,
                        "Source URL": record.evidence.source_url,
                        "Retrieved At (UTC)": retrieved_at.isoformat(),
                    }
                )

        st.dataframe(
            nav_rows,
            use_container_width=True,
            hide_index=True,
        )


# =========================================================
# 9. HOLDING-WISE VALUATION AND DONUT CHART
# =========================================================

if verified:
    nav_records = result.get("nav_records", [])

    nav_by_scheme = {
        record.scheme_name.strip().casefold(): record
        for record in nav_records
    }

    breakdown_rows = []
    breakdown_total = Decimal("0")

    for holding in result["portfolio"].holdings:
        scheme_key = holding.scheme_name.strip().casefold()
        nav_record = nav_by_scheme.get(scheme_key)

        if nav_record is None:
            st.warning(
                f"NAV record not found for {holding.scheme_name}. "
                "Its individual valuation cannot be displayed."
            )
            continue

        if nav_record.nav_date != result["portfolio"].valuation_date:
            st.warning(
                f"NAV date mismatch for {holding.scheme_name}. "
                "Its individual valuation cannot be displayed."
            )
            continue

        units = Decimal(str(holding.units))
        nav = Decimal(str(nav_record.nav))

        current_value = (units * nav).quantize(Decimal("0.01"))

        allocation_pct = (
            current_value / total_value * Decimal("100")
        ).quantize(Decimal("0.01")) if total_value > 0 else Decimal("0.00")

        breakdown_rows.append(
            {
                "Scheme Name": holding.scheme_name,
                "Units Held": float(units),
                "NAV (INR)": float(nav),
                "Current Value (INR)": float(current_value),
                "Allocation (%)": float(allocation_pct),
            }
        )

        breakdown_total += current_value

    if breakdown_rows:
        st.subheader('Holding-wise Valuation Breakdown')

        st.dataframe(
            breakdown_rows,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Scheme Name": st.column_config.TextColumn("Scheme Name"),
                "Units Held": st.column_config.NumberColumn(
                    "Units Held",
                    format="%.4f",
                ),
                "NAV (INR)": st.column_config.NumberColumn(
                    "NAV (INR)",
                    format="%.4f",
                ),
                "Current Value (INR)": st.column_config.NumberColumn(
                    "Current Value (INR)",
                    format="%.2f",
                ),
                "Allocation (%)": st.column_config.NumberColumn(
                    "Allocation (%)",
                    format="%.2f%%",
                ),
            },
        )

        st.caption(
            "Individual values are calculated as units held x verified NAV, "
            "rounded to two decimal places."
        )

        chart_colors = [
            "#087f68", "#4776c5", "#e5a34d", "#8a6bd1",
            "#d96b79", "#3b9bb4", "#7b9b48", "#cf7f42",
            "#54717d", "#a65f9e", "#5e8fca", "#bd9952",
            "#4d9a82", "#a66b52", "#6675a8", "#bd6670",
            "#5c9eaa", "#8c8c55", "#8870a8", "#4d7f6c",
        ]

        chart_total = sum(
            (
                Decimal(str(row["Current Value (INR)"]))
                for row in breakdown_rows
            ),
            Decimal("0"),
        )

        if chart_total > 0:
            gradient_parts = []
            legend_parts = []
            angle = Decimal("0")

            for index, row in enumerate(breakdown_rows):
                value = Decimal(str(row["Current Value (INR)"]))
                sweep = value / chart_total * Decimal("360")
                color = chart_colors[index % len(chart_colors)]
                next_angle = angle + sweep

                gradient_parts.append(
                    f"{color} {float(angle):.3f}deg "
                    f"{float(next_angle):.3f}deg"
                )

                percentage = value / chart_total * Decimal("100")

                legend_parts.append(
                    "<div style='display:flex;align-items:center;gap:9px;"
                    "margin:9px 0;font-size:13px;color:#30495a;'>"
                    f"<span style='width:10px;height:10px;flex:0 0 10px;"
                    f"border-radius:3px;background:{color};"
                    "display:inline-block;'></span>"
                    "<span style='flex:1;min-width:0;overflow-wrap:anywhere;'>"
                    f"{escape(str(row['Scheme Name']))}</span>"
                    f"<strong style='white-space:nowrap;'>"
                    f"{percentage:.1f}%</strong>"
                    "</div>"
                )

                angle = next_angle

            st.subheader('Portfolio Allocation')

            chart_col, legend_col = st.columns([1, 1.35])

            with chart_col:
                st.markdown(
                    "<div style='display:flex;justify-content:center;padding:12px;'>"
                    "<div role='img' aria-label='Portfolio allocation donut chart' "
                    f"style='width:230px;height:230px;border-radius:50%;"
                    f"background:conic-gradient({', '.join(gradient_parts)});"
                    "display:flex;align-items:center;justify-content:center;"
                    "box-shadow:0 12px 28px rgba(21,48,59,.12);'>"
                    "<div style='width:142px;height:142px;border-radius:50%;"
                    "background:#fff;display:flex;flex-direction:column;"
                    "align-items:center;justify-content:center;"
                    "border:1px solid #e0eae7;'>"
                    "<span style='font-size:11px;color:#607486;'>"
                    "VERIFIED VALUE</span>"
                    f"<strong style='font-size:20px;color:#142d3a;'>"
                    f"INR {total_value:,.0f}</strong>"
                    f"<span style='font-size:11px;color:#607486;'>"
                    f"{len(breakdown_rows)} holdings</span>"
                    "</div></div></div>",
                    unsafe_allow_html=True,
                )

            with legend_col:
                st.markdown(
                    "<div style='background:rgba(255,255,255,.82);"
                    "border:1px solid #e0eae7;border-radius:16px;"
                    "padding:12px 16px;'>"
                    + "".join(legend_parts)
                    + "</div>",
                    unsafe_allow_html=True,
                )

        if breakdown_total != total_value:
            st.warning(
                "The sum of displayed holding values differs from the "
                "verified portfolio total. Check the holding records."
            )


# =========================================================
# 10. AUDIT TRAIL AND EVIDENCE
# =========================================================

# =========================================================
# 10. AUDIT TRAIL AND EVIDENCE
# =========================================================

st.divider()
st.header('Audit Trail & Evidence')

st.caption(
    "Review workflow events and persistent verification records "
    "stored in the FundVoice AI SQLite audit database."
)

# Show in-memory workflow events.
with st.expander("View current workflow audit events", expanded=False):
    workflow_events = result.get("audit_events", [])

    if workflow_events:
        for event in workflow_events:
            st.write(
                f"**{event.get('event_type', 'Event')}** - "
                f"{event.get('timestamp', '')}"
            )
            st.json(event.get("details", {}))
    else:
        st.info("No in-memory audit events are available.")

# Read persisted events from SQLite.
with st.expander("View persistent SQLite audit history", expanded=True):
    try:
        repository = AuditRepository()

        # The current workflow state does not pass run_id into its nodes.
        # Verification events therefore fall back to the portfolio ID.
        portfolio_audit_id = str(result["portfolio"].portfolio_id)

        execution_run_id = str(execution.get("run_id", ""))

        persisted_events = []

        # Read events saved under the workflow run ID, if any.
        if execution_run_id:
            persisted_events.extend(
                repository.get_events(execution_run_id)
            )

        # Also read verification events saved using the portfolio ID.
        if portfolio_audit_id != execution_run_id:
            persisted_events.extend(
                repository.get_events(portfolio_audit_id)
            )

        # Deduplicate events by SQLite primary key.
        unique_events = {
            event["id"]: event
            for event in persisted_events
        }
        persisted_events = list(unique_events.values())
        persisted_events.sort(key=lambda event: event["id"])

        st.metric("Persistent audit events", len(persisted_events))

        if persisted_events:
            audit_rows = []

            for event in persisted_events:
                details = event.get("details", {})

                audit_rows.append(
                    {
                        "Database ID": event["id"],
                        "Run / Portfolio ID": event["run_id"],
                        "Event Type": event["event_type"],
                        "Timestamp": event["timestamp"],
                        "Portfolio ID": details.get("portfolio_id", ""),
                        "Verification Status": details.get(
                            "verification_status",
                            details.get("status", ""),
                        ),
                    }
                )

            st.dataframe(
                audit_rows,
                use_container_width=True,
                hide_index=True,
            )

            for event in persisted_events:
                with st.expander(
                    f"Event #{event['id']} - {event['event_type']}"
                ):
                    st.write(f"**Run ID:** {event['run_id']}")
                    st.write(f"**Timestamp:** {event['timestamp']}")
                    st.json(event.get("details", {}))

        else:
            st.info(
                "No persistent audit events were found for this run "
                "or portfolio. Run the portfolio workflow first."
            )

    except Exception as exc:
        st.error(
            "Could not read the persistent audit history from SQLite."
        )
        st.caption(f"Diagnostic details: {exc}")

# Submitted holdings.
with st.expander("View submitted holdings"):
    for holding in result["portfolio"].holdings:
        st.write(
            f"**{holding.scheme_name}** - {holding.units} units"
        )

# Workflow errors and verification issues.
with st.expander("View workflow errors and review reasons"):
    errors = result.get("errors", [])

    if errors:
        for error in errors:
            st.write(f"- {error}")
    else:
        st.write("No workflow errors were reported.")

    if verification is not None:
        for issue in verification.issues:
            st.write(f"- {issue.code}: {issue.message}")

# NAV evidence from the current workflow result.
with st.expander("View NAV evidence metadata"):
    nav_records = result.get("nav_records", [])

    if nav_records:
        evidence_rows = []

        for record in nav_records:
            evidence = record.evidence
            retrieved_at = getattr(evidence, "retrieved_at", None)

            if isinstance(retrieved_at, datetime):
                if retrieved_at.tzinfo is None:
                    retrieved_at = retrieved_at.replace(
                        tzinfo=timezone.utc
                    )
                else:
                    retrieved_at = retrieved_at.astimezone(
                        timezone.utc
                    )

                retrieved_at_text = retrieved_at.isoformat()
            else:
                retrieved_at_text = "Unavailable"

            evidence_rows.append(
                {
                    "Scheme Name": record.scheme_name,
                    "NAV": str(record.nav),
                    "NAV Date": record.nav_date.isoformat(),
                    "Evidence ID": evidence.evidence_id,
                    "Source URL": evidence.source_url,
                    "Retrieved At (UTC)": retrieved_at_text,
                }
            )

        st.dataframe(
            evidence_rows,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No NAV records are available for this workflow.")

# =========================================================
# 11. HUMAN REVIEW CHECKLIST
# =========================================================

st.divider()
st.header('Human Review & Evidence Checklist')

st.caption(
    "Record a manual review of the submitted information. "
    "This checklist does not change verification status or approve a trade."
)

review_key = f"fundvoice_review_{execution['run_id']}"

if review_key not in st.session_state:
    st.session_state[review_key] = False

with st.container(border=True):
    st.markdown("**Before relying on this report, confirm:**")

    review_scheme = st.checkbox(
        "Scheme names match the submitted statement",
        key=f"review_scheme_{execution['run_id']}",
    )

    review_units = st.checkbox(
        "Units held match the submitted statement",
        key=f"review_units_{execution['run_id']}",
    )

    review_date = st.checkbox(
        "NAV dates match the requested valuation date",
        key=f"review_date_{execution['run_id']}",
    )

    review_evidence = st.checkbox(
        "Source evidence and evidence IDs have been inspected",
        key=f"review_evidence_{execution['run_id']}",
    )

    if st.button(
        "Record Checklist Review",
        key=f"record_review_{execution['run_id']}",
    ):
        if all(
            [
                review_scheme,
                review_units,
                review_date,
                review_evidence,
            ]
        ):
            st.session_state[review_key] = True
            st.success("Checklist recorded for this dashboard session.")
        else:
            st.warning(
                "Complete all checklist items before recording the review."
            )

    if st.session_state[review_key]:
        st.success("Manual checklist recorded in this session.")
    else:
        st.info("Manual checklist has not been recorded for this run.")

    if human_review_required or not verified:
        st.warning(
            "This checklist cannot override a REVIEW_REQUIRED or FAILED result. "
            "Resolve the workflow's verification issues first."
        )


# =========================================================
# 12. PORTFOLIO REPORT
# =========================================================

st.divider()
st.header('Portfolio Report')

report_text = result.get("report")

if human_review_required:
    st.warning(
        "Human review is required. The normal valuation report must not "
        "be used as a confirmed valuation."
    )

if report_text:
    st.text_area(
        "Generated report",
        value=report_text,
        height=200,
        disabled=True,
    )
else:
    st.info("The workflow did not generate a report.")

safe_speech_text = prepare_voice_report_from_result(result)

st.caption("Speech preview")
st.write(safe_speech_text)


# =========================================================
# 13. BROWSER VOICE PLAYBACK
# =========================================================

st.divider()
st.header('Voice Playback')

speech_json = json.dumps(safe_speech_text).replace("<", "\\u003c")

components.html(
    f"""
    <div style="font-family:sans-serif;padding:12px;
                background:#ffffff;border:1px solid #dce9e5;
                border-radius:14px;color:#142d3a;">

      <div style="margin-bottom:12px;">
        <label for="voice-select">Voice</label>
        <select id="voice-select"
                style="margin-left:8px;max-width:100%;">
          <option value="">Loading available voices...</option>
        </select>
      </div>

      <div style="margin-bottom:12px;">
        <label for="speech-rate">Speech speed</label>
        <input id="speech-rate" type="range"
               min="0.7" max="1.2" step="0.1" value="0.9"/>
        <span id="rate-value">0.9x</span>
      </div>

      <button onclick="playReport()">Play</button>
      <button onclick="pauseReport()">Pause / Resume</button>
      <button onclick="stopReport()">Stop</button>

      <p id="voice-status" aria-live="polite">Ready to speak.</p>

      <script>
        const reportText = {speech_json};
        const voiceSelect = document.getElementById("voice-select");
        const rateInput = document.getElementById("speech-rate");
        const rateValue = document.getElementById("rate-value");
        const status = document.getElementById("voice-status");

        let availableVoices = [];
        let paused = false;

        rateInput.addEventListener("input", () => {{
          rateValue.textContent = rateInput.value + "x";
        }});

        function loadVoices() {{
          if (!("speechSynthesis" in window)) {{
            voiceSelect.innerHTML =
              '<option value="">Speech unavailable</option>';
            status.textContent =
              "Speech playback is not supported in this browser.";
            return;
          }}

          availableVoices = window.speechSynthesis.getVoices();
          voiceSelect.innerHTML = "";

          if (availableVoices.length === 0) {{
            const option = document.createElement("option");
            option.value = "";
            option.textContent = "Use browser default voice";
            voiceSelect.appendChild(option);
            return;
          }}

          availableVoices.forEach((voice, index) => {{
            const option = document.createElement("option");
            option.value = String(index);
            option.textContent = voice.name + " (" + voice.lang + ")";

            if (
              voice.lang.toLowerCase() === "en-in" &&
              !voiceSelect.dataset.userSelected
            ) {{
              option.selected = true;
            }}

            voiceSelect.appendChild(option);
          }});
        }}

        voiceSelect.addEventListener("change", () => {{
          voiceSelect.dataset.userSelected = "true";
        }});

        if ("speechSynthesis" in window) {{
          loadVoices();
          window.speechSynthesis.addEventListener(
            "voiceschanged",
            loadVoices
          );
        }} else {{
          loadVoices();
        }}

        function playReport() {{
          if (!("speechSynthesis" in window)) {{
            status.textContent =
              "Speech playback is not supported in this browser.";
            return;
          }}

          window.speechSynthesis.cancel();

          const utterance = new SpeechSynthesisUtterance(reportText);
          utterance.lang = "en-IN";
          utterance.rate = Number(rateInput.value);

          const selectedIndex = voiceSelect.value;

          if (
            selectedIndex !== "" &&
            availableVoices[Number(selectedIndex)]
          ) {{
            utterance.voice = availableVoices[Number(selectedIndex)];
          }}

          utterance.onstart = () => {{
            status.textContent = "Speaking...";
          }};

          utterance.onend = () => {{
            status.textContent = "Playback finished.";
            paused = false;
          }};

          utterance.onerror = (event) => {{
            status.textContent =
              event.error === "canceled"
                ? "Playback stopped."
                : "Playback could not be completed.";
            paused = false;
          }};

          paused = false;
          window.speechSynthesis.speak(utterance);
        }}

        function pauseReport() {{
          if (!("speechSynthesis" in window)) return;

          if (window.speechSynthesis.speaking && !paused) {{
            window.speechSynthesis.pause();
            paused = true;
            status.textContent = "Paused.";
          }} else if (paused) {{
            window.speechSynthesis.resume();
            paused = false;
            status.textContent = "Speaking...";
          }}
        }}

        function stopReport() {{
          if ("speechSynthesis" in window) {{
            window.speechSynthesis.cancel();
          }}

          paused = false;
          status.textContent = "Stopped.";
        }}
      </script>
    </div>
    """,
    height=240,
)

st.caption(
    "Voice playback uses the voices available in your browser or operating "
    "system. Voice options vary by device."
)
