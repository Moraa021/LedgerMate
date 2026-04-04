import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Basic Flask config
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # --- DATABASE CONFIG START ---
    raw_db_url = os.environ.get('DATABASE_URL')
    
    # Fix for Vercel/Render: SQLAlchemy requires 'postgresql://' instead of 'postgres://'
    if raw_db_url and raw_db_url.startswith("postgres://"):
        raw_db_url = raw_db_url.replace("postgres://", "postgresql://", 1)
    
    SQLALCHEMY_DATABASE_URI = raw_db_url or 'sqlite:///ledgermate.db'
    # --- DATABASE CONFIG END ---

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session config
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    REMEMBER_COOKIE_DURATION = timedelta(days=30)
    
    # File uploads (Note: Vercel's filesystem is read-only, 
    # so uploads won't save permanently unless using AWS S3/Cloudinary)
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  
    UPLOAD_FOLDER = os.path.join('instance', 'uploads')
    
    # App specific
    ITEMS_PER_PAGE = 20
    DEFAULT_CURRENCY = 'KES'
    
    # Supported languages
    LANGUAGES = {
        'en': 'English',
        'sw': 'Kiswahili'
    }

class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    # In production, ensure we use the environment's SECRET_KEY
    SECRET_KEY = os.environ.get('SECRET_KEY')

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

# Select config based on environment
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}