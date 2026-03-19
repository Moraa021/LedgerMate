from app import create_app

# Create application instance
app = create_app('development')

if __name__ == '__main__':
    app.run(debug=True)