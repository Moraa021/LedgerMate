from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User, Category
from app.extensions import db
from datetime import datetime
from flask_wtf import FlaskForm

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        phone_number = request.form.get('phone_number', '').strip()
        business_name = request.form.get('business_name', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validation
        errors = []
        
        if not phone_number:
            errors.append('Phone number is required')
        elif not phone_number.isdigit() or len(phone_number) != 10:
            errors.append('Phone number must be 10 digits')
        
        if not password:
            errors.append('Password is required')
        elif len(password) < 6:
            errors.append('Password must be at least 6 characters')
        
        if password != confirm_password:
            errors.append('Passwords do not match')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('auth/register.html')
        
        # Check if user exists
        existing_user = User.query.filter_by(phone_number=phone_number).first()
        if existing_user:
            flash('Phone number already registered', 'error')
            return render_template('auth/register.html')
        
        # Create new user
        user = User(
            phone_number=phone_number,
            business_name=business_name if business_name else None,
            language=session.get('language', 'en')
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        # Create default categories for user
        create_default_categories(user)
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        phone_number = request.form.get('phone_number')
        password = request.form.get('password')
        remember = request.form.get('remember', False)
        
        user = User.query.filter_by(phone_number=phone_number).first()
        
        if user and user.check_password(password):
            login_user(user, remember=remember)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            # Update session language from user preference
            session['language'] = user.language
            
            next_page = request.args.get('next')
            flash(f'Welcome back, {user.business_name or "User"}!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('main.dashboard'))
        else:
            flash('Invalid phone number or password', 'error')
    
    return render_template('auth/login.html',form=FlaskForm())

@bp.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('main.index'))

def create_default_categories(user):
    """Create default categories for a new user"""
    default_categories = [
        # Income categories
        {'name': 'Sales', 'name_sw': 'Mauzo', 'type': 'income', 'icon': '💰', 'color': '#27ae60', 'is_system': True},
        {'name': 'Services', 'name_sw': 'Huduma', 'type': 'income', 'icon': '🛠️', 'color': '#2980b9', 'is_system': True},
        {'name': 'M-Pesa Income', 'name_sw': 'Mapato M-Pesa', 'type': 'income', 'icon': '📱', 'color': '#16a085', 'is_system': True},
        
        # Expense categories
        {'name': 'Inventory', 'name_sw': 'Bidhaa', 'type': 'expense', 'icon': '📦', 'color': '#e74c3c', 'is_system': True},
        {'name': 'Rent', 'name_sw': 'Kodi', 'type': 'expense', 'icon': '🏠', 'color': '#c0392b', 'is_system': True},
        {'name': 'Transport', 'name_sw': 'Usafiri', 'type': 'expense', 'icon': '🚗', 'color': '#f39c12', 'is_system': True},
        {'name': 'Utilities', 'name_sw': 'Huduma', 'type': 'expense', 'icon': '💡', 'color': '#d35400', 'is_system': True},
        {'name': 'Salaries', 'name_sw': 'Mishahara', 'type': 'expense', 'icon': '👥', 'color': '#8e44ad', 'is_system': True},
    ]
    
    for cat_data in default_categories:
        category = Category(user_id=user.id, **cat_data)
        db.session.add(category)
    
    db.session.commit()