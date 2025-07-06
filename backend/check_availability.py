from flask import Blueprint, request, jsonify,render_template
from database import mysql
check_availabilities= Blueprint('check_availabilities', __name__)


# Route to check room availability
@check_availabilities.route('/check_availability', methods=['GET'])
def check_availability():
    check_in = request.form.get('check_in')
    check_out = request.form.get('check_out')
    room_type = request.form.get('room_type')
    capacity = request.form.get('capacity')

    cursor = mysql.connection.cursor()

    # Base query: rooms not booked in given date range
    query = """
        SELECT * FROM rooms 
        WHERE room_number NOT IN (
            SELECT room_number FROM bookings
            WHERE NOT (
                check_out <= %s OR check_in >= %s
            )
        )
    """
    params = [check_in, check_out]

    # Add optional filters
    if room_type:
        query += " AND room_type = %s"
        params.append(room_type)
    if capacity:
        query += " AND capacity >= %s"
        params.append(capacity)

    cursor.execute(query, params)
    available_rooms = cursor.fetchall()
    cursor.close()

    return jsonify(available_rooms)