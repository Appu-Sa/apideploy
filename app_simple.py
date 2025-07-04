from flask import Flask, jsonify, request
from flask_cors import CORS
import os

app = Flask(__name__)

# Configure CORS
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
    return "Welcome to the simple API!"

@app.route('/api/data', methods=['GET'])
def get_data():
    data = {
        "name": "Alice",
        "age": 30,
        "city": "New York",
        "message": "API is working successfully!"
    }
    return jsonify(data)

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'message': 'API is running'
    })

# Simple in-memory data store for testing
users_data = [
    {"id": 1, "name": "Alice", "age": 30, "city": "New York"},
    {"id": 2, "name": "Bob", "age": 25, "city": "San Francisco"},
    {"id": 3, "name": "Charlie", "age": 35, "city": "Chicago"}
]

@app.route('/api/users', methods=['GET'])
def get_users():
    return jsonify(users_data)

@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    user = next((u for u in users_data if u['id'] == user_id), None)
    if user:
        return jsonify(user)
    return jsonify({'error': 'User not found'}), 404

@app.route('/api/users', methods=['POST'])
def create_user():
    try:
        data = request.get_json()
        
        if not data or not all(key in data for key in ['name', 'age', 'city']):
            return jsonify({'error': 'Missing required fields: name, age, city'}), 400
        
        new_user = {
            'id': len(users_data) + 1,
            'name': data['name'],
            'age': data['age'],
            'city': data['city']
        }
        
        users_data.append(new_user)
        return jsonify(new_user), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
