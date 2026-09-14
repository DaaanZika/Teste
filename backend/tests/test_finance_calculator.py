import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.models.enums import TransactionType
from app.models.transaction import Transaction
from app.services.finance import calculator


@pytest.fixture()
def campaign_id():
    # Each test uses its own campaign id so calculator queries (filtered by
    # campaign_id) never see transactions inserted by other tests sharing
    # the same session-wide sqlite database.
    return str(uuid.uuid4())


def _add_transaction(db_session, *, campaign_id, type_, amount, when=None, category=None, counterparty=None):
    txn = Transaction(
        campaign_id=campaign_id,
        type=type_,
        amount=Decimal(amount),
        date=when or date(2024, 1, 1),
        category=category,
        counterparty=counterparty,
    )
    db_session.add(txn)
    db_session.commit()
    return txn


def test_total_revenues_and_expenses_use_decimal_precision(db_session, campaign_id):
    _add_transaction(db_session, campaign_id=campaign_id, type_=TransactionType.REVENUE, amount="1000.10")
    _add_transaction(db_session, campaign_id=campaign_id, type_=TransactionType.REVENUE, amount="0.05")
    _add_transaction(db_session, campaign_id=campaign_id, type_=TransactionType.EXPENSE, amount="250.33")

    total_rev = calculator.total_revenues(db_session, campaign_id=campaign_id)
    total_exp = calculator.total_expenses(db_session, campaign_id=campaign_id)

    assert total_rev == Decimal("1000.15")
    assert total_exp == Decimal("250.33")
    assert isinstance(total_rev, Decimal)


def test_balance_is_revenues_minus_expenses(db_session, campaign_id):
    _add_transaction(db_session, campaign_id=campaign_id, type_=TransactionType.REVENUE, amount="500.00")
    _add_transaction(db_session, campaign_id=campaign_id, type_=TransactionType.EXPENSE, amount="199.99")

    assert calculator.balance(db_session, campaign_id=campaign_id) == Decimal("300.01")


def test_balance_handles_large_values_without_float_rounding_errors(db_session, campaign_id):
    _add_transaction(db_session, campaign_id=campaign_id, type_=TransactionType.REVENUE, amount="999999999.99")
    _add_transaction(db_session, campaign_id=campaign_id, type_=TransactionType.EXPENSE, amount="0.01")

    assert calculator.balance(db_session, campaign_id=campaign_id) == Decimal("999999999.98")


def test_totals_by_category_computes_percentages(db_session, campaign_id):
    _add_transaction(
        db_session, campaign_id=campaign_id, type_=TransactionType.EXPENSE, amount="75.00", category="Combustível"
    )
    _add_transaction(
        db_session, campaign_id=campaign_id, type_=TransactionType.EXPENSE, amount="25.00", category="Aluguel"
    )

    breakdown = calculator.totals_by_category(db_session, campaign_id=campaign_id, type_=TransactionType.EXPENSE)
    by_category = {row["category"]: row for row in breakdown}

    assert by_category["Combustível"]["total"] == Decimal("75.00")
    assert by_category["Combustível"]["percentage_of_total"] == Decimal("75.00")
    assert by_category["Aluguel"]["percentage_of_total"] == Decimal("25.00")


def test_totals_by_period_groups_by_month(db_session, campaign_id):
    _add_transaction(
        db_session, campaign_id=campaign_id, type_=TransactionType.REVENUE, amount="100.00", when=date(2024, 3, 10)
    )
    _add_transaction(
        db_session, campaign_id=campaign_id, type_=TransactionType.EXPENSE, amount="40.00", when=date(2024, 3, 20)
    )
    _add_transaction(
        db_session, campaign_id=campaign_id, type_=TransactionType.REVENUE, amount="10.00", when=date(2024, 4, 1)
    )

    periods = {
        row["period"]: row
        for row in calculator.totals_by_period(db_session, campaign_id=campaign_id, granularity="month")
    }

    assert periods["2024-03"]["total_revenues"] == Decimal("100.00")
    assert periods["2024-03"]["total_expenses"] == Decimal("40.00")
    assert periods["2024-03"]["balance"] == Decimal("60.00")
    assert periods["2024-04"]["total_revenues"] == Decimal("10.00")


def test_totals_by_period_day_granularity_and_date_range(db_session, campaign_id):
    _add_transaction(
        db_session, campaign_id=campaign_id, type_=TransactionType.REVENUE, amount="20.00", when=date(2024, 6, 1)
    )
    _add_transaction(
        db_session, campaign_id=campaign_id, type_=TransactionType.REVENUE, amount="30.00", when=date(2024, 6, 2)
    )
    _add_transaction(
        db_session, campaign_id=campaign_id, type_=TransactionType.REVENUE, amount="99.00", when=date(2024, 7, 1)
    )

    rows = calculator.totals_by_period(
        db_session,
        campaign_id=campaign_id,
        granularity="day",
        start_date=date(2024, 6, 1),
        end_date=date(2024, 6, 30),
    )

    assert {r["period"] for r in rows} == {"2024-06-01", "2024-06-02"}
    by_day = {r["period"]: r for r in rows}
    assert by_day["2024-06-01"]["total_revenues"] == Decimal("20.00")
    assert by_day["2024-06-02"]["total_revenues"] == Decimal("30.00")
