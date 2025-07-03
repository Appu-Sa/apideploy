from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    return "Welcome to the simple API!"

@app.route('/api/data', methods=['GET'])
def get_data():
    data = {
        "name": "Alice",
        "age": 30,
        "city": "New York"
    }
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)