from flask import Blueprint, request, jsonify, current_app
import jwt
import datetime

auth_bp = Blueprint('auth', __name__)

# Example users - for demo purposes; in prod, use DB!
USERS = {
    "admin1": {"password": "adminpass", "role": "admin"},
    "manager1": {"password": "managerpass", "role": "manager"},
    "staff1": {"password": "staffpass", "role": "staff"},
    "guest1": {"password": "guestpass", "role": "guest"}
}

def generate_token(username, role):
    payload = {
        'username': username,
        'role': role,
        'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)
    }
    return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    user = USERS.get(username)
    if not user or user['password'] != password:
        return jsonify({"message": "Invalid credentials"}), 401
    token = generate_token(username, user['role'])
    return jsonify({"token":token})