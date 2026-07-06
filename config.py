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

    # --- DARAJA (M-PESA) CONFIG ---
    # 'sandbox' while developing/testing, 'production' once Safaricom approves
    # your go-live application.
    MPESA_ENV = os.environ.get('MPESA_ENV', 'sandbox')
    MPESA_CONSUMER_KEY = os.environ.get('MPESA_CONSUMER_KEY')
    MPESA_CONSUMER_SECRET = os.environ.get('MPESA_CONSUMER_SECRET')
    MPESA_SHORTCODE = os.environ.get('MPESA_SHORTCODE')  # Paybill or Till number
    MPESA_PASSKEY = os.environ.get('MPESA_PASSKEY')

    # Public base URL Safaricom can reach for callbacks, e.g.
    # https://your-app.vercel.app or an ngrok URL in development.
    MPESA_CALLBACK_BASE_URL = os.environ.get('MPESA_CALLBACK_BASE_URL', '')

    # Optional: if you're running LedgerMate for a single business (not
    # multi-tenant), set this to that user's numeric ID so C2B payments with
    # no recognizable account reference still get posted to the ledger.
    MPESA_DEFAULT_USER_ID = os.environ.get('MPESA_DEFAULT_USER_ID')

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