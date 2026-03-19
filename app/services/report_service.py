from datetime import datetime, timedelta
from app.models import Transaction, Category
from app.extensions import db
from sqlalchemy import func, extract
import calendar
import json

class ReportService:
    """Service for generating financial reports"""
    
    def __init__(self):
        pass
    
    def generate_report(self, user_id, period='monthly', from_date=None, to_date=None, 
                       transaction_type='all', category_id=None):
        """Generate report based on parameters"""
        
        # Set date range
        if period == 'daily':
            to_date = datetime.utcnow().date()
            from_date = to_date
        elif period == 'weekly':
            to_date = datetime.utcnow().date()
            from_date = to_date - timedelta(days=7)
        elif period == 'monthly':
            to_date = datetime.utcnow().date()
            from_date = to_date - timedelta(days=30)
        elif period == 'custom':
            if not from_date or not to_date:
                raise ValueError("Custom period requires from_date and to_date")
        else:
            raise ValueError(f"Invalid period: {period}")
        
        # Build query
        query = Transaction.query.filter(
            Transaction.user_id == user_id,
            Transaction.is_deleted == False,
            func.date(Transaction.transaction_date) >= from_date,
            func.date(Transaction.transaction_date) <= to_date
        )
        
        # Apply type filter
        if transaction_type != 'all':
            query = query.filter(Transaction.type == transaction_type)
        
        # Apply category filter
        if category_id and category_id != 'all':
            query = query.filter(Transaction.category_id == category_id)
        
        # Execute query
        transactions = query.order_by(Transaction.transaction_date.desc()).all()
        
        # Calculate summaries
        income_total = sum(t.amount for t in transactions if t.type == 'income')
        expense_total = sum(t.amount for t in transactions if t.type == 'expense')
        
        # Group by category
        category_breakdown = self._get_category_breakdown(transactions, user_id)
        
        # Group by date for chart
        daily_data = self._get_daily_breakdown(transactions, from_date, to_date)
        
        # Format transactions for output
        formatted_transactions = self._format_transactions(transactions)
        
        return {
            'period': period,
            'from_date': from_date.strftime('%Y-%m-%d'),
            'to_date': to_date.strftime('%Y-%m-%d'),
            'summary': {
                'income': float(income_total),
                'expense': float(expense_total),
                'net': float(income_total - expense_total),
                'transaction_count': len(transactions)
            },
            'category_breakdown': category_breakdown,
            'daily_breakdown': daily_data,
            'transactions': formatted_transactions
        }
    
    def _get_category_breakdown(self, transactions, user_id):
        """Break down transactions by category"""
        categories = {}
        
        # Get all categories for this user
        category_objects = {c.id: c for c in Category.query.filter_by(user_id=user_id).all()}
        
        for t in transactions:
            cat_id = t.category_id
            if cat_id not in categories:
                cat = category_objects.get(cat_id)
                categories[cat_id] = {
                    'name': cat.name if cat else 'Unknown',
                    'type': cat.type if cat else 'unknown',
                    'income': 0,
                    'expense': 0,
                    'count': 0
                }
            
            if t.type == 'income':
                categories[cat_id]['income'] += float(t.amount)
            else:
                categories[cat_id]['expense'] += float(t.amount)
            
            categories[cat_id]['count'] += 1
        
        # Calculate percentages
        total_income = sum(c['income'] for c in categories.values())
        total_expense = sum(c['expense'] for c in categories.values())
        
        for cat_id, data in categories.items():
            if total_income > 0:
                data['income_percentage'] = (data['income'] / total_income) * 100
            else:
                data['income_percentage'] = 0
            
            if total_expense > 0:
                data['expense_percentage'] = (data['expense'] / total_expense) * 100
            else:
                data['expense_percentage'] = 0
        
        return categories
    
    def _get_daily_breakdown(self, transactions, from_date, to_date):
        """Get daily totals for chart"""
        daily_data = {}
        
        # Initialize all dates in range
        current = from_date
        while current <= to_date:
            date_str = current.strftime('%Y-%m-%d')
            daily_data[date_str] = {
                'date': date_str,
                'income': 0,
                'expense': 0,
                'count': 0
            }
            current += timedelta(days=1)
        
        # Aggregate transactions
        for t in transactions:
            date_str = t.transaction_date.strftime('%Y-%m-%d')
            if date_str in daily_data:
                if t.type == 'income':
                    daily_data[date_str]['income'] += float(t.amount)
                else:
                    daily_data[date_str]['expense'] += float(t.amount)
                daily_data[date_str]['count'] += 1
        
        # Convert to list sorted by date
        return [daily_data[date] for date in sorted(daily_data.keys())]
    
    def _format_transactions(self, transactions):
        """Format transactions for output"""
        formatted = []
        
        for t in transactions:
            formatted.append({
                'id': t.public_id,
                'type': t.type,
                'amount': float(t.amount),
                'payment_method': t.payment_method,
                'description': t.description,
                'mpesa_code': t.mpesa_code,
                'category_id': t.category_id,
                'date': t.transaction_date.strftime('%Y-%m-%d'),
                'time': t.transaction_date.strftime('%H:%M'),
                'created_at': t.created_at.strftime('%Y-%m-%d %H:%M')
            })
        
        return formatted
    
    def get_monthly_summary(self, user_id, year=None, month=None):
        """Get summary for a specific month"""
        if not year:
            year = datetime.utcnow().year
        if not month:
            month = datetime.utcnow().month
        
        # Get first and last day of month
        first_day = datetime(year, month, 1)
        if month == 12:
            last_day = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = datetime(year, month + 1, 1) - timedelta(days=1)
        
        # Get transactions for the month
        transactions = Transaction.query.filter(
            Transaction.user_id == user_id,
            Transaction.is_deleted == False,
            Transaction.transaction_date >= first_day,
            Transaction.transaction_date <= last_day
        ).all()
        
        # Calculate totals
        income = sum(t.amount for t in transactions if t.type == 'income')
        expense = sum(t.amount for t in transactions if t.type == 'expense')
        
        # Get daily totals for chart
        daily_data = []
        current = first_day
        while current <= last_day:
            day_transactions = [t for t in transactions 
                              if t.transaction_date.date() == current.date()]
            day_income = sum(t.amount for t in day_transactions if t.type == 'income')
            day_expense = sum(t.amount for t in day_transactions if t.type == 'expense')
            
            daily_data.append({
                'day': current.day,
                'date': current.strftime('%Y-%m-%d'),
                'income': float(day_income),
                'expense': float(day_expense)
            })
            
            current += timedelta(days=1)
        
        return {
            'year': year,
            'month': month,
            'month_name': calendar.month_name[month],
            'summary': {
                'income': float(income),
                'expense': float(expense),
                'net': float(income - expense),
                'transaction_count': len(transactions)
            },
            'daily_data': daily_data
        }
    
    def get_year_summary(self, user_id, year=None):
        """Get summary for a specific year"""
        if not year:
            year = datetime.utcnow().year
        
        # Get all months
        monthly_data = []
        
        for month in range(1, 13):
            monthly = self.get_monthly_summary(user_id, year, month)
            monthly_data.append(monthly)
        
        # Calculate yearly totals
        yearly_income = sum(m['summary']['income'] for m in monthly_data)
        yearly_expense = sum(m['summary']['expense'] for m in monthly_data)
        
        return {
            'year': year,
            'summary': {
                'income': yearly_income,
                'expense': yearly_expense,
                'net': yearly_income - yearly_expense,
                'total_transactions': sum(m['summary']['transaction_count'] for m in monthly_data)
            },
            'monthly_data': monthly_data
        }
    
    def compare_periods(self, user_id, period1_start, period1_end, period2_start, period2_end):
        """Compare two time periods"""
        # Get data for first period
        period1_data = self.generate_report(
            user_id, 'custom', 
            from_date=period1_start, 
            to_date=period1_end
        )
        
        # Get data for second period
        period2_data = self.generate_report(
            user_id, 'custom',
            from_date=period2_start,
            to_date=period2_end
        )
        
        # Calculate changes
        income_change = period2_data['summary']['income'] - period1_data['summary']['income']
        expense_change = period2_data['summary']['expense'] - period1_data['summary']['expense']
        net_change = period2_data['summary']['net'] - period1_data['summary']['net']
        
        income_percent = (income_change / period1_data['summary']['income'] * 100) if period1_data['summary']['income'] > 0 else 0
        expense_percent = (expense_change / period1_data['summary']['expense'] * 100) if period1_data['summary']['expense'] > 0 else 0
        
        return {
            'period1': {
                'from': period1_start.strftime('%Y-%m-%d'),
                'to': period1_end.strftime('%Y-%m-%d'),
                'summary': period1_data['summary']
            },
            'period2': {
                'from': period2_start.strftime('%Y-%m-%d'),
                'to': period2_end.strftime('%Y-%m-%d'),
                'summary': period2_data['summary']
            },
            'changes': {
                'income': {
                    'absolute': float(income_change),
                    'percentage': float(income_percent),
                    'direction': 'up' if income_change > 0 else 'down' if income_change < 0 else 'same'
                },
                'expense': {
                    'absolute': float(expense_change),
                    'percentage': float(expense_percent),
                    'direction': 'up' if expense_change > 0 else 'down' if expense_change < 0 else 'same'
                },
                'net': {
                    'absolute': float(net_change),
                    'direction': 'up' if net_change > 0 else 'down' if net_change < 0 else 'same'
                }
            }
        }

# Create singleton instance
report_service = ReportService()