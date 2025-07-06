from flask import Flask, render_template, request, redirect, url_for, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import uuid
from datetime import datetime, timezone, timedelta
from functools import wraps
from flask_mysqldb import MySQL
from bookings import booking_bp
from add_guest import adding_guest
from add_room import adding_room
from check_availability import check_availabilities
from book_room import booking_room
from database import mysql, init_db
from auth import auth_bp
app = Flask(__name__)

# MySQL Configuration
init_db(app)
app.config['SECRET_KEY'] = 'supersecretkey'

# # Configuration
# app.config['SECRET_KEY'] = 'your_secret_key'
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///Database.db'
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# # Database setup
# db = SQLAlchemy(app)

# class User(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     public_id = db.Column(db.String(50), unique=True)
#     name = db.Column(db.String(100))
#     email = db.Column(db.String(70), unique=True)
#     password = db.Column(db.String(80))

# # Token required decorator
# def token_required(f):
#     @wraps(f)
#     def decorated(*args, **kwargs):
#         token = request.cookies.get('jwt_token')

#         if not token:
#             return jsonify({'message': 'Token is missing!'}), 401

#         try:
#             data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
#             current_user = User.query.filter_by(public_id=data['public_id']).first()
#         except:
#             return jsonify({'message': 'Token is invalid!'}), 401

#         return f(current_user, *args, **kwargs)

#     return decorated

# @app.route('/')
# def home():
#     return render_template('login.html')

# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     if request.method == 'POST':
#         email = request.form['email']
#         password = request.form['password']
#         user = User.query.filter_by(email=email).first()

#         if not user or not check_password_hash(user.password, password):
#             return jsonify({'message': 'Invalid email or password'}), 401

#         token = jwt.encode({'public_id': user.public_id, 'exp': datetime.now(timezone.utc) + timedelta(hours=1)}, 
#                            app.config['SECRET_KEY'], algorithm="HS256")

#         response = make_response(redirect(url_for('dashboard')))
#         response.set_cookie('jwt_token', token)

#         return response

#     return render_template('login.html')

# @app.route('/signup', methods=['GET', 'POST'])
# def register():
#     if request.method == 'POST':
#         name = request.form['name']
#         email = request.form['email']
#         password = request.form['password']

#         existing_user = User.query.filter_by(email=email).first()
#         if existing_user:
#             return jsonify({'message': 'User already exists. Please login.'}), 400

#         hashed_password = generate_password_hash(password)
#         new_user = User(public_id=str(uuid.uuid4()), name=name, email=email, password=hashed_password)

#         db.session.add(new_user)
#         db.session.commit()

#         return redirect(url_for('login'))

#     return render_template('register.html')

# @app.route('/dashboard')
# @token_required
# def dashboard(current_user):
#     return f"Welcome {current_user.name}! You are logged in."










# Role hierarchy (should match that in role_auth.py or auth.py)
ROLE_HIERARCHY = ["guest", "staff", "manager", "admin"]

# Role-protected decorator (same as before, for demo)
def role_required(required_role):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return jsonify({'message': 'Missing or invalid token'}), 401
            token = auth_header.split(" ")[1]
            try:
                decoded = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
                user_role = decoded.get('role')
                if ROLE_HIERARCHY.index(user_role) < ROLE_HIERARCHY.index(required_role):
                    return jsonify({'message': f'Insufficient privileges. Your role: {user_role}'}), 403
                request.user = decoded
            except jwt.ExpiredSignatureError:
                return jsonify({'message': 'Token expired'}), 401
            except Exception as e:
                return jsonify({'message': f'Invalid token: {str(e)}'}), 401
            return f(*args, **kwargs)
        return wrapper
    return decorator

# --- Your protected endpoints ---
@app.route('/admin/dashboard', methods=['GET'])
@role_required('admin')
def admin_dashboard():
    return jsonify({"message": "Welcome Admin! You have full access."})

@app.route('/manager/reports', methods=['GET'])
@role_required('manager')
def manager_reports():
    return jsonify({"message": "Welcome Manager! You can view reports."})

@app.route('/staff/room-service', methods=['GET'])
@role_required('staff')
def staff_room_service():
    return jsonify({"message": "Welcome Staff! You can manage room services."})

@app.route('/guest/profile', methods=['GET'])
@role_required('guest')
def guest_profile():
    return jsonify({"message": "Welcome Guest! You can view your profile."})

@app.route('/manage/rooms', methods=['POST'])
@role_required('manager')
def manage_rooms():
    return jsonify({"message": "Room managed by Manager or Admin"})

@app.route('/clean/rooms', methods=['POST'])
@role_required('staff')
def clean_rooms():
    return jsonify({"message": "Room cleaning recorded by Staff, Manager, or Admin"})

@app.route('/public/info', methods=['GET'])
def public_info():
    return jsonify({"message": "This is public hotel info"})







@app.route('/')
def index():
        """Home page"""
        return jsonify({
            'message': 'Hotel Management System API',
         
        })


app.register_blueprint(booking_bp, url_prefix='/booking')
app.register_blueprint(adding_guest, url_prefix='/addguests')
app.register_blueprint(adding_room, url_prefix= '/addRooms')
app.register_blueprint(check_availabilities, url_prefix= '/availability_check')
app.register_blueprint(booking_room, url_prefix= '/bookRoom')

# Register auth blueprint
app.register_blueprint(auth_bp, url_prefix='/auth')




if __name__ == '__main__':
    with app.app_context():
        app.run(debug=True)
