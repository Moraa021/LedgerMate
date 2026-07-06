from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db, login_manager
import uuid

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    """User model for MSE owners"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(50), unique=True, default=lambda: str(uuid.uuid4()))
    phone_number = db.Column(db.String(20), unique=True, nullable=False)
    business_name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True, nullable=True)
    password_hash = db.Column(db.String(200), nullable=False)
    
    # Preferences
    language = db.Column(db.String(10), default='en')
    currency = db.Column(db.String(10), default='KES')
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    transactions = db.relationship('Transaction', backref='user', lazy='dynamic',
                                   cascade='all, delete-orphan')
    categories = db.relationship('Category', backref='user', lazy='dynamic',
                                 cascade='all, delete-orphan')
    inventory_items = db.relationship('InventoryItem', backref='user', lazy='dynamic',
                                      cascade='all, delete-orphan')
    liabilities = db.relationship('Liability', backref='user', lazy='dynamic',
                                  cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.phone_number}>'

class Category(db.Model):
    """Transaction categories (income/expense)"""
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    name_sw = db.Column(db.String(50))  # Swahili translation
    type = db.Column(db.String(20), nullable=False)  # 'income' or 'expense'
    icon = db.Column(db.String(50), default='📁')
    color = db.Column(db.String(20), default='#3498db')
    
    # System categories (True) vs user-created (False)
    is_system = db.Column(db.Boolean, default=False)
    
    # User relationship (NULL for system categories)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    transactions = db.relationship('Transaction', backref='category', lazy='dynamic')
    
    __table_args__ = (
        db.UniqueConstraint('name', 'user_id', name='unique_category_per_user'),
    )
    
    def to_dict(self, lang='en'):
        return {
            'id': self.id,
            'name': self.name_sw if lang == 'sw' and self.name_sw else self.name,
            'type': self.type,
            'icon': self.icon,
            'color': self.color
        }
    
    def __repr__(self):
        return f'<Category {self.name}>'

class Transaction(db.Model):
    """Financial transactions (income/expense)"""
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(50), unique=True, default=lambda: str(uuid.uuid4()))
    
    # Transaction details
    type = db.Column(db.String(20), nullable=False)  # 'income' or 'expense'
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_method = db.Column(db.String(20), nullable=False)  # 'cash', 'mpesa', 'other'
    description = db.Column(db.Text)
    
    # M-Pesa specific (manual entries, e.g. cash-style M-Pesa till payments)
    mpesa_code = db.Column(db.String(50))
    mpesa_receipt = db.Column(db.String(100))

    # Paystack specific - populated automatically by the webhook, never typed by hand
    paystack_reference = db.Column(db.String(100), unique=True, nullable=True)
    paystack_status = db.Column(db.String(20))  # 'success', 'pending', 'failed'
    payer_email = db.Column(db.String(120))
    payer_name = db.Column(db.String(120))
    
    # Additional details (JSON field for flexibility)
    additional_info = db.Column(db.JSON)
    
    # Dates
    transaction_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Soft delete
    is_deleted = db.Column(db.Boolean, default=False)
    
    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    
    def to_dict(self):
        return {
            'id': self.public_id,
            'type': self.type,
            'amount': float(self.amount),
            'payment_method': self.payment_method,
            'description': self.description,
            'mpesa_code': self.mpesa_code,
            'paystack_reference': self.paystack_reference,
            'paystack_status': self.paystack_status,
            'category_id': self.category_id,
            'transaction_date': self.transaction_date.isoformat() if self.transaction_date else None,
            'additional_info': self.additional_info
        }
    
    def __repr__(self):
        return f'<Transaction {self.type} {self.amount}>'

class SyncQueue(db.Model):
    """Offline sync queue"""
    __tablename__ = 'sync_queue'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    operation = db.Column(db.String(20), nullable=False)  # 'create', 'update', 'delete'
    entity_type = db.Column(db.String(50), nullable=False)  # 'transaction', 'category'
    entity_id = db.Column(db.String(50))  # Public ID of entity
    payload = db.Column(db.JSON)  # Operation data
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    synced_at = db.Column(db.DateTime)
    retry_count = db.Column(db.Integer, default=0)
    
    def __repr__(self):
        return f'<SyncQueue {self.operation} {self.entity_type}>'

class InventoryItem(db.Model):
    """Stock items owned by an MSE"""
    __tablename__ = 'inventory_items'

    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(50), unique=True, default=lambda: str(uuid.uuid4()))

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    name = db.Column(db.String(120), nullable=False)
    sku = db.Column(db.String(50))
    category = db.Column(db.String(60))

    quantity_on_hand = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    unit_cost = db.Column(db.Numeric(10, 2), nullable=False, default=0)     # what you pay
    unit_price = db.Column(db.Numeric(10, 2), nullable=False, default=0)    # what you sell for
    reorder_level = db.Column(db.Numeric(12, 2), default=5)

    is_deleted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    movements = db.relationship('InventoryMovement', backref='item', lazy='dynamic',
                                cascade='all, delete-orphan')

    @property
    def stock_value(self):
        return float(self.quantity_on_hand) * float(self.unit_cost)

    @property
    def is_low_stock(self):
        return float(self.quantity_on_hand) <= float(self.reorder_level or 0)

    def to_dict(self):
        return {
            'id': self.public_id,
            'name': self.name,
            'sku': self.sku,
            'category': self.category,
            'quantity_on_hand': float(self.quantity_on_hand),
            'unit_cost': float(self.unit_cost),
            'unit_price': float(self.unit_price),
            'reorder_level': float(self.reorder_level or 0),
            'stock_value': self.stock_value,
            'is_low_stock': self.is_low_stock
        }

    def __repr__(self):
        return f'<InventoryItem {self.name}>'


class InventoryMovement(db.Model):
    """Stock in/out history for an inventory item"""
    __tablename__ = 'inventory_movements'

    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('inventory_items.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    movement_type = db.Column(db.String(20), nullable=False)  # 'restock', 'sale', 'adjustment'
    quantity = db.Column(db.Numeric(12, 2), nullable=False)     # always positive; direction from movement_type
    unit_cost = db.Column(db.Numeric(10, 2))
    unit_price = db.Column(db.Numeric(10, 2))
    notes = db.Column(db.String(255))
    transaction_public_id = db.Column(db.String(50))  # linked ledger transaction, if any

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'movement_type': self.movement_type,
            'quantity': float(self.quantity),
            'unit_cost': float(self.unit_cost) if self.unit_cost is not None else None,
            'unit_price': float(self.unit_price) if self.unit_price is not None else None,
            'notes': self.notes,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M')
        }

    def __repr__(self):
        return f'<InventoryMovement {self.movement_type} {self.quantity}>'


class Liability(db.Model):
    """Loans / payables owed by the business - used for the balance sheet"""
    __tablename__ = 'liabilities'

    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(50), unique=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    name = db.Column(db.String(120), nullable=False)
    liability_type = db.Column(db.String(20), default='other')  # 'loan', 'payable', 'other'
    amount = db.Column(db.Numeric(12, 2), nullable=False, default=0)

    is_deleted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.public_id,
            'name': self.name,
            'type': self.liability_type,
            'amount': float(self.amount)
        }

    def __repr__(self):
        return f'<Liability {self.name} {self.amount}>'


class PaymentRequest(db.Model):
    """
    A Paystack checkout that was generated from the app. The reference here
    IS the Paystack transaction reference. When the webhook confirms payment,
    it looks up this row to know which user/category/description to file the
    resulting Transaction under - no manual entry needed anywhere.
    """
    __tablename__ = 'payment_requests'

    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(60), unique=True, default=lambda: f"lm-{uuid.uuid4().hex[:20]}")

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)

    amount = db.Column(db.Numeric(10, 2), nullable=False)
    description = db.Column(db.String(255))
    customer_email = db.Column(db.String(120))
    customer_name = db.Column(db.String(120))

    status = db.Column(db.String(20), default='pending')  # 'pending', 'success', 'failed'
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<PaymentRequest {self.reference} {self.status}>'


class ChatHistory(db.Model):
    """Chatbot conversation history"""
    __tablename__ = 'chat_history'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    session_id = db.Column(db.String(100))
    
    message = db.Column(db.Text)
    response = db.Column(db.Text)
    intent = db.Column(db.String(50))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ChatHistory {self.session_id}>'