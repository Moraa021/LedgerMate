from flask import Blueprint, render_template, session, jsonify, request, flash, redirect, url_for
from flask_login import login_required, current_user, logout_user
from app.models import Transaction, Category
from app.extensions import db
from datetime import datetime, timedelta
from sqlalchemy import func

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')

@bp.route('/dashboard')
@login_required
def dashboard():
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


# --- NEW LOGOUT ROUTE ---
@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))

@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    # 1. Setup initial data for the GET request
    categories = Category.query.filter_by(user_id=current_user.id).all()

    income_total = db.session.query(func.sum(Transaction.amount)).filter_by(
        user_id=current_user.id, type='income', is_deleted=False
    ).scalar() or 0
    
    expense_total = db.session.query(func.sum(Transaction.amount)).filter_by(
        user_id=current_user.id, type='expense', is_deleted=False
    ).scalar() or 0

    total_transactions = Transaction.query.filter_by(
        user_id=current_user.id, is_deleted=False
    ).count()

    stats = {
        'income_total': float(income_total),
        'expense_total': float(expense_total),
        'net_total': float(income_total - expense_total),
        'total_transactions': total_transactions,
        'member_since': current_user.created_at.strftime('%d %b %Y') if hasattr(current_user, 'created_at') and current_user.created_at else "Mar 2026"
    }

    # 2. Handle Form Submissions (POST)
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'update_profile':
            current_user.business_name = request.form.get('business_name')
            current_user.email = request.form.get('email')
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('main.profile'))
            
        elif action == 'add_category':
            name = request.form.get('category_name')
            category_type = request.form.get('category_type')
            
            if not name or not category_type:
                flash('Please provide both a category name and a type.', 'warning')
            else:
                try:
                    new_cat = Category(
                        name=name, 
                        type=category_type,
                        user_id=current_user.id,
                        icon='📁',
                        color='#3498db',
                        is_system=False
                    )
                    db.session.add(new_cat)
                    db.session.commit()
                    flash(f'Category "{name}" ({category_type}) added successfully!', 'success')
                except Exception as e:
                    db.session.rollback()
                    flash('An error occurred while saving the category.', 'danger')
            return redirect(url_for('main.profile'))
        
        elif action == 'delete_category':
            cat_id = request.form.get('category_id')
            cat = Category.query.filter_by(id=cat_id, user_id=current_user.id).first()
            if cat:
                db.session.delete(cat)
                db.session.commit()
                flash('Category removed.', 'info')
            return redirect(url_for('main.profile'))

        elif action == 'change_password':
            new_pass = request.form.get('new_password')
            if new_pass:
                current_user.set_password(new_pass)
                db.session.commit()
                flash('Password updated! Please log in again.', 'success')
                logout_user()
                # Use 'auth.login' or whatever your login route is named
                return redirect(url_for('auth.login'))

        elif action == 'delete_account':
            # 1. Delete all associated user data first
            Transaction.query.filter_by(user_id=current_user.id).delete()
            Category.query.filter_by(user_id=current_user.id).all()
            
            # 2. Get the ACTUAL User object, not the Proxy
            user_to_delete = current_user._get_current_object()
            
            # 3. Log them out BEFORE deleting the record
            logout_user() 
            
            # 4. Delete the actual user record
            db.session.delete(user_to_delete)
            db.session.commit()
            
            flash('Your account and all associated data have been deleted.', 'warning')
            return redirect(url_for('main.index'))

    # 3. Final Return for GET requests (and if POST falls through)
    return render_template('profile.html', 
                           title='Profile', 
                           stats=stats, 
                           categories=categories)