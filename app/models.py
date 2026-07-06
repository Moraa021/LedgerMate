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
    
    # M-Pesa specific
    mpesa_code = db.Column(db.String(50))
    mpesa_receipt = db.Column(db.String(100))
    
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

    # Optional link to an inventory item, set automatically when a transaction
    # is generated from a stock sale/purchase (see InventoryService)
    inventory_item_id = db.Column(db.Integer, db.ForeignKey('inventory_items.id'), nullable=True)

    # Marks whether this transaction represents Cost of Goods Sold, so the
    # P&L service can separate it from ordinary operating expenses
    is_cogs = db.Column(db.Boolean, default=False)

    # Marks an inventory purchase (buying stock). This is real cash leaving
    # the business (counted in the Balance Sheet's cash position) but is NOT
    # an operating expense in the P&L - it converts cash into an inventory
    # asset. Its cost only hits the P&L later, as COGS, when the stock sells.
    is_inventory_purchase = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'id': self.public_id,
            'type': self.type,
            'amount': float(self.amount),
            'payment_method': self.payment_method,
            'description': self.description,
            'mpesa_code': self.mpesa_code,
            'category_id': self.category_id,
            'transaction_date': self.transaction_date.isoformat() if self.transaction_date else None,
            'additional_info': self.additional_info,
            'is_cogs': self.is_cogs
        }
    
    def __repr__(self):
        return f'<Transaction {self.type} {self.amount}>'


class InventoryItem(db.Model):
    """Stock keeping unit tracked for inventory management"""
    __tablename__ = 'inventory_items'

    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(50), unique=True, default=lambda: str(uuid.uuid4()))

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    name = db.Column(db.String(150), nullable=False)
    sku = db.Column(db.String(50))
    unit = db.Column(db.String(20), default='pcs')  # pcs, kg, litre, etc.

    # Weighted-average cost per unit (updated on every purchase)
    unit_cost = db.Column(db.Numeric(10, 2), default=0)
    selling_price = db.Column(db.Numeric(10, 2), default=0)

    quantity_on_hand = db.Column(db.Numeric(12, 2), default=0)
    reorder_level = db.Column(db.Numeric(12, 2), default=0)

    is_active = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    movements = db.relationship('StockMovement', backref='item', lazy='dynamic',
                                 cascade='all, delete-orphan')

    __table_args__ = (
        db.UniqueConstraint('sku', 'user_id', name='unique_sku_per_user'),
    )

    @property
    def stock_value(self):
        return float(self.quantity_on_hand or 0) * float(self.unit_cost or 0)

    @property
    def is_low_stock(self):
        return float(self.quantity_on_hand or 0) <= float(self.reorder_level or 0)

    def to_dict(self):
        return {
            'id': self.public_id,
            'name': self.name,
            'sku': self.sku,
            'unit': self.unit,
            'unit_cost': float(self.unit_cost or 0),
            'selling_price': float(self.selling_price or 0),
            'quantity_on_hand': float(self.quantity_on_hand or 0),
            'reorder_level': float(self.reorder_level or 0),
            'stock_value': self.stock_value,
            'is_low_stock': self.is_low_stock,
            'is_active': self.is_active
        }

    def __repr__(self):
        return f'<InventoryItem {self.name} qty={self.quantity_on_hand}>'


class StockMovement(db.Model):
    """Audit trail of every stock in/out event"""
    __tablename__ = 'stock_movements'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('inventory_items.id'), nullable=False)

    movement_type = db.Column(db.String(20), nullable=False)  # 'purchase', 'sale', 'adjustment'
    quantity = db.Column(db.Numeric(12, 2), nullable=False)  # always positive
    unit_cost = db.Column(db.Numeric(10, 2), nullable=False)  # cost per unit at time of movement

    # Linked ledger entry created for this movement (income for sale, expense for purchase)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), nullable=True)

    notes = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<StockMovement {self.movement_type} {self.quantity}>'


class MpesaTransaction(db.Model):
    """Staging table for Daraja (M-Pesa) payment events, before/while they are
    reconciled into a ledger Transaction."""
    __tablename__ = 'mpesa_transactions'

    id = db.Column(db.Integer, primary_key=True)

    # Nullable because C2B payments may arrive before we know which user they
    # belong to (matched via account reference / phone number)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # 'stk_push' (app-initiated) or 'c2b' (customer paid the till/paybill directly)
    source = db.Column(db.String(20), nullable=False)

    merchant_request_id = db.Column(db.String(100))
    checkout_request_id = db.Column(db.String(100), index=True)

    phone_number = db.Column(db.String(20))
    amount = db.Column(db.Numeric(10, 2))

    mpesa_receipt = db.Column(db.String(50), unique=True)

    status = db.Column(db.String(20), default='pending')  # pending, success, failed
    result_code = db.Column(db.String(10))
    result_desc = db.Column(db.String(255))

    raw_callback = db.Column(db.JSON)

    # Set once we've posted this to the ledger, to guarantee idempotency
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<MpesaTransaction {self.source} {self.status} {self.amount}>'

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