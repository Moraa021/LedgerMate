"""
Lightweight AI forecasting for LedgerMate.

Uses a simple linear regression (numpy polyfit, degree 1) over monthly
income/expense totals to project the next few months. This is intentionally
simple and explainable rather than a black box - MSE owners need to trust
and understand a forecast, not just see a number.
"""
from datetime import datetime
from dateutil.relativedelta import relativedelta
import numpy as np
from sqlalchemy import func, extract
from app.models import Transaction
from app.extensions import db


class ForecastService:

    def _monthly_totals(self, user_id, months_back=12):
        """Returns list of dicts: [{year, month, income, expense}] oldest -> newest."""
        today = datetime.utcnow()
        start = (today.replace(day=1) - relativedelta(months=months_back - 1))

        rows = db.session.query(
            extract('year', Transaction.transaction_date).label('year'),
            extract('month', Transaction.transaction_date).label('month'),
            Transaction.type,
            func.sum(Transaction.amount).label('total')
        ).filter(
            Transaction.user_id == user_id,
            Transaction.is_deleted == False,
            Transaction.transaction_date >= start
        ).group_by('year', 'month', Transaction.type).all()

        buckets = {}
        cursor = start
        for _ in range(months_back):
            key = (cursor.year, cursor.month)
            buckets[key] = {'year': cursor.year, 'month': cursor.month, 'income': 0.0, 'expense': 0.0}
            cursor += relativedelta(months=1)

        for r in rows:
            key = (int(r.year), int(r.month))
            if key in buckets:
                buckets[key][r.type] = float(r.total or 0)

        return [buckets[k] for k in sorted(buckets.keys())]

    def _linear_forecast(self, series, periods_ahead):
        """Fit y = a*x + b over the series and project forward. Never predicts below 0."""
        n = len(series)
        if n < 2 or all(v == 0 for v in series):
            avg = sum(series) / n if n else 0
            return [max(avg, 0) for _ in range(periods_ahead)]

        x = np.arange(n)
        y = np.array(series, dtype=float)
        slope, intercept = np.polyfit(x, y, 1)

        forecasts = []
        for i in range(periods_ahead):
            projected = slope * (n + i) + intercept
            forecasts.append(round(max(projected, 0), 2))
        return forecasts

    def generate_forecast(self, user_id, months_ahead=3, history_months=12):
        history = self._monthly_totals(user_id, months_back=history_months)
        income_series = [h['income'] for h in history]
        expense_series = [h['expense'] for h in history]

        income_forecast = self._linear_forecast(income_series, months_ahead)
        expense_forecast = self._linear_forecast(expense_series, months_ahead)

        # Build forward-looking month labels
        last = datetime.utcnow().replace(day=1)
        future_labels = []
        for i in range(1, months_ahead + 1):
            m = last + relativedelta(months=i)
            future_labels.append(m.strftime('%b %Y'))

        history_labels = [f"{datetime(h['year'], h['month'], 1):%b %Y}" for h in history]

        # Simple trend classification based on regression slope of net (income - expense)
        net_series = [i - e for i, e in zip(income_series, expense_series)]
        trend = 'stable'
        if len(net_series) >= 3:
            x = np.arange(len(net_series))
            slope, _ = np.polyfit(x, np.array(net_series, dtype=float), 1)
            if slope > max(abs(np.mean(net_series)), 1) * 0.05:
                trend = 'improving'
            elif slope < -max(abs(np.mean(net_series)), 1) * 0.05:
                trend = 'declining'

        insights = []
        if income_forecast and expense_forecast:
            projected_net = sum(income_forecast) - sum(expense_forecast)
            if projected_net < 0:
                insights.append(
                    f"Projected expenses may outpace income over the next {months_ahead} month(s) "
                    f"by roughly KES {abs(projected_net):,.0f} - worth reviewing costs."
                )
            else:
                insights.append(
                    f"Business is projected to net roughly KES {projected_net:,.0f} over the next {months_ahead} month(s)."
                )
        if trend == 'declining':
            insights.append("Your net income trend over recent months is trending downward.")
        elif trend == 'improving':
            insights.append("Your net income trend over recent months is trending upward.")

        return {
            'history': {
                'labels': history_labels,
                'income': income_series,
                'expense': expense_series
            },
            'forecast': {
                'labels': future_labels,
                'income': income_forecast,
                'expense': expense_forecast
            },
            'trend': trend,
            'insights': insights,
            'method': 'Linear regression over monthly totals (simple trend projection, not a guarantee).'
        }


forecast_service = ForecastService()
