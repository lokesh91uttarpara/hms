from flask import Blueprint, request, jsonify,render_template
from database import mysql
booking_room= Blueprint('booking_room', __name__)

# ROOM BOOKING SECTION
@booking_room.route('/book_room', methods=['POST'])
def book_room():
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form


    guest_id = data.get('guest_id')
    guest_name=data.get('guest_name')
    room_number = data.get('room_number')
    check_in = data.get('check_in')
    check_out = data.get('check_out')
    total_amount =data.get('total_amount')

    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO bookings (guest_id,guest_name, room_number, check_in, check_out,total_amount) VALUES (%s, %s, %s, %s,%s,%s)",
                (guest_id,guest_name, room_number, check_in, check_out,total_amount))
    mysql.connection.commit()
    cur.close()
    return jsonify({"message": "Room booked successfully"})