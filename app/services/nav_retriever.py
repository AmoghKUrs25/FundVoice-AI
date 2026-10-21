
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import httpx

from app.models.nav import NAVEvidence, NAVRecord


AMFI_NAV_URL = "https://portal.amfiindia.com/DownloadNAVHistoryReport_Po.aspx"


class NAVRetrievalError(Exception):
    """Raised when NAV information cannot be retrieved safely."""


def parse_nav_csv(
    csv_text: str,
    requested_scheme_name: str,
    requested_date: date,
) -> NAVRecord:
    """Parse legacy and current AMFI-style NAV history records."""

    matches = []

    for line in csv_text.splitlines():
        fields = [field.strip() for field in line.split(";")]

        scheme_name = ""
        nav_text = ""
        date_text = ""

        # Current AMFI format: 8 columns
        # Scheme Code;NAV Name;Plan;Option;ISIN;ISIN;NAV;Date
        if len(fields) >= 8 and fields[0].isdigit():
            scheme_name = fields[1]
            nav_text = fields[6]
            date_text = fields[7]

        # Legacy/test format: 6 columns
        # Scheme Code;ISIN;ISIN;Scheme Name;NAV;Date
        elif len(fields) >= 6 and fields[0].isdigit():
            scheme_name = fields[3]
            nav_text = fields[4]
            date_text = fields[5]

        else:
            continue

        if scheme_name.casefold() != requested_scheme_name.strip().casefold():
            continue

        try:
            nav_date = datetime.strptime(
                date_text,
                "%d-%b-%Y",
            ).date()
            nav = Decimal(nav_text)
        except (ValueError, ArithmeticError):
            continue

        if nav_date != requested_date:
            continue

        if not nav.is_finite() or nav <= Decimal("0"):
            continue

        matches.append((scheme_name, nav_date, nav, line))

    if not matches:
        raise NAVRetrievalError(
            "No valid NAV record matched both the requested "
            "scheme name and valuation date."
        )

    if len(matches) > 1:
        raise NAVRetrievalError(
            "Multiple NAV records matched the requested scheme "
            "and date. Scheme identification needs further review."
        )

    scheme_name, nav_date, nav, evidence_line = matches[0]

    evidence = NAVEvidence(
        evidence_id=str(uuid4()),
        source_url=AMFI_NAV_URL,
        retrieved_at=datetime.now(timezone.utc),
        evidence_text=evidence_line,
    )

    return NAVRecord(
        scheme_name=scheme_name,
        nav_date=nav_date,
        nav=nav,
        evidence=evidence,
    )


async def fetch_nav_history(
    start_date: date,
    end_date: date,
) -> str:
    """
    Request NAV history for a date range.

    Returns the response text if the HTTP request succeeds.
    """

    if start_date > end_date:
        raise ValueError(
            "Start date cannot be later than end date."
        )

    params = {
        "frmdt": start_date.strftime("%d-%b-%Y"),
        "todt": end_date.strftime("%d-%b-%Y"),
    }

    try:
        async with httpx.AsyncClient(
            timeout=20.0,
            follow_redirects=True,
        ) as client:
            response = await client.get(
                AMFI_NAV_URL,
                params=params,
            )
            response.raise_for_status()

    except httpx.HTTPError as exc:
        raise NAVRetrievalError(
            f"Unable to retrieve NAV history: {exc}"
        ) from exc

    if not response.text.strip():
        raise NAVRetrievalError(
            "The NAV source returned an empty response."
        )

    return response.text


def fetch_nav_history_sync(
    start_date: date,
    end_date: date,
) -> str:
    """Synchronously download NAV history for a date range."""

    if start_date > end_date:
        raise ValueError(
            "Start date cannot be later than end date."
        )

    params = {
        "frmdt": start_date.strftime("%d-%b-%Y"),
        "todt": end_date.strftime("%d-%b-%Y"),
    }

    try:
        with httpx.Client(
            timeout=20.0,
            follow_redirects=True,
        ) as client:
            response = client.get(
                AMFI_NAV_URL,
                params=params,
            )
            response.raise_for_status()

    except httpx.HTTPError as exc:
        raise NAVRetrievalError(
            f"Unable to retrieve NAV history: {exc}"
        ) from exc

    if not response.text.strip():
        raise NAVRetrievalError(
            "The NAV source returned an empty response."
        )

    return response.text
