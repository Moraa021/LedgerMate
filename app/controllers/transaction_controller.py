from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app.models import Transaction, Category
from app.extensions import db
from datetime import datetime
from sqlalchemy.orm import joinedload
import uuid
import json

# The url_prefix='/transactions' means all routes start with /transactions
bp = Blueprint('transactions', __name__, url_prefix='/transactions')

@bp.route('/')
@login_required
def transactions():
    """Renders the main transactions list page"""
    return render_template('transactions/transactions.html')

@bp.route('/api/list')
@login_required
def list_transactions():
    """API endpoint that the JavaScript calls to get data"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # Filters from JS
    t_type = request.args.get('type')
    payment_method = request.args.get('payment_method')
    search = request.args.get('search')

    # Base Query
    query = Transaction.query.options(joinedload(Transaction.category)).filter_by(
        user_id=current_user.id, 
        is_deleted=False
    )

    # Apply Filters
    if t_type and t_type != 'all':
        query = query.filter_by(type=t_type)
    if payment_method and payment_method != 'all':
        query = query.filter_by(payment_method=payment_method)
    if search:
        query = query.filter(Transaction.description.ilike(f'%{search}%'))

    paginated = query.order_by(Transaction.transaction_date.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    transactions_list = []
    for t in paginated.items:
        # Safe JSON parsing for M-Pesa codes
        info = t.additional_info or {}
        if isinstance(info, str):
            try: info = json.loads(info)
            except: info = {}
        
        transactions_list.append({
            'id': t.public_id,
            'type': t.type,
            'amount': float(t.amount),
            'category': t.category.name if t.category else 'Uncategorized',
            'payment_method': t.payment_method.capitalize(),
            'description': t.description,
            'date': t.transaction_date.strftime('%d %b %Y'),
            'mpesa_code': info.get('mpesa_code')
        })

    return jsonify({
        'success': True,
        'transactions': transactions_list,
        'pages': paginated.pages,
        'current_page': page
    })

@bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_transaction():
    """Handles adding new records"""
    if request.method == 'POST':
        try:
            # Note: Storing M-Pesa code in additional_info JSON field
            mpesa_code = request.form.get('mpesa_code')
            additional_info = {"mpesa_code": mpesa_code} if mpesa_code else {}
            
            new_tx = Transaction(
                public_id=str(uuid.uuid4()),
                user_id=current_user.id,
                type=request.form.get('type'),
                amount=float(request.form.get('amount')),
                category_id=request.form.get('category_id'),
                payment_method=request.form.get('payment_method'),
                description=request.form.get('description'),
                transaction_date=datetime.utcnow(),
                additional_info=additional_info
            )
            db.session.add(new_tx)
            db.session.commit()
            flash('Transaction Added!', 'success')
            return redirect(url_for('transactions.transactions'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')

    categories = Category.query.filter_by(user_id=current_user.id).all()
    return render_template('transactions/add_transaction.html', categories=categories)