from flask import Flask, request, session
from config import config
from app.extensions import db, login_manager, migrate, csrf
import os

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Ensure instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    
    # Language preference middleware
    @app.before_request
    def set_language():
        """Set language preference from session, cookie, or default"""
        if 'language' not in session:
            # Try to get from cookie, default to English
            session['language'] = request.cookies.get('language', 'en')
    
    # Register blueprints
    from app.controllers import auth_controller, transaction_controller, \
        report_controller, category_controller, main_controller
    
    app.register_blueprint(auth_controller.bp)
    app.register_blueprint(transaction_controller.bp)
    app.register_blueprint(report_controller.bp)
    app.register_blueprint(category_controller.bp)
    app.register_blueprint(main_controller.bp)
   
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app