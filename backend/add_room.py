from flask import Blueprint, request, jsonify,render_template
from database import mysql
adding_room = Blueprint('adding_room', __name__)



# Route to handle Add Room form
@adding_room.route('/add_room', methods=['POST'])
def add_room():
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form

    
    room_number = data.get('room_number')
    room_type = data.get('room_type')
    capacity = data.get('capacity')
    price = data.get('price')
    status = data.get('status')
    amenities = data.get('amenities')

    cursor = mysql.connection.cursor()
    try:
        cursor.execute("""
            INSERT INTO rooms (room_number, room_type, capacity, price, status, amenities)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (room_number, room_type, capacity, price, status, amenities))
        mysql.connection.commit()
        message = "Room added successfully"
    except Exception as e:
        mysql.connection.rollback()
        message = f"Error adding room: {e}"
    finally:
        cursor.close()

    return jsonify({'message': message})