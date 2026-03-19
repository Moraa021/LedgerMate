from app import create_app
import os

# Create application instance
app = create_app(os.getenv('FLASK_ENV', 'production'))

# This is critical for Vercel
app = app

if __name__ == '__main__':
    app.run()