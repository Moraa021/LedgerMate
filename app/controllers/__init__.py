# This file makes the controllers directory a Python package
from .auth_controller import bp as auth_bp
from .main_controller import bp as main_bp
from .transaction_controller import bp as transactions_bp
from .report_controller import bp as reports_bp
from .category_controller import bp as categories_bp

# Export all blueprints
__all__ = ['auth_bp', 'main_bp', 'transactions_bp', 'reports_bp', 'categories_bp']