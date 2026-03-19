from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app.models import Transaction, Category
from app.extensions import db
from datetime import datetime
import uuid

bp = Blueprint('transactions', __name__, url_prefix='/transactions')

@bp.route('/')
@login_required
def transactions():
    """List all transactions"""
    return render_template('transactions/transactions.html')

@bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_transaction():
    """Add new transaction"""
    if request.method == 'POST':
        try:
            # Get form data
            transaction_type = request.form.get('type')
            amount = request.form.get('amount')
            category_id = request.form.get('category_id')
            payment_method = request.form.get('payment_method')
            description = request.form.get('description')
            transaction_date = request.form.get('transaction_date')
            mpesa_code = request.form.get('mpesa_code')
            
            # Additional info as JSON
            additional_info = {}
            if payment_method == 'mpesa' and mpesa_code:
                additional_info['mpesa_code'] = mpesa_code
            
            # Parse date
            if transaction_date:
                trans_date = datetime.strptime(transaction_date, '%Y-%m-%d')
            else:
                trans_date = datetime.utcnow()
            
            # Create transaction
            transaction = Transaction(
                public_id=str(uuid.uuid4()),
                user_id=current_user.id,
                type=transaction_type,
                amount=amount,
                category_id=category_id,
                payment_method=payment_method,
                description=description,
                transaction_date=trans_date,
                additional_info=additional_info
            )
            
            db.session.add(transaction)
            db.session.commit()
            
            flash('Transaction added successfully!', 'success')
            return redirect(url_for('transactions.transactions'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding transaction: {str(e)}', 'error')
    
    # Get categories for form
    categories = Category.query.filter_by(
        user_id=current_user.id
    ).all()
    today_date = datetime.utcnow().strftime('%Y-%m-%d')
    
    return render_template('transactions/add_transaction.html', categories=categories,today=today_date)

@bp.route('/api/list')
@login_required
def list_transactions():
    """API endpoint to list transactions with filtering"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    transaction_type = request.args.get('type')
    category_id = request.args.get('category_id')
    payment_method = request.args.get('payment_method')
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    search = request.args.get('search')
    
    # Build query
    query = Transaction.query.filter_by(
        user_id=current_user.id,
        is_deleted=False
    )
    
    # Apply filters
    if transaction_type:
        query = query.filter_by(type=transaction_type)
    
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    if payment_method:
        query = query.filter_by(payment_method=payment_method)
    
    if from_date:
        query = query.filter(Transaction.transaction_date >= datetime.strptime(from_date, '%Y-%m-%d'))
    
    if to_date:
        query = query.filter(Transaction.transaction_date <= datetime.strptime(to_date, '%Y-%m-%d'))
    
    if search:
        query = query.filter(Transaction.description.ilike(f'%{search}%'))
    
    # Order by date (newest first)
    query = query.order_by(Transaction.transaction_date.desc())
    
    # Paginate
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Format transactions
    transactions = []
    for t in paginated.items:
        category = Category.query.get(t.category_id)
        transactions.append({
            'id': t.public_id,
            'type': t.type,
            'amount': float(t.amount),
            'category': category.name if category else 'Unknown',
            'payment_method': t.payment_method,
            'description': t.description,
            'date': t.transaction_date.strftime('%Y-%m-%d %H:%M'),
            'mpesa_code': t.mpesa_code
        })
    
    return jsonify({
        'success': True,
        'transactions': transactions,
        'total': paginated.total,
        'page': page,
        'pages': paginated.pages,
        'per_page': per_page
    })

@bp.route('/api/<transaction_id>')
@login_required
def get_transaction(transaction_id):
    """Get single transaction details"""
    transaction = Transaction.query.filter_by(
        public_id=transaction_id,
        user_id=current_user.id,
        is_deleted=False
    ).first_or_404()
    
    category = Category.query.get(transaction.category_id)
    
    return jsonify({
        'success': True,
        'transaction': {
            'id': transaction.public_id,
            'type': transaction.type,
            'amount': float(transaction.amount),
            'category_id': transaction.category_id,
            'category': category.name if category else 'Unknown',
            'payment_method': transaction.payment_method,
            'description': transaction.description,
            'date': transaction.transaction_date.strftime('%Y-%m-%d'),
            'mpesa_code': transaction.mpesa_code,
            'additional_info': transaction.additional_info
        }
    })

@bp.route('/api/<transaction_id>', methods=['PUT'])
@login_required
def update_transaction(transaction_id):
    """Update transaction"""
    transaction = Transaction.query.filter_by(
        public_id=transaction_id,
        user_id=current_user.id,
        is_deleted=False
    ).first_or_404()
    
    data = request.get_json()
    
    # Update fields
    if 'type' in data:
        transaction.type = data['type']
    if 'amount' in data:
        transaction.amount = data['amount']
    if 'category_id' in data:
        transaction.category_id = data['category_id']
    if 'payment_method' in data:
        transaction.payment_method = data['payment_method']
    if 'description' in data:
        transaction.description = data['description']
    if 'mpesa_code' in data:
        transaction.mpesa_code = data['mpesa_code']
    if 'transaction_date' in data:
        transaction.transaction_date = datetime.strptime(data['transaction_date'], '%Y-%m-%d')
    
    transaction.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Transaction updated'})

@bp.route('/api/<transaction_id>', methods=['DELETE'])
@login_required
def delete_transaction(transaction_id):
    """Soft delete transaction"""
    transaction = Transaction.query.filter_by(
        public_id=transaction_id,
        user_id=current_user.id
    ).first_or_404()
    
    transaction.is_deleted = True
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Transaction deleted'})