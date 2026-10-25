
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import NamedTuple
from uuid import uuid4

import httpx

from app.models.nav import NAVEvidence, NAVRecord


# AMFI historical NAV endpoint.
AMFI_NAV_URL = (
    "https://portal.amfiindia.com/"
    "DownloadNAVHistoryReport_Po.aspx"
)

# Supported fund houses. Add more only after verifying their IDs.
AMFI_FUND_HOUSES = {
    "hdfc": "9",
    "icici prudential": "20",
}

# Explicit aliases for official scheme-name changes.
SCHEME_NAME_ALIASES = {
    "icici prudential bluechip fund":
        "icici prudential large cap fund (erstwhile bluechip fund)",
}


class NAVRetrievalError(Exception):
    """Raised when NAV information cannot be retrieved safely."""


class NAVFetchResult(NamedTuple):
    """NAV response and metadata captured during retrieval."""

    text: str
    source_url: str
    retrieved_at: datetime


def get_fund_house_id(scheme_name: str) -> str:
    """Resolve a supported scheme name to its AMFI fund-house ID."""

    name = scheme_name.strip().casefold()

    matches = [
        (prefix, fund_id)
        for prefix, fund_id in AMFI_FUND_HOUSES.items()
        if name.startswith(prefix)
    ]

    if len(matches) != 1:
        raise NAVRetrievalError(
            f"Could not confidently identify the AMFI fund house "
            f"for scheme: {scheme_name!r}. Human review is required."
        )

    return matches[0][1]


def _normalize_scheme_name(value: str) -> str:
    """Normalize whitespace, case, and explicitly known aliases."""

    normalized = " ".join(value.strip().casefold().split())
    return SCHEME_NAME_ALIASES.get(normalized, normalized)


def _normalize_option(value: str) -> str:
    """Treat 'Growth' and 'Growth Option' as equivalent."""

    normalized = " ".join(value.strip().casefold().split())

    if normalized.endswith(" option"):
        normalized = normalized[:-len(" option")].strip()

    return normalized


def _parse_date(value: str) -> date | None:
    """Parse dates in common AMFI formats."""

    for fmt in (
        "%d-%b-%Y",
        "%d-%B-%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue

    return None


def _detect_csv_layout(csv_text: str) -> tuple[str, list[str]]:
    """
    Identify the AMFI CSV layout from its header.

    Supported layouts:
    - historical: NAV Name, Plan, Option, NAV, Date
    - export: Scheme Name, Plan, Option, Net Asset Value, Date
    - legacy: six-column fixtures with Scheme Name, NAV, Date
    """

    header = next(
        (
            [field.strip().casefold() for field in line.split(";")]
            for line in csv_text.splitlines()
            if "scheme code" in line.casefold() and ";" in line
        ),
        [],
    )

    if not header:
        return "legacy", []

    if "nav name" in header:
        return "historical", header

    # IMPORTANT:
    # Do not classify a six-column fixture as the eight-column export.
    # The official export has the specific "Net Asset Value" header.
    if (
        "scheme name" in header
        and "net asset value" in header
    ):
        return "export", header

    return "legacy", header


def parse_nav_csv(
    csv_text: str,
    requested_scheme_name: str,
    requested_date: date,
    source_url: str = AMFI_NAV_URL,
    retrieved_at: datetime | None = None,
) -> NAVRecord:
    """
    Parse NAV history and require a unique scheme/date match.

    Exact-date matching is mandatory. Ambiguous or missing NAV records
    are rejected rather than guessed.
    """

    if not requested_scheme_name.strip():
        raise NAVRetrievalError(
            "A scheme name is required for NAV lookup."
        )

    if not csv_text.strip():
        raise NAVRetrievalError(
            "The NAV source returned an empty response."
        )

    if (
        "No data found on the basis of selected parameters"
        in csv_text
    ):
        raise NAVRetrievalError(
            "AMFI returned no NAV data for the selected parameters."
        )

    layout, _header = _detect_csv_layout(csv_text)
    matches = []

    for line in csv_text.splitlines():
        fields = [field.strip() for field in line.split(";")]

        # Ignore headers, blank lines, and non-data lines.
        if not fields or not fields[0].isdigit():
            continue

        if layout == "historical":
            # 0=Scheme Code, 1=NAV Name, 2=Plan, 3=Option,
            # 6=Net Asset Value, 7=Date
            if len(fields) < 8:
                continue

            nav_name = fields[1]
            plan = fields[2]
            option = fields[3]
            nav_value = fields[6]
            date_value = fields[7]

            parts = [
                part.strip()
                for part in requested_scheme_name.rsplit(" - ", 2)
            ]

            if len(parts) == 3:
                requested_base, requested_plan, requested_option = parts

                normalized_nav_name = _normalize_scheme_name(nav_name)
                normalized_base = _normalize_scheme_name(requested_base)

                # NAV Name may append plan/option information.
                if not (
                    normalized_nav_name == normalized_base
                    or normalized_nav_name.startswith(
                        normalized_base + " -"
                    )
                ):
                    continue

                if plan.casefold() != requested_plan.casefold():
                    continue

                if _normalize_option(option) != _normalize_option(
                    requested_option
                ):
                    continue

                scheme_name = requested_base

            else:
                normalized_nav_name = _normalize_scheme_name(nav_name)
                normalized_requested = _normalize_scheme_name(
                    requested_scheme_name
                )

                if not (
                    normalized_nav_name == normalized_requested
                    or normalized_nav_name.startswith(
                        normalized_requested + " -"
                    )
                ):
                    continue

                scheme_name = nav_name

        elif layout == "export":
            # 0=Scheme Code, 3=Scheme Name, 4=Plan,
            # 5=Option, 6=Net Asset Value, 7=Date
            if len(fields) < 8:
                continue

            scheme_name = fields[3]
            plan = fields[4]
            option = fields[5]
            nav_value = fields[6]
            date_value = fields[7]

            parts = [
                part.strip()
                for part in requested_scheme_name.rsplit(" - ", 2)
            ]

            if len(parts) == 3:
                requested_base, requested_plan, requested_option = parts

                if (
                    _normalize_scheme_name(scheme_name)
                    != _normalize_scheme_name(requested_base)
                    or plan.casefold() != requested_plan.casefold()
                    or _normalize_option(option)
                    != _normalize_option(requested_option)
                ):
                    continue

            elif (
                _normalize_scheme_name(scheme_name)
                != _normalize_scheme_name(requested_scheme_name)
            ):
                continue

        else:
            # Legacy six-column layout:
            # 0=Scheme Code, 1=ISIN, 2=ISIN Reinvestment,
            # 3=Scheme Name, 4=NAV, 5=Date
            if len(fields) < 6:
                continue

            scheme_name = fields[3]

            if (
                _normalize_scheme_name(scheme_name)
                != _normalize_scheme_name(requested_scheme_name)
            ):
                continue

            nav_value = fields[4]
            date_value = fields[5]

        nav_date = _parse_date(date_value)

        if nav_date != requested_date:
            continue

        try:
            nav = Decimal(nav_value)
        except (InvalidOperation, ValueError):
            continue

        if not nav.is_finite() or nav <= Decimal("0"):
            continue

        matches.append(
            (scheme_name, nav_date, nav, line, fields[0])
        )

    if not matches:
        raise NAVRetrievalError(
            "No valid NAV record matched the requested "
            f"scheme name {requested_scheme_name!r} and date "
            f"{requested_date.isoformat()}. The scheme may have "
            "a different official name, the date may have no data, "
            "or the selected plan/option may need clarification."
        )

    if len(matches) > 1:
        raise NAVRetrievalError(
            "Multiple NAV records matched the requested scheme "
            "and date. Human review is required."
        )

    scheme_name, nav_date, nav, evidence_line, _scheme_code = matches[0]

    timestamp = retrieved_at or datetime.now(timezone.utc)

    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    else:
        timestamp = timestamp.astimezone(timezone.utc)

    evidence = NAVEvidence(
        evidence_id=str(uuid4()),
        source_url=source_url,
        retrieved_at=timestamp,
        evidence_text=evidence_line,
    )

    return NAVRecord(
        scheme_name=scheme_name,
        nav_date=nav_date,
        nav=nav,
        evidence=evidence,
    )


async def _fetch_nav_history_with_metadata(
    start_date: date,
    end_date: date,
    fund_house_id: str | None = None,
) -> NAVFetchResult:
    """
    Fetch AMFI NAV history and retain its final URL and retrieval time.

    A request is limited to 90 calendar days.
    """

    if start_date > end_date:
        raise ValueError(
            "Start date cannot be later than end date."
        )

    days = (end_date - start_date).days + 1

    if days > 90:
        raise ValueError(
            "AMFI historical NAV downloads support at most "
            "90 calendar days per request."
        )

    if not fund_house_id:
        raise NAVRetrievalError(
            "A fund-house ID is required for the current AMFI "
            "historical download endpoint."
        )

    params = {
        "mf": fund_house_id,
        "frmdt": start_date.strftime("%d-%b-%Y"),
        "todt": end_date.strftime("%d-%b-%Y"),
        "tp": "1",
    }

    try:
        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0"},
        ) as client:
            response = await client.get(
                AMFI_NAV_URL,
                params=params,
            )

            response.raise_for_status()
            retrieved_at = datetime.now(timezone.utc)

    except httpx.HTTPError as exc:
        raise NAVRetrievalError(
            f"Unable to retrieve NAV history: {exc}"
        ) from exc

    text = response.text.strip()

    if not text:
        raise NAVRetrievalError(
            "The NAV source returned an empty response."
        )

    if (
        "No data found on the basis of selected parameters"
        in text
    ):
        raise NAVRetrievalError(
            "AMFI returned no NAV records for the requested "
            f"fund house and dates {start_date} to {end_date}."
        )

    beginning = text[:1000].lstrip().casefold()

    if "<html" in beginning or "<!doctype html" in beginning:
        raise NAVRetrievalError(
            "AMFI returned HTML instead of NAV records. "
            "The response cannot be used as valuation evidence."
        )

    if "scheme code;" not in text.casefold():
        raise NAVRetrievalError(
            "The AMFI response does not contain the expected "
            "historical NAV column header."
        )

    return NAVFetchResult(
        text=text,
        source_url=str(response.url),
        retrieved_at=retrieved_at,
    )


async def fetch_nav_history(
    start_date: date,
    end_date: date,
    fund_house_id: str | None = None,
) -> str:
    """
    Backward-compatible fetch function returning NAV text.

    Existing callers can continue using this function. The metadata
    helper is available for callers that need the final source URL
    and UTC retrieval timestamp.
    """

    result = await _fetch_nav_history_with_metadata(
        start_date=start_date,
        end_date=end_date,
        fund_house_id=fund_house_id,
    )

    return result.text

