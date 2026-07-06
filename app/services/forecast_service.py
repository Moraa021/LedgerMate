"""
Simple, dependable forecasting for a small business ledger.

Rather than a black-box model, this uses linear regression over daily
aggregated income/expense totals (scikit-learn, already a dependency) plus a
naive 7-day moving average as a sanity baseline. This is intentionally
simple: with the transaction volumes a micro-business logs (tens/hundreds of
entries a month), a simple trend line generalizes far better than a complex
model, and it's easy to explain to a non-technical user ("based on your
recent trend, you're on track for roughly X next month").

If/when there's enough history (12+ months), swap in `statsmodels` ARIMA or
Prophet for seasonality-aware forecasts — the interface below
(`forecast_series`) is written so that swap only touches this file.
"""
from datetime import datetime, timedelta
import numpy as np
from sqlalchemy import func
from app.models import Transaction


class ForecastService:

    def _daily_totals(self, user_id, metric, lookback_days=90):
        """Returns (dates: list[date], values: list[float]) for the given
        metric ('income', 'expense', or 'net'), filling gaps with 0."""
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=lookback_days)

        rows = Transaction.query.with_entities(
            func.date(Transaction.transaction_date).label('date'),
            Transaction.type,
            func.sum(Transaction.amount).label('total')
        ).filter(
            Transaction.user_id == user_id,
            Transaction.is_deleted == False,
            func.date(Transaction.transaction_date) >= start_date,
            func.date(Transaction.transaction_date) <= end_date,
        ).group_by(func.date(Transaction.transaction_date), Transaction.type).all()

        by_date = {}
        for row in rows:
            d = row.date if not isinstance(row.date, str) else datetime.strptime(row.date, '%Y-%m-%d').date()
            by_date.setdefault(d, {'income': 0.0, 'expense': 0.0})
            by_date[d][row.type] = float(row.total or 0)

        dates, values = [], []
        current = start_date
        while current <= end_date:
            day = by_date.get(current, {'income': 0.0, 'expense': 0.0})
            if metric == 'net':
                val = day['income'] - day['expense']
            else:
                val = day.get(metric, 0.0)
            dates.append(current)
            values.append(val)
            current += timedelta(days=1)

        return dates, values

    def forecast_series(self, values, horizon):
        """Linear regression trend forecast, with a moving-average baseline
        for comparison. Returns forecasted daily values for `horizon` days
        ahead."""
        n = len(values)
        if n < 7:
            # Not enough history — flat forecast using the available average
            avg = float(np.mean(values)) if values else 0.0
            return [avg] * horizon, 'insufficient_history'

        try:
            from sklearn.linear_model import LinearRegression
            X = np.arange(n).reshape(-1, 1)
            y = np.array(values)
            model = LinearRegression()
            model.fit(X, y)

            future_X = np.arange(n, n + horizon).reshape(-1, 1)
            preds = model.predict(future_X)
            preds = np.maximum(preds, 0)  # no negative income/expense forecasts
            return preds.tolist(), 'linear_trend'
        except Exception:
            # Fallback: flat 7-day moving average
            window = values[-7:]
            avg = float(np.mean(window)) if window else 0.0
            return [avg] * horizon, 'moving_average_fallback'

    def forecast(self, user_id, metric='net', horizon_days=30, lookback_days=90):
        dates, values = self._daily_totals(user_id, metric, lookback_days)
        forecasted, method = self.forecast_series(values, horizon_days)

        last_date = dates[-1] if dates else datetime.utcnow().date()
        forecast_dates = [
            (last_date + timedelta(days=i + 1)).strftime('%Y-%m-%d')
            for i in range(horizon_days)
        ]

        # 7-day moving average trendline for the historical part, useful for charting
        history_ma = []
        for i in range(len(values)):
            window = values[max(0, i - 6):i + 1]
            history_ma.append(round(float(np.mean(window)), 2))

        recent_avg = float(np.mean(values[-30:])) if len(values) >= 1 else 0.0
        forecast_avg = float(np.mean(forecasted)) if forecasted else 0.0
        if recent_avg > 0:
            trend_pct = ((forecast_avg - recent_avg) / recent_avg) * 100
        else:
            trend_pct = 0.0

        return {
            'metric': metric,
            'method': method,
            'history': {
                'dates': [d.strftime('%Y-%m-%d') for d in dates],
                'values': [round(v, 2) for v in values],
                'moving_average': history_ma,
            },
            'forecast': {
                'dates': forecast_dates,
                'values': [round(v, 2) for v in forecasted],
                'total_projected': round(sum(forecasted), 2),
            },
            'trend': {
                'direction': 'up' if trend_pct > 5 else 'down' if trend_pct < -5 else 'stable',
                'change_pct': round(trend_pct, 1),
            },
        }

    def cash_flow_forecast(self, user_id, horizon_days=30, lookback_days=90):
        """Convenience: income, expense, and net forecasts together, useful
        for a single dashboard/report view."""
        return {
            'income': self.forecast(user_id, 'income', horizon_days, lookback_days),
            'expense': self.forecast(user_id, 'expense', horizon_days, lookback_days),
            'net': self.forecast(user_id, 'net', horizon_days, lookback_days),
        }


forecast_service = ForecastService()
