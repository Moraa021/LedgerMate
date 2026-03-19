from flask import Blueprint, render_template, session, jsonify, request
from flask_login import login_required, current_user
from app.models import Transaction, Category
from app.extensions import db
from datetime import datetime, timedelta
from sqlalchemy import func

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    """Home page / Landing page"""
    if current_user.is_authenticated:
        return render_template('dashboard/dashboard.html')
    return render_template('index.html')

@bp.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard with financial overview"""
    return render_template('dashboard/dashboard.html')

@bp.route('/api/dashboard/stats')
@login_required
def dashboard_stats():
    """API endpoint for dashboard statistics"""
    # Get date range (last 30 days)
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)
    
    # Calculate totals
    income_total = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == 'income',
        Transaction.transaction_date >= start_date,
        Transaction.transaction_date <= end_date,
        Transaction.is_deleted == False
    ).scalar() or 0
    
    expense_total = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == 'expense',
        Transaction.transaction_date >= start_date,
        Transaction.transaction_date <= end_date,
        Transaction.is_deleted == False
    ).scalar() or 0
    
    # Get recent transactions
    recent = Transaction.query.filter_by(
        user_id=current_user.id,
        is_deleted=False
    ).order_by(
        Transaction.transaction_date.desc()
    ).limit(10).all()
    
    # Get daily totals for chart
    daily_data = db.session.query(
        func.date(Transaction.transaction_date).label('date'),
        Transaction.type,
        func.sum(Transaction.amount).label('total')
    ).filter(
        Transaction.user_id == current_user.id,
        Transaction.transaction_date >= start_date,
        Transaction.is_deleted == False
    ).group_by(
        func.date(Transaction.transaction_date),
        Transaction.type
    ).all()
    
    # Format chart data
    chart_labels = []
    chart_income = []
    chart_expense = []
    
   # Process daily data
    date_totals = {}
    for item in daily_data:
        # Handle the date regardless of whether it's a string or a date object
        if isinstance(item.date, str):
            date_str = item.date
        elif item.date:
            date_str = item.date.strftime('%Y-%m-%d')
        else:
            continue
            
        # Initialize the date in our dictionary if it's the first time seeing it
        if date_str not in date_totals:
            date_totals[date_str] = {'income': 0, 'expense': 0}
        
        # Safely add the total to the correct type (income or expense)
        if item.type in date_totals[date_str]:
            date_totals[date_str][item.type] = float(item.total or 0)
    
    # Fill in missing dates for the chart
    current = start_date
    while current <= end_date:
        date_str = current.strftime('%Y-%m-%d')
        
        # Format the label for the chart (e.g., "19 Mar")
        chart_labels.append(current.strftime('%d %b'))
        
        # Get values from our processed totals, default to 0 if no data exists for that day
        day_data = date_totals.get(date_str, {})
        chart_income.append(day_data.get('income', 0))
        chart_expense.append(day_data.get('expense', 0))
        
        # Move to the next day
        current += timedelta(days=1)
    
    # Format recent transactions
    recent_data = []
    for t in recent:
        category = Category.query.get(t.category_id)
        recent_data.append({
            'id': t.public_id,
            'type': t.type,
            'amount': float(t.amount),
            'category': category.name if category else 'Unknown',
            'description': t.description,
            'date': t.transaction_date.strftime('%d %b %Y'),
            'payment_method': t.payment_method
        })
    
    return jsonify({
        'success': True,
        'income_total': float(income_total),
        'expense_total': float(expense_total),
        'net_total': float(income_total) - float(expense_total),
        'recent_transactions': recent_data,
        'chart_data': {
            'labels': chart_labels,
            'income': chart_income,
            'expense': chart_expense
        }
    })

@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        # Handle profile updates here (optional for now)
        pass

    # Dummy stats to prevent the template from crashing
    stats = {
        'member_since': current_user.created_at.strftime('%d %b %Y') if hasattr(current_user, 'created_at') else "Mar 2026",
        'total_transactions': Transaction.query.filter_by(user_id=current_user.id, is_deleted=False).count(),
        'category_count': Category.query.filter_by(user_id=current_user.id).count(),
        'net_total': db.session.query(func.sum(Transaction.amount)).filter_by(user_id=current_user.id, type='income').scalar() or 0 - 
                     (db.session.query(func.sum(Transaction.amount)).filter_by(user_id=current_user.id, type='expense').scalar() or 0),
        'income_total': 0, 'expense_total': 0, 'month_income': 0, 'month_expense': 0, 'month_net': 0
    }
    return render_template('profile.html', stats=stats)

@bp.route('/set-language', methods=['POST'])
def set_language():
    # This line handles both JSON and Form data automatically
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form
        
    language = data.get('language')

    if language in ['en', 'sw']:
        session['language'] = language
        # If you have a user model, save it there too
        if current_user.is_authenticated:
            current_user.language = language
            db.session.commit()
            
        return jsonify({'success': True}), 200
    
    return jsonify({'success': False, 'error': 'Invalid language'}), 400