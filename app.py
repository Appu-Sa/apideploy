from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)

# Database Configuration for Cloud SQL PostgreSQL
# In production (Cloud Run), this will come from environment variables
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    print(f"DATABASE_URL found: {DATABASE_URL[:50]}...")
    print(f"Using database: {'PostgreSQL' if 'postgresql://' in DATABASE_URL else 'SQLite'}")
else:
    print("No DATABASE_URL found, using SQLite fallback")
    DATABASE_URL = 'sqlite:///fallback.db'

# Configure database connection
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Cloud SQL specific configurations
if DATABASE_URL and 'postgresql://' in DATABASE_URL:
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_timeout': 20,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
        'max_overflow': 0,
        'pool_size': 5
    }
    print("Using PostgreSQL configuration")
else:
    print("Using SQLite configuration")

# Initialize SQLAlchemy with error handling
try:
    db = SQLAlchemy(app)
    print("Database initialized successfully")
except Exception as e:
    print(f"Database initialization error: {e}")
    # Create a fallback SQLite configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///emergency.db'
    db = SQLAlchemy(app)
    print("Using emergency SQLite database")

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

# Configure CORS
CORS(app, origins=["*"], 
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

# Alternative manual CORS headers
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

@app.route('/')
def home():
    return "Welcome to Flask API with Cloud SQL PostgreSQL!"

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
            'database_type': 'Cloud SQL PostgreSQL' if 'postgresql://' in DATABASE_URL else 'SQLite',
            'environment': 'production' if 'cloudsql' in DATABASE_URL else 'development'
        })
    except Exception as e:
        print(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'database': 'disconnected',
            'error': str(e)
        }), 500

@app.route('/api/init-db', methods=['POST'])
def initialize_database():
    """Manual database initialization endpoint"""
    try:
        print("Manual database initialization requested")
        db.create_all()
        
        # Add sample data if no users exist
        if User.query.count() == 0:
            sample_users = [
                User(name="Alice", age=30, city="New York"),
                User(name="Bob", age=25, city="San Francisco"),
                User(name="Charlie", age=35, city="Chicago")
            ]
            
            for user in sample_users:
                db.session.add(user)
            
            db.session.commit()
            print("Sample data added successfully")
            
            return jsonify({
                'status': 'success',
                'message': 'Database initialized and sample data added',
                'users_created': len(sample_users)
            })
        else:
            return jsonify({
                'status': 'info',
                'message': 'Database already has data',
                'user_count': User.query.count()
            })
            
    except Exception as e:
        print(f"Database initialization failed: {e}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'Database initialization failed',
            'error': str(e)
        }), 500

@app.route('/api/users', methods=['GET'])
def get_users():
    """Get all users from database"""
    try:
        users = User.query.all()
        return jsonify([user.to_dict() for user in users])
    except Exception as e:
        print(f"Error fetching users: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/users', methods=['POST'])
def create_user():
    """Create a new user"""
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
        
        print(f"New user created: {new_user.name}")
        return jsonify(new_user.to_dict()), 201
        
    except Exception as e:
        print(f"Error creating user: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """Get user by ID"""
    try:
        user = User.query.get_or_404(user_id)
        return jsonify(user.to_dict())
    except Exception as e:
        print(f"Error fetching user {user_id}: {e}")
        return jsonify({'error': str(e)}), 404

@app.route('/api/data', methods=['GET'])
def get_data():
    """Legacy endpoint for compatibility"""
    data = {
        "name": "Alice",
        "age": 30,
        "city": "New York",
        "message": "This is sample data. Use /api/users for database operations.",
        "database_type": "Cloud SQL PostgreSQL" if 'postgresql://' in DATABASE_URL else "SQLite"
    }
    return jsonify(data)

@app.route('/api/debug', methods=['GET'])
def debug_info():
    """Debug endpoint to check database configuration"""
    try:
        # Get all environment variables that contain 'DATABASE'
        env_vars = {k: v for k, v in os.environ.items() if 'DATABASE' in k}
        
        return jsonify({
            'database_url': DATABASE_URL,
            'database_type': 'PostgreSQL' if DATABASE_URL and 'postgresql://' in DATABASE_URL else 'SQLite',
            'is_cloud_sql': 'cloudsql' in DATABASE_URL if DATABASE_URL else False,
            'environment': 'production' if DATABASE_URL and 'cloudsql' in DATABASE_URL else 'development',
            'sqlalchemy_url': app.config['SQLALCHEMY_DATABASE_URI'],
            'env_vars': env_vars,
            'all_env_count': len(os.environ)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
