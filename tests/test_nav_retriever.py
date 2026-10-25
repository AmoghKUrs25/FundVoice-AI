from decimal import Decimal
from datetime import date
from decimal import Decimal
import pytest

from app.services.nav_retriever import (
    NAVRetrievalError,
    parse_nav_csv,
)


SAMPLE_NAV_DATA = """\
100001;INF000000001;INF000000001;Example Equity Fund;80.2500;16-Oct-2026
100002;INF000000002;INF000000002;Example Debt Fund;25.5000;16-Oct-2026
100001;INF000000001;INF000000001;Example Equity Fund;81.0000;17-Oct-2026
"""


def test_exact_scheme_and_date_match():
    result = parse_nav_csv(
        SAMPLE_NAV_DATA,
        "Example Equity Fund",
        date(2026, 10, 16),
    )

    assert result.scheme_name == "Example Equity Fund"
    assert result.nav_date == date(2026, 10, 16)
    assert str(result.nav) == "80.2500"


def test_scheme_matching_is_case_insensitive():
    result = parse_nav_csv(
        SAMPLE_NAV_DATA,
        "example equity fund",
        date(2026, 10, 16),
    )

    assert result.scheme_name == "Example Equity Fund"


def test_different_date_is_not_substituted():
    with pytest.raises(NAVRetrievalError):
        parse_nav_csv(
            SAMPLE_NAV_DATA,
            "Example Equity Fund",
            date(2026, 10, 18),
        )


def test_wrong_scheme_is_rejected():
    with pytest.raises(NAVRetrievalError):
        parse_nav_csv(
            SAMPLE_NAV_DATA,
            "Unknown Fund",
            date(2026, 10, 16),
        )


def test_duplicate_matching_records_are_rejected():
    duplicate_data = (
        "100001;INF000000001;INF000000001;"
        "Example Equity Fund;80.25;16-Oct-2026\n"
        "100003;INF000000003;INF000000003;"
        "Example Equity Fund;80.30;16-Oct-2026\n"
    )

    with pytest.raises(NAVRetrievalError):
        parse_nav_csv(
            duplicate_data,
            "Example Equity Fund",
            date(2026, 10, 16),
        )


def test_invalid_nav_is_rejected():
    invalid_data = (
        "100001;INF000000001;INF000000001;"
        "Example Equity Fund;0;16-Oct-2026\n"
    )

    with pytest.raises(NAVRetrievalError):
        parse_nav_csv(
            invalid_data,
            "Example Equity Fund",
            date(2026, 10, 16),
        )



def test_current_eight_column_amfi_format():
    live_format_data = (
        "145488;Example Overnight Fund;"
        "Direct Plan;Monthly IDCW;INF209KB1ZL4;;"
        "1003.6262;20-Oct-2026\n"
    )

    result = parse_nav_csv(
        live_format_data,
        "Example Overnight Fund - Direct Plan - Monthly IDCW",
        date(2026, 10, 20),
    )

    assert result.scheme_name == "Example Overnight Fund"
    assert result.nav == Decimal("1003.6262")
    assert result.nav_date == date(2026, 10, 20)


def test_invalid_nav_in_current_eight_column_format():
    invalid_data = (
        "145488;Example Overnight Fund - Direct;"
        "Direct Plan;Monthly IDCW;INF209KB1ZL4;;"
        "0;20-Oct-2026\n"
    )

    with pytest.raises(NAVRetrievalError):
        parse_nav_csv(
            invalid_data,
            "Example Overnight Fund - Direct",
            date(2026, 10, 20),
        )


def test_duplicate_current_format_records_are_rejected():
    duplicate_data = (
        "145488;Example Overnight Fund - Direct;"
        "Direct Plan;Monthly IDCW;INF209KB1ZL4;;"
        "1003.6262;20-Oct-2026\n"
        "145489;Example Overnight Fund - Direct;"
        "Direct Plan;Monthly IDCW;INF209KB1ZL5;;"
        "1004.0000;20-Oct-2026\n"
    )

    with pytest.raises(NAVRetrievalError):
        parse_nav_csv(
            duplicate_data,
            "Example Overnight Fund - Direct",
            date(2026, 10, 20),
        )