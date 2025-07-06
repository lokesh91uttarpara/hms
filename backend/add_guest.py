from flask import Blueprint, request, jsonify,render_template
from database import mysql
adding_guest = Blueprint('adding_guest', __name__)

# Route to add a guest
@adding_guest.route('/add_guest', methods=['POST'])
def add_guest():
    # Check if request is JSON or form data
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form
    
    guest_name = data.get('guest_name')
    email = data.get('email')
    phone = data.get('phone')
    gender = data.get('gender')
    id_proof = data.get('id_proof')
    id_no = data.get('id_no')
    address = data.get('address')
    check_in = data.get('check_in')
    
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("""
            INSERT INTO guests (guest_name, email, phone, gender, id_proof, id_no, address, check_in)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (guest_name, email, phone, gender, id_proof, id_no, address, check_in))
        mysql.connection.commit()
        message = "Guest added successfully"
    except Exception as e:
        mysql.connection.rollback()
        message = f"Error adding guest: {e}"
    finally:
        cursor.close()

    return jsonify({"message": message})