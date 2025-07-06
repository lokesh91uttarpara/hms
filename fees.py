from flask import Blueprint, request, jsonify
from db import mysql
import MySQLdb.cursors
import json
import jwt
from datetime import date

fees_bp = Blueprint('fees', __name__)
fees_bp.secret_key = 'abcd21234455'  

@fees_bp.route('/fees/assign-class-structure', methods=['POST'])
def assign_structure():
    data = request.get_json()
    class_id = data['class_id']
    session_id = data['session_id']
    month = data['month']
    fields = json.dumps(data['fields'])  # store as JSON
    total_amount = data['amount']
    mode = data['mode']
    sections = data.get('sections', [])

    cursor = mysql.connection.cursor()

    if mode == 'class':
        cursor.execute("SELECT section FROM sms_class_section WHERE class_number = %s", (class_id,))
        sections = [row[0] for row in cursor.fetchall()]

    for section in sections:
        cursor.execute("""
            SELECT class_section_id FROM sms_class_section 
            WHERE class_number = %s AND section = %s
        """, (class_id, section))
        cs = cursor.fetchone()
        if cs:
            class_section_id = cs[0]
            # Check for existing structure
            cursor.execute("""
                SELECT id FROM fee_structures 
                WHERE class_section_id = %s AND session_id = %s AND month = %s
            """, (class_section_id, session_id, month))
            if cursor.fetchone():
                continue
            # Insert new structure
            cursor.execute("""
                INSERT INTO fee_structures (class_section_id, session_id, month, fields, total_amount)
                VALUES (%s, %s, %s, %s, %s)
            """, (class_section_id, session_id, month, fields, total_amount))

    mysql.connection.commit()
    cursor.close()
    return jsonify({"message": "Fee structure assigned successfully."})

# @fees_bp.route('/fees/pay', methods=['POST'])
# def pay_fee():
#     data = request.get_json()

#     student_id = data['student_id']
#     class_number = data['class']         # class from frontend
#     section = data['section']            # section from frontend
#     session_id = data['session_id']
#     month = data['month']
#     amount_paid = data['amount_paid']
#     payment_mode = data['payment_mode']
#     receipt_no = data['receipt_no']
#     payment_date = date.today()

#     try:
#         cursor = mysql.connection.cursor()

#         # 1. Get class_section_id
#         cursor.execute("""
#             SELECT class_section_id FROM sms_class_section
#             WHERE class_number = %s AND section = %s
#         """, (class_number, section))
#         result = cursor.fetchone()

#         if not result:
#             return jsonify({"error": "Class/Section combination not found."}), 404

#         class_section_id = result[0]

#         # 2. Insert into fee_payments
#         cursor.execute("""
#             INSERT INTO fee_payments 
#             (student_id, class_section_id, session_id, month, amount_paid, payment_mode, receipt_no, payment_date)
#             VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
#         """, (
#             student_id, class_section_id, session_id, month,
#             amount_paid, payment_mode, receipt_no, payment_date
#         ))

#         mysql.connection.commit()
#         cursor.close()
#         return jsonify({"message": "Payment recorded successfully."}), 200

#     except Exception as e:
#         print(f"Error in pay_fee: {e}")
#         return jsonify({"error": "Something went wrong.", "details": str(e)}), 500
# @fees_bp.route('/fees/pay', methods=['POST'])
# def pay_fee():
#     """
#     Receives JSON, for example:
#     {
#       "student_id": 123,
#       "class": 2,
#       "section": "A",
#       "session_id": 1,
#       "months": ["January", "February", "March"],
#       "payment_mode": "Online",
#       "receipt_no": "...",
#       ...
#     }
#     We then:
#       1) For each month: get its fee from fee_structures
#       2) Insert one record into fee_payments with that specific month’s fee.
#     """
#     data = request.get_json()

#     student_id   = data.get('student_id')
#     class_number = data.get('class')
#     section      = data.get('section')
#     session_id   = data.get('session_id')
#     months       = data.get('months', [])
#     payment_mode = data.get('payment_mode')
#     receipt_no   = data.get('receipt_no')
#     payment_date = date.today()  # or from data.get('payment_date')

#     if not (student_id and class_number and section and session_id and months):
#         return jsonify({"error": "Missing required fields"}), 400

#     cursor = mysql.connection.cursor()

#     # 1) Determine class_section_id
#     cursor.execute("""
#         SELECT class_section_id FROM sms_class_section
#         WHERE class_number = %s AND section = %s
#     """, (class_number, section))
#     row = cursor.fetchone()
#     if not row:
#         return jsonify({"error": "Invalid class/section"}), 404

#     class_section_id = row[0]

#     # 2) Insert payment record for each month with that month’s fee
#     for m in months:
#         # (a) Find the monthly fee in fee_structures
#         cursor.execute("""
#             SELECT total_amount
#             FROM fee_structures
#             WHERE class_section_id = %s AND session_id = %s AND month = %s
#         """, (class_section_id, session_id, m))
#         fee_row = cursor.fetchone()
#         monthly_fee = fee_row[0] if fee_row else 0  # fallback to 0 if not found

#         # (b) Insert that monthly fee into fee_payments
#         cursor.execute("""
#             INSERT INTO fee_payments
#             (
#                 student_id,
#                 class_section_id,
#                 session_id,
#                 month,
#                 amount_paid,
#                 payment_mode,
#                 receipt_no,
#                 payment_date
#             )
#             VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
#         """, (
#             student_id,
#             class_section_id,
#             session_id,
#             m,
#             monthly_fee,
#             payment_mode,
#             receipt_no,
#             payment_date
#         ))

#     mysql.connection.commit()
#     cursor.close()

#     return jsonify({"message": "Payments recorded by month successfully"}), 200
    
@fees_bp.route('/fees/pay', methods=['POST'])
def pay_fee():
    """
    Processes fee payment for one or more months.
    For students in classes 9-12 who have the elective "Computer",
    an extra fee is added (220 for classes 9-10, 250 for classes 11-12).
    """
    data = request.get_json()

    student_id   = data.get('student_id')
    class_number = data.get('class')
    section      = data.get('section')
    session_id   = data.get('session_id')
    months       = data.get('months', [])
    payment_mode = data.get('payment_mode')
    receipt_no   = data.get('receipt_no')
    payment_date = date.today()  # or get from data if needed

    if not (student_id and class_number and section and session_id and months):
        return jsonify({"error": "Missing required fields"}), 400

    cursor = mysql.connection.cursor()

    # 1) Determine class_section_id
    cursor.execute("""
        SELECT class_section_id FROM sms_class_section
        WHERE class_number = %s AND section = %s
    """, (class_number, section))
    row = cursor.fetchone()
    if not row:
        return jsonify({"error": "Invalid class/section"}), 404

    class_section_id = row[0]

    # 2) Get the student's elective subject from sms_students
    cursor.execute("SELECT elective_subject FROM sms_students WHERE id = %s", (student_id,))
    elective_row = cursor.fetchone()
    elective_subject = elective_row[0] if elective_row else None

    # 3) Determine extra fee based on elective subject and class level
    extra_fee = 0
    try:
        cls = int(class_number)
    except Exception:
        cls = 0

    if elective_subject and elective_subject.lower() in ["computer science", "biology"]:
    # your code here
        if cls in [9, 10]:
            extra_fee = 220
        elif cls in [11, 12]:
            extra_fee = 250

    # 4) Process payment for each month by adding the extra fee to the base fee
    for m in months:
        # (a) Get the base monthly fee from fee_structures
        cursor.execute("""
            SELECT total_amount
            FROM fee_structures
            WHERE class_section_id = %s AND session_id = %s AND month = %s
        """, (class_section_id, session_id, m))
        fee_row = cursor.fetchone()
        base_fee = fee_row[0] if fee_row else 0  # fallback if fee structure not found

        # Calculate the final fee (base fee + extra fee if applicable)
        monthly_fee = base_fee + extra_fee

        # (b) Insert the payment record into fee_payments
        cursor.execute("""
            INSERT INTO fee_payments
            (
                student_id,
                class_section_id,
                session_id,
                month,
                amount_paid,
                payment_mode,
                receipt_no,
                payment_date
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            student_id,
            class_section_id,
            session_id,
            m,
            monthly_fee,
            payment_mode,
            receipt_no,
            payment_date
        ))

    mysql.connection.commit()
    cursor.close()

    return jsonify({"message": "Payments recorded by month successfully"}), 200

    
@fees_bp.route('/fees/unpaid-status', methods=['POST'])
def unpaid_status():
    data = request.get_json()
    class_number = data['class']
    section = data['section']
    session_id = data['session_id']
    month = data['month']

    cursor = mysql.connection.cursor()

    # Step 1: Get class_section_id for class & section
    cursor.execute("""
        SELECT class_section_id 
        FROM sms_class_section 
        WHERE class_number = %s AND section = %s
    """, (class_number, section))
    row = cursor.fetchone()

    if not row:
        return jsonify({"error": "Invalid class or section"}), 404

    class_section_id = row[0]

    # Step 2: Get all students enrolled in that class_section and session
    cursor.execute("""
        SELECT s.id AS student_id, s.name, s.admission_no, e.roll_no
        FROM sms_students s
        JOIN sms_student_enrollments e ON s.id = e.student_id
        WHERE e.class_section_id = %s AND e.session_id = %s
        ORDER BY e.roll_no
    """, (class_section_id, session_id))
    students = cursor.fetchall()

    result = []

    # Step 3: For each student, check if payment exists for that month
    for student in students:
        sid = student[0]
        name = student[1]
        admission_no = student[2]
        roll_no = student[3]

        cursor.execute("""
            SELECT payment_mode, payment_date 
            FROM fee_payments 
            WHERE student_id = %s AND session_id = %s AND month = %s
        """, (sid, session_id, month))
        payment = cursor.fetchone()

        result.append({
            "student_id": sid,
            "name": name,
            "admission_no": admission_no,
            "roll_no": roll_no,
            "paid": bool(payment),
            "payment_mode": payment[0] if payment else None,
            "payment_date": str(payment[1]) if payment else None
        })

    cursor.close()
    return jsonify(result)


# @fees_bp.route('/fees/get-assigned', methods=['GET'])
# def get_assigned_fee():
#     class_number = request.args.get('class_id')
#     section = request.args.get('section')
#     session_id = request.args.get('session_id')
#     month = request.args.get('month')

#     cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    
#     if not class_number or not section or not session_id or not month:
#         return jsonify({'error': 'Missing parameters'}), 400

#     # 1. Find class_section_id
#     cursor.execute("""
#         SELECT class_section_id FROM sms_class_section
#         WHERE class_number = %s AND section = %s
#     """, (class_number, section))
#     class_section_result = cursor.fetchone()

#     if not class_section_result:
#         return jsonify({'error': 'Class-section not found'}), 404

#     class_section_id = class_section_result['class_section_id']

#     # 2. Find fee_structure
#     cursor.execute("""
#         SELECT * FROM fee_structures
#         WHERE class_section_id = %s AND session_id = %s AND month = %s
#     """, (class_section_id, session_id, month))
#     fee_structure = cursor.fetchone()

#     if fee_structure:
#         fee_structure['fields'] = json.loads(fee_structure['fields'])
#         fee_structure['class_section_id'] = class_section_id
#         return jsonify(fee_structure)
#     else:
#         return jsonify({})

@fees_bp.route('/fees/get-assigned', methods=['GET'])
def get_assigned_fee():
    class_number = request.args.get('class_id')
    section = request.args.get('section')
    session_id = request.args.get('session_id')
    months_str = request.args.get('months', '')
    student_id = request.args.get('student_id')  # Optional parameter

    if not class_number or not section or not session_id or not months_str:
        return jsonify({'error': 'Missing parameters'}), 400

    months = [m.strip() for m in months_str.split(',') if m.strip()]
    if not months:
        return jsonify({'error': 'No valid months provided'}), 400

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        SELECT class_section_id, class_number FROM sms_class_section
        WHERE class_number = %s AND section = %s
    """, (class_number, section))
    cs_result = cursor.fetchone()
    if not cs_result:
        return jsonify({'error': 'Class-section not found'}), 404

    class_section_id = cs_result['class_section_id']
    base_class = cs_result['class_number']

    # If a student_id is provided, fetch their elective and compute extra fee
    extra_fee = 0
    if student_id:
        cursor.execute("SELECT elective_subject FROM sms_students WHERE id = %s", (student_id,))
        elective_row = cursor.fetchone()
        if elective_row and elective_row.get('elective_subject'):
            elective = elective_row['elective_subject'].lower()
            try:
                cls = int(base_class)
            except Exception:
                cls = 0
            if elective and elective.lower() in ["computer science", "biology"]:
                if cls in [9, 10]:
                    extra_fee = 220
                elif cls in [11, 12]:
                    extra_fee = 250

    placeholders = ','.join(['%s'] * len(months))
    params = [class_section_id, session_id] + months
    query = f"""
        SELECT 
            id,
            month, 
            total_amount, 
            fields 
        FROM fee_structures
        WHERE class_section_id = %s
          AND session_id = %s
          AND month IN ({placeholders})
    """
    cursor.execute(query, params)
    fee_structures = cursor.fetchall()

    # If a student is specified, adjust each fee with the extra fee
    for fee in fee_structures:
        fee['expected_fee'] = fee['total_amount'] + extra_fee
        if fee.get('fields'):
            fee['fields'] = json.loads(fee['fields'])

    return jsonify(fee_structures)

# ✏️ Update Fee Structure by ID
@fees_bp.route('/fees/update-assigned', methods=['PUT'])
def update_assigned_fee():
    data = request.get_json()
    fee_id = data.get('id')
    fields = data.get('fields')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    if not fee_id or not fields:
        return jsonify({'message': 'Missing data'}), 400

    total_amount = float(sum(float(f.get('amount', 0)) for f in fields))

    query = """
        UPDATE fee_structures
        SET fields = %s, total_amount = %s
        WHERE id = %s
    """
    cursor.execute(query, (json.dumps(fields), total_amount, fee_id))
    mysql.connection.commit()

    return jsonify({'message': 'Fee structure updated successfully'})


# 🚀 Optional: Add or Seed Fee Structure (only if it doesn't exist)
@fees_bp.route('/fees/create-or-update', methods=['POST'])
def create_or_update_fee_structure():
    data = request.get_json()

    class_id  = data.get('class_id')
    section   = data.get('section')
    session_id= data.get('session_id')
    months    = data.get('months', [])  # now an array
    fields    = data.get('fields')

    # Validate
    if not (class_id and section and session_id and months and fields):
        return jsonify({'error': 'Missing parameters'}), 400

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # 1. Resolve class_section_id
    cursor.execute("""
        SELECT class_section_id
        FROM sms_class_section
        WHERE class_number = %s AND section = %s
    """, (class_id, section))
    result = cursor.fetchone()
    if not result:
        return jsonify({'error': 'Class-section not found'}), 404

    class_section_id = result['class_section_id']

    # 2. Calculate total once for these fields (or each iteration if needed).
    total_amount = sum(float(f.get('amount', 0)) for f in fields)

    # 3. For each month in the array:
    for m in months:
        # Check if there's an existing record for that month
        cursor.execute("""
            SELECT id
            FROM fee_structures
            WHERE class_section_id = %s AND session_id = %s AND month = %s
        """, (class_section_id, session_id, m))
        existing = cursor.fetchone()

        if existing:
            # Update
            cursor.execute("""
                UPDATE fee_structures
                SET fields = %s, total_amount = %s
                WHERE id = %s
            """, (json.dumps(fields), total_amount, existing['id']))
        else:
            # Insert
            cursor.execute("""
                INSERT INTO fee_structures
                    (class_section_id, session_id, month, fields, total_amount)
                VALUES (%s, %s, %s, %s, %s)
            """, (class_section_id, session_id, m, json.dumps(fields), total_amount))

    mysql.connection.commit()
    cursor.close()

    return jsonify({'message': 'Fee structures saved successfully for ' + ', '.join(months)})

@fees_bp.route('/fees/get-paid-months', methods=['GET'])
def get_paid_months():
    student_id = request.args.get('student_id')
    class_number = request.args.get('class')
    section = request.args.get('section')
    session_id = request.args.get('session_id')

    if not (student_id and class_number and section and session_id):
        return jsonify([])

    # 1) Get class_section_id from class_number + section
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        SELECT class_section_id 
        FROM sms_class_section
        WHERE class_number = %s AND section = %s
    """, (class_number, section))
    row_cs = cursor.fetchone()

    if not row_cs:
        return jsonify([])

    class_section_id = row_cs['class_section_id']

    # 2) Fetch distinct months paid
    cursor.execute("""
        SELECT DISTINCT month
        FROM fee_payments
        WHERE student_id = %s
          AND class_section_id = %s
          AND session_id = %s
    """, (student_id, class_section_id, session_id))
    rows = cursor.fetchall()
    cursor.close()

    paid_months = [row['month'] for row in rows]
    return jsonify(paid_months)

#########################Student view fees ########################################
# @fees_bp.route('/fees/student-monthly-status', methods=['GET'])
# def student_monthly_status():
#     auth_header = request.headers.get('Authorization')
#     if not auth_header or not auth_header.startswith("Bearer "):
#         return jsonify({"error": "Token is missing or invalid"}), 401

#     token = auth_header.split(" ")[1]

#     try:
#         decoded = jwt.decode(token, fees_bp.secret_key, algorithms=["HS256"])
#         student_id = decoded.get('id')
#         admission_no = decoded.get('admission_no')
#         role = decoded.get('role')
#     except jwt.ExpiredSignatureError:
#         return jsonify({"error": "Token has expired"}), 401
#     except jwt.InvalidTokenError as e:
#         return jsonify({"error": f"Invalid token: {str(e)}"}), 401

#     # Session ID required
#     session_id = request.args.get('session_id')
#     if not session_id:
#         return jsonify({'error': 'Missing session_id'}), 400

#     cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

#     # Get class_section_id from enrollment
#     cursor.execute("""
#         SELECT e.class_section_id, cs.class_number, cs.section
#         FROM sms_student_enrollments e
#         JOIN sms_class_section cs ON cs.class_section_id = e.class_section_id
#         WHERE e.student_id = %s AND e.session_id = %s
#     """, (student_id, session_id))
#     row = cursor.fetchone()

#     if not row:
#         return jsonify({'error': 'Enrollment not found'}), 404

#     class_section_id = row['class_section_id']
#     class_number = row['class_number']
#     section = row['section']

#     months = [
#         'January', 'February', 'March', 'April', 'May', 'June',
#         'July', 'August', 'September', 'October', 'November', 'December'
#     ]

#     monthly_status = []

#     for month in months:
#         # Fetch fee structure
#         cursor.execute("""
#             SELECT total_amount FROM fee_structures
#             WHERE class_section_id = %s AND session_id = %s AND month = %s
#         """, (class_section_id, session_id, month))
#         structure = cursor.fetchone()
#         total_amount = structure['total_amount'] if structure else 0.0

#         # Check payment status
#         cursor.execute("""
#             SELECT amount_paid, payment_mode, payment_date FROM fee_payments
#             WHERE student_id = %s AND class_section_id = %s AND session_id = %s AND month = %s
#         """, (student_id, class_section_id, session_id, month))
#         payment = cursor.fetchone()

#         monthly_status.append({
#             'month': month,
#             'total_amount': total_amount,
#             'paid': bool(payment),
#             'amount_paid': payment['amount_paid'] if payment else 0.0,
#             'payment_mode': payment['payment_mode'] if payment else None,
#             'payment_date': str(payment['payment_date']) if payment and payment['payment_date'] else None,
#         })

#     cursor.close()

#     return jsonify({
#         "student_id": student_id,
#         "admission_no": admission_no,
#         "class_number": class_number,
#         "section": section,
#         "session_id": session_id,
#         "monthly_fees": monthly_status
#     })
   
@fees_bp.route('/fees/student-monthly-status', methods=['GET'])
def student_monthly_status():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Token is missing or invalid"}), 401

    token = auth_header.split(" ")[1]

    try:
        decoded = jwt.decode(token, fees_bp.secret_key, algorithms=["HS256"])
        student_id = decoded.get('id')
        admission_no = decoded.get('admission_no')
        role = decoded.get('role')
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Token has expired"}), 401
    except jwt.InvalidTokenError as e:
        return jsonify({"error": f"Invalid token: {str(e)}"}), 401

    session_id = request.args.get('session_id')
    if not session_id:
        return jsonify({'error': 'Missing session_id'}), 400

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Get enrollment and class info
    cursor.execute("""
        SELECT e.class_section_id, cs.class_number, cs.section
        FROM sms_student_enrollments e
        JOIN sms_class_section cs ON cs.class_section_id = e.class_section_id
        WHERE e.student_id = %s AND e.session_id = %s
    """, (student_id, session_id))
    row = cursor.fetchone()

    if not row:
        return jsonify({'error': 'Enrollment not found'}), 404

    class_section_id = row['class_section_id']
    class_number = row['class_number']
    section = row['section']

    # Fetch student's elective subject
    cursor.execute("SELECT elective_subject FROM sms_students WHERE id = %s", (student_id,))
    elective_row = cursor.fetchone()
    elective_subject = elective_row['elective_subject'] if elective_row else None

    # Determine extra fee based on elective subject
    extra_fee = 0
    try:
        cls = int(class_number)
    except Exception:
        cls = 0
    if elective_subject and elective_subject.lower() in ["computer science", "biology"]:
    # your code here
        if cls in [9, 10]:
            extra_fee = 220
        elif cls in [11, 12]:
            extra_fee = 250

    months = [
        'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
    ]
    monthly_status = []

    for month in months:
        # Get base fee from fee_structures
        cursor.execute("""
            SELECT total_amount FROM fee_structures
            WHERE class_section_id = %s AND session_id = %s AND month = %s
        """, (class_section_id, session_id, month))
        structure = cursor.fetchone()
        base_fee = structure['total_amount'] if structure else 0.0

        # Calculate expected fee (base fee + extra fee if elective applies)
        expected_fee = base_fee + extra_fee

        # Check if payment exists for this month
        cursor.execute("""
            SELECT amount_paid, payment_mode, payment_date FROM fee_payments
            WHERE student_id = %s AND class_section_id = %s AND session_id = %s AND month = %s
        """, (student_id, class_section_id, session_id, month))
        payment = cursor.fetchone()

        monthly_status.append({
            'month': month,
            'expected_fee': expected_fee,  # shows the fee the student should pay
            'paid': bool(payment),
            'amount_paid': payment['amount_paid'] if payment else 0.0,
            'payment_mode': payment['payment_mode'] if payment else None,
            'payment_date': str(payment['payment_date']) if payment and payment['payment_date'] else None,
        })

    cursor.close()

    return jsonify({
        "student_id": student_id,
        "admission_no": admission_no,
        "class_number": class_number,
        "section": section,
        "session_id": session_id,
        "monthly_fees": monthly_status
    })
 
   
    

# @fees_bp.route('/fees/admin-student-fee-status', methods=['GET'])
# def admin_student_fee_status():
#     # 1) Validate token in Authorization header
#     auth_header = request.headers.get('Authorization', '')
#     if not auth_header.startswith("Bearer "):
#         return jsonify({"error": "Token is missing or invalid"}), 401

#     token = auth_header.split(" ")[1]
#     try:
#         decoded = jwt.decode(token, fees_bp.secret_key, algorithms=["HS256"])
#         role = decoded.get('role')
#         # Only allow admin or teacher
#         if role not in ["administrator", "teacher"]:
#             return jsonify({"error": "Unauthorized access"}), 403
#     except jwt.ExpiredSignatureError:
#         return jsonify({"error": "Token has expired"}), 401
#     except jwt.InvalidTokenError as e:
#         return jsonify({"error": f"Invalid token: {str(e)}"}), 401

#     # 2) Get admission_no, session_id from query params
#     admission_no = request.args.get('admission_no')
#     session_id = request.args.get('session_id')
#     if not admission_no or not session_id:
#         return jsonify({"error": "Admission number and session ID are required"}), 400

#     # 3) Look up student from `sms_students` by admission_no
#     cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
#     cursor.execute("""
#         SELECT id AS student_id, name
#         FROM sms_students
#         WHERE admission_no = %s
#     """, (admission_no,))
#     student_row = cursor.fetchone()
#     if not student_row:
#         return jsonify({"error": "Student not found"}), 404

#     student_id = student_row['student_id']

#     # 4) Find enrollment for that session (class_section_id, class_number, section)
#     cursor.execute("""
#         SELECT e.class_section_id, cs.class_number, cs.section
#         FROM sms_student_enrollments e
#         JOIN sms_class_section cs ON cs.class_section_id = e.class_section_id
#         WHERE e.student_id = %s 
#           AND e.session_id = %s
#         LIMIT 1
#     """, (student_id, session_id))
#     enroll = cursor.fetchone()
#     if not enroll:
#         return jsonify({"error": "No enrollment found for this session"}), 404

#     class_section_id = enroll['class_section_id']
#     class_number = enroll['class_number']
#     section = enroll['section']

#     # 5) Build array of months + fee/payment info
#     months_list = [
#         'January', 'February', 'March', 'April', 'May', 'June',
#         'July', 'August', 'September', 'October', 'November', 'December'
#     ]
#     fee_status = []

#     for m in months_list:
#         # a) Get total_amount from fee_structures
#         cursor.execute("""
#             SELECT total_amount
#             FROM fee_structures
#             WHERE class_section_id = %s 
#               AND session_id = %s 
#               AND month = %s
#         """, (class_section_id, session_id, m))
#         row_struct = cursor.fetchone()
#         total_amount = row_struct['total_amount'] if row_struct else 0.0

#         # b) Check fee_payments
#         cursor.execute("""
#             SELECT amount_paid, payment_mode, payment_date
#             FROM fee_payments
#             WHERE student_id = %s
#               AND class_section_id = %s
#               AND session_id = %s
#               AND month = %s
#         """, (student_id, class_section_id, session_id, m))
#         row_payment = cursor.fetchone()

#         if row_payment:
#             paid = True
#             amount_paid = row_payment['amount_paid']
#             payment_mode = row_payment['payment_mode']
#             payment_date = (
#                 str(row_payment['payment_date'])
#                 if row_payment['payment_date'] else None
#             )
#         else:
#             paid = False
#             amount_paid = 0.0
#             payment_mode = None
#             payment_date = None

#         fee_status.append({
#             "month": m,
#             "total_amount": total_amount,
#             "paid": paid,
#             "amount_paid": amount_paid,
#             "payment_mode": payment_mode,
#             "payment_date": payment_date
#         })

#     cursor.close()

#     return jsonify({
#         "admission_no": admission_no,
#         "class_number": class_number,
#         "section": section,
#         "session_id": session_id,
#         "months": fee_status
#     }), 200
@fees_bp.route('/fees/admin-student-fee-status', methods=['GET'])
def admin_student_fee_status():
    # Validate token in Authorization header
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith("Bearer "):
        return jsonify({"error": "Token is missing or invalid"}), 401

    token = auth_header.split(" ")[1]
    try:
        decoded = jwt.decode(token, fees_bp.secret_key, algorithms=["HS256"])
        role = decoded.get('role')
        # Only allow admin or teacher
        if role not in ["administrator", "teacher"]:
            return jsonify({"error": "Unauthorized access"}), 403
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Token has expired"}), 401
    except jwt.InvalidTokenError as e:
        return jsonify({"error": f"Invalid token: {str(e)}"}), 401

    # Get admission_no and session_id from query params
    admission_no = request.args.get('admission_no')
    session_id = request.args.get('session_id')
    if not admission_no or not session_id:
        return jsonify({"error": "Admission number and session ID are required"}), 400

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    # Look up student using admission_no
    cursor.execute("""
        SELECT id AS student_id, name
        FROM sms_students
        WHERE admission_no = %s
    """, (admission_no,))
    student_row = cursor.fetchone()
    if not student_row:
        return jsonify({"error": "Student not found"}), 404

    student_id = student_row['student_id']

    # Find enrollment for the given session (get class_section_id, class_number, section)
    cursor.execute("""
        SELECT e.class_section_id, cs.class_number, cs.section
        FROM sms_student_enrollments e
        JOIN sms_class_section cs ON cs.class_section_id = e.class_section_id
        WHERE e.student_id = %s 
          AND e.session_id = %s
        LIMIT 1
    """, (student_id, session_id))
    enroll = cursor.fetchone()
    if not enroll:
        return jsonify({"error": "No enrollment found for this session"}), 404

    class_section_id = enroll['class_section_id']
    class_number = enroll['class_number']
    section = enroll['section']

    # Fetch student's elective subject
    cursor.execute("SELECT elective_subject FROM sms_students WHERE id = %s", (student_id,))
    elective_row = cursor.fetchone()
    elective_subject = elective_row['elective_subject'] if elective_row and 'elective_subject' in elective_row else None

    # Determine extra fee based on elective subject
    extra_fee = 0
    try:
        cls = int(class_number)
    except Exception:
        cls = 0
    if elective_subject and elective_subject.lower() in ["computer science", "biology"]:
    # your code here
        if cls in [9, 10]:
            extra_fee = 220
        elif cls in [11, 12]:
            extra_fee = 250

    # Build fee status for each month
    months_list = [
        'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
    ]
    fee_status = []

    for m in months_list:
        # Get base fee from fee_structures
        cursor.execute("""
            SELECT total_amount
            FROM fee_structures
            WHERE class_section_id = %s 
              AND session_id = %s 
              AND month = %s
        """, (class_section_id, session_id, m))
        row_struct = cursor.fetchone()
        base_fee = row_struct['total_amount'] if row_struct else 0.0

        # Calculate expected fee (base fee + extra fee if applicable)
        expected_fee = base_fee + extra_fee

        # Check fee payment records for this month
        cursor.execute("""
            SELECT amount_paid, payment_mode, payment_date
            FROM fee_payments
            WHERE student_id = %s
              AND class_section_id = %s
              AND session_id = %s
              AND month = %s
        """, (student_id, class_section_id, session_id, m))
        row_payment = cursor.fetchone()

        if row_payment:
            paid = True
            amount_paid = row_payment['amount_paid']
            payment_mode = row_payment['payment_mode']
            payment_date = str(row_payment['payment_date']) if row_payment['payment_date'] else None
        else:
            paid = False
            amount_paid = 0.0
            payment_mode = None
            payment_date = None

        fee_status.append({
            "month": m,
            "expected_fee": expected_fee,  # Reflects base fee plus extra fee if applicable
            "paid": paid,
            "amount_paid": amount_paid,
            "payment_mode": payment_mode,
            "payment_date": payment_date
        })

    cursor.close()

    return jsonify({
        "admission_no": admission_no,
        "class_number": class_number,
        "section": section,
        "session_id": session_id,
        "months": fee_status
    }), 200
