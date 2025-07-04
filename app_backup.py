from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import os
import logging

# Configure logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Database Configuration for Cloud SQL PostgreSQL
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///local.db')

# Configure database connection
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Cloud SQL specific configurations
if 'postgresql://' in DATABASE_URL:
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_timeout': 20,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
        'max_overflow': 0,
        'pool_size': 5
    }
    logger.info("Using PostgreSQL configuration")
else:
    logger.info("Using SQLite configuration")

db = SQLAlchemy(app)

# Database Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    city = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'age': self.age,
            'city': self.city,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# Configure CORS - replace with your Next.js domain in production
CORS(app, origins=["*"], 
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

# Alternative manual CORS headers (backup)
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

@app.route('/')
def home():
    return "Welcome to the simple API with Database!"

# Get all users from database
@app.route('/api/users', methods=['GET'])
def get_users():
    try:
        users = User.query.all()
        return jsonify([user.to_dict() for user in users])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Create a new user
@app.route('/api/users', methods=['POST'])
def create_user():
    try:
        data = request.get_json()
        
        if not data or not all(key in data for key in ['name', 'age', 'city']):
            return jsonify({'error': 'Missing required fields: name, age, city'}), 400
        
        new_user = User(
            name=data['name'],
            age=data['age'],
            city=data['city']
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        return jsonify(new_user.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Get user by ID
@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    try:
        user = User.query.get_or_404(user_id)
        return jsonify(user.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 404

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint to verify database connection"""
    try:
        # Try to query the database
        user_count = User.query.count()
        
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'user_count': user_count,
            'database_url': 'Cloud SQL' if '/cloudsql/' in DATABASE_URL else 'Local/Other'
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'database': 'disconnected',
            'error': str(e)
        }), 500

# Initialize database tables and sample data
def init_db():
    """Initialize database tables and add sample data if needed"""
    try:
        logger.info("Initializing database...")
        db.create_all()
        logger.info("Database tables created successfully")
        
        # Add sample data if no users exist
        if User.query.count() == 0:
            logger.info("Adding sample data...")
            sample_users = [
                User(name="Alice", age=30, city="New York"),
                User(name="Bob", age=25, city="San Francisco"),
                User(name="Charlie", age=35, city="Chicago")
            ]
            
            for user in sample_users:
                db.session.add(user)
            
            db.session.commit()
            logger.info("Sample data added successfully")
        else:
            logger.info("Database already has data, skipping sample data creation")
            
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        db.session.rollback()
        raise

# Initialize database when the app starts
try:
    with app.app_context():
        init_db()
except Exception as e:
    logger.error(f"Failed to initialize database on startup: {e}")
    # Don't fail completely, allow the app to start

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)