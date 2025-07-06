from flask import Blueprint, request, jsonify
from database import mysql

booking_bp = Blueprint('booking_bp', __name__)
@booking_bp.route('/view_bookings', methods=['GET'])
def view_bookings():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT b.booking_id, g.guest_name, r.room_number, r.room_type, b.check_in, b.check_out
        FROM bookings b
        JOIN guests g ON b.guest_id = g.guest_id
        JOIN rooms r ON b.room_number = r.room_number
    """)
    rows = cur.fetchall()
    column_names = [i[0] for i in cur.description]
    result = [dict(zip(column_names, row)) for row in rows]
    cur.close()
    return jsonify(result)
