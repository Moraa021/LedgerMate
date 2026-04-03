from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app.models import Transaction, Category
from app.extensions import db
from datetime import datetime
from sqlalchemy.orm import joinedload
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
    if request.method == 'POST':
        try:
            # 1. Capture Form Data
            transaction_type = request.form.get('type') 
            amount = float(request.form.get('amount', 0))
            category_id = request.form.get('category_id')
            payment_method = request.form.get('payment_method')
            description = request.form.get('description', '')
            transaction_date_str = request.form.get('transaction_date')
            mpesa_code = request.form.get('mpesa_code')

            # 2. Date Parsing
            trans_date = datetime.strptime(transaction_date_str, '%Y-%m-%d') if transaction_date_str else datetime.utcnow()

            # 3. Handle M-Pesa Code & Additional Info
            # We store the M-Pesa code inside the additional_info JSON field
            add_info_content = request.form.get('additional_info', '')
            additional_info = {"notes": add_info_content}
            
            if payment_method == 'mpesa' and mpesa_code:
                additional_info['mpesa_code'] = mpesa_code

            # 4. Create and Save Transaction
            new_transaction = Transaction(
                public_id=str(uuid.uuid4()),
                user_id=current_user.id,
                type=transaction_type,
                amount=amount,
                category_id=category_id,
                payment_method=payment_method,
                description=description, # Primary description field
                transaction_date=trans_date,
                additional_info=additional_info, # JSON field for codes/notes
                is_deleted=False
            )

            db.session.add(new_transaction)
            db.session.commit()

            flash('Transaction recorded!', 'success')
            return redirect(url_for('main.dashboard'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')

    categories = Category.query.filter_by(user_id=current_user.id).all()
    today = datetime.utcnow().strftime('%Y-%m-%d')
    
    return render_template('transactions/add_transaction.html', categories=categories, today=today)

@bp.route('/api/list')
@login_required
def list_transactions():
    """API endpoint to list transactions with optimized filtering"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Get parameters from request
    transaction_type = request.args.get('type')
    category_id = request.args.get('category_id')
    payment_method = request.args.get('payment_method')
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    search = request.args.get('search')
    
    # Build query with joinedload for performance
    query = Transaction.query.options(joinedload(Transaction.category)).filter_by(
        user_id=current_user.id,
        is_deleted=False
    )
    
    # Apply filters - checking for 'all' to prevent zero-result bugs
    if transaction_type and transaction_type != 'all':
        query = query.filter_by(type=transaction_type)
    
    if category_id and category_id != 'all':
        query = query.filter_by(category_id=category_id)
    
    if payment_method and payment_method != 'all':
        query = query.filter_by(payment_method=payment_method)
    
    try:
        if from_date:
            query = query.filter(Transaction.transaction_date >= datetime.strptime(from_date, '%Y-%m-%d'))
        if to_date:
            query = query.filter(Transaction.transaction_date <= datetime.strptime(to_date, '%Y-%m-%d'))
    except ValueError:
        pass # Ignore malformed dates
    
    if search:
        query = query.filter(Transaction.description.ilike(f'%{search}%'))
    
    # Order and paginate
    paginated = query.order_by(Transaction.transaction_date.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Format transactions efficiently
    transactions_list = []
    for t in paginated.items:
        transactions_list.append({
            'id': t.public_id,
            'type': t.type,
            'amount': float(t.amount),
            'category': t.category.name if t.category else 'Unknown',
            'payment_method': t.payment_method,
            'description': t.description,
            'date': t.transaction_date.strftime('%d %b %Y %H:%M'),
            'mpesa_code': getattr(t, 'mpesa_code', None)
        })
    
    return jsonify({
        'success': True,
        'transactions': transactions_list,
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
    
    return jsonify({
        'success': True,
        'transaction': {
            'id': transaction.public_id,
            'type': transaction.type,
            'amount': float(transaction.amount),
            'category_id': transaction.category_id,
            'category': transaction.category.name if transaction.category else 'Unknown',
            'payment_method': transaction.payment_method,
            'description': transaction.description,
            'date': transaction.transaction_date.strftime('%Y-%m-%d'),
            'mpesa_code': getattr(transaction, 'mpesa_code', None),
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
    
    # Update fields safely
    if 'type' in data:
        transaction.type = data['type']
    if 'amount' in data:
        transaction.amount = float(data['amount'])
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