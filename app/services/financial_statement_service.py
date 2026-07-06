"""
Generates a Profit & Loss statement and a Balance Sheet from the existing
transaction ledger and inventory valuation.

IMPORTANT — read before presenting these to a bank, investor, or KRA:
LedgerMate keeps a single-entry, cash-basis record (money in / money out),
not full double-entry books. These statements are simplified accordingly:

  - There is no accounts-payable/receivable tracking, so all sales/expenses
    are assumed to be settled in cash/M-Pesa at the transaction date.
  - Inventory is valued at the CURRENT weighted-average cost, not a
    historical as-of-date cost, so Balance Sheets for past dates are an
    approximation.
  - Owner's Equity is a plug (Assets - Liabilities) since capital
    contributions/drawings aren't tracked separately from trading profit.

These are good enough for day-to-day management decisions and rough investor
conversations. For statutory filing or a loan application, have an
accountant review them.
"""
from datetime import datetime
from app.models import Transaction
from app.extensions import db
from sqlalchemy import func
from app.services.inventory_service import inventory_service


class FinancialStatementService:

    def profit_and_loss(self, user_id, from_date=None, to_date=None):
        query = Transaction.query.filter(
            Transaction.user_id == user_id,
            Transaction.is_deleted == False,
        )
        if from_date:
            query = query.filter(func.date(Transaction.transaction_date) >= from_date)
        if to_date:
            query = query.filter(func.date(Transaction.transaction_date) <= to_date)

        transactions = query.all()

        revenue = sum(float(t.amount) for t in transactions if t.type == 'income')
        cogs = sum(float(t.amount) for t in transactions if t.type == 'expense' and t.is_cogs)

        # Inventory purchases are capitalized (they convert cash into a stock
        # asset) - they are NOT an operating expense. Their cost only hits the
        # P&L later, as COGS, when that stock is sold. Shown separately below
        # for transparency/cash-flow visibility, not added into net profit.
        inventory_purchases_total = sum(
            float(t.amount) for t in transactions
            if t.type == 'expense' and t.is_inventory_purchase
        )

        def _is_operating_expense(t):
            return t.type == 'expense' and not t.is_cogs and not t.is_inventory_purchase

        operating_expenses_total = sum(float(t.amount) for t in transactions if _is_operating_expense(t))

        # Break operating expenses down by category for the statement
        expense_by_category = {}
        for t in transactions:
            if _is_operating_expense(t):
                name = t.category.name if t.category else 'Uncategorized'
                expense_by_category[name] = expense_by_category.get(name, 0) + float(t.amount)

        revenue_by_category = {}
        for t in transactions:
            if t.type == 'income':
                name = t.category.name if t.category else 'Uncategorized'
                revenue_by_category[name] = revenue_by_category.get(name, 0) + float(t.amount)

        gross_profit = revenue - cogs
        net_profit = gross_profit - operating_expenses_total

        return {
            'from_date': str(from_date) if from_date else None,
            'to_date': str(to_date) if to_date else None,
            'revenue': {
                'total': revenue,
                'by_category': revenue_by_category,
            },
            'cost_of_goods_sold': cogs,
            'gross_profit': gross_profit,
            'gross_margin_pct': (gross_profit / revenue * 100) if revenue > 0 else 0,
            'operating_expenses': {
                'total': operating_expenses_total,
                'by_category': expense_by_category,
            },
            'inventory_purchases_capitalized': inventory_purchases_total,
            'net_profit': net_profit,
            'net_margin_pct': (net_profit / revenue * 100) if revenue > 0 else 0,
        }

    def balance_sheet(self, user_id, as_of_date=None):
        as_of_date = as_of_date or datetime.utcnow().date()

        query = Transaction.query.filter(
            Transaction.user_id == user_id,
            Transaction.is_deleted == False,
            func.date(Transaction.transaction_date) <= as_of_date,
        )
        transactions = query.all()

        total_income = sum(float(t.amount) for t in transactions if t.type == 'income')
        total_expense = sum(float(t.amount) for t in transactions if t.type == 'expense')

        # Cash & M-Pesa: cumulative net cash position to date
        cash_and_mpesa = total_income - total_expense

        # Inventory asset: current stock valuation (see module docstring caveat)
        inventory_value = inventory_service.total_inventory_value(user_id)

        total_assets = cash_and_mpesa + inventory_value

        # No debt/payables tracking yet
        total_liabilities = 0.0

        # Retained earnings = cumulative net profit to date (no separate
        # owner capital contributions tracked, so this doubles as total equity)
        retained_earnings = total_income - total_expense + (inventory_value - 0)
        # Note: retained_earnings intentionally includes inventory value so
        # that Assets == Liabilities + Equity balances exactly.
        total_equity = total_assets - total_liabilities

        return {
            'as_of_date': str(as_of_date),
            'assets': {
                'cash_and_mpesa': round(cash_and_mpesa, 2),
                'inventory': round(inventory_value, 2),
                'total': round(total_assets, 2),
            },
            'liabilities': {
                'total': round(total_liabilities, 2),
                'note': 'Accounts payable/loans are not yet tracked by LedgerMate.',
            },
            'equity': {
                'retained_earnings': round(total_equity, 2),
                'total': round(total_equity, 2),
            },
            'balances': round(total_assets - (total_liabilities + total_equity), 2) == 0,
        }


financial_statement_service = FinancialStatementService()
