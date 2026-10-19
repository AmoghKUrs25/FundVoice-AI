
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
    """
    Parse AMFI-style semicolon-separated NAV data.

    Expected record format:
        Scheme Code;ISIN;ISIN;Scheme Name;NAV;Date

    This function requires an exact scheme-name match
    and an exact NAV-date match.

    It does not silently substitute a NAV from another date.
    """

    matches = []

    for line in csv_text.splitlines():
        fields = [field.strip() for field in line.split(";")]

        if len(fields) < 6:
            continue

        scheme_name = fields[3]
        nav_text = fields[4]
        date_text = fields[5]

        if scheme_name.casefold() != requested_scheme_name.casefold():
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
