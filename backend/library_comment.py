
from flask import Blueprint, request, jsonify, current_app
from db import mysql
import MySQLdb.cursors
import jwt
from datetime import date

library_cmmnt = Blueprint('library_cmmnt', __name__)

# 🔹 Utility Function to Verify JWT Token & Librarian Role
def verify_librarian():
    token = request.headers.get("Authorization")
    if not token:
        return {"error": "Token is missing"}, 401

    try:
        token = token.split(" ")[1]  # Remove "Bearer " prefix
        decoded_token = jwt.decode(token, current_app.secret_key, algorithms=["HS256"])
        if decoded_token.get("role") != "librarian":
            return {"error": "Unauthorized. Only librarians can perform this action."}, 403
        return decoded_token
    except jwt.ExpiredSignatureError:
        return {"error": "Token expired"}, 401
    except jwt.InvalidTokenError:
        return {"error": "Invalid token"}, 401



@library_cmmnt.route('/add_comment', methods=['POST'])
def add_comment():
    librarian_check = verify_librarian()
    if isinstance(librarian_check, tuple):
        return jsonify({"error": "Unauthorized. Only librarians can perform this action."}), 403

    librarian_id = librarian_check.get("id")
    data = request.get_json()
    student_id = data.get('student_id')
    comment = data.get('comment')
    comment_type = data.get('comment_type')  # new field

    if not student_id or not comment or not comment_type:
        return jsonify({"error": "Missing student_id, comment, or comment_type."}), 400

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        cursor.execute("""
            INSERT INTO librarian_comments (student_id, librarian_id, comment, comment_type)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
                comment = VALUES(comment),
                created_at = CURRENT_TIMESTAMP
        """, (student_id, librarian_id, comment, comment_type))
        mysql.connection.commit()
        return jsonify({"message": "Comment added/updated successfully."}), 200

    except Exception as e:
        mysql.connection.rollback()
        return jsonify({"error": f"Failed to add comment: {str(e)}"}), 500

    finally:
        cursor.close()

# 🔹 View comments added by the librarian for students of a specific class and section
@library_cmmnt.route('/get_comments', methods=['GET'])
def get_comments():
    """
    Expects query parameters:
      - class: The class number (e.g., "1")
      - section: The section (e.g., "A")
    
    Looks up the corresponding class_section_id from the sms_class_section table,
    then retrieves comments (with comment type) for that class section.
    
    If the authenticated user is a librarian, only comments made by that librarian are shown.
    If the authenticated user is an administrator, comments from all librarians for that class
    section are returned.
    """
    # New verification function that allows both librarians and administrators
    def verify_librarian_admin():
        token = request.headers.get("Authorization")
        if not token:
            return {"error": "Token is missing"}, 401
        try:
            token = token.split(" ")[1]  # Remove "Bearer " prefix
            decoded_token = jwt.decode(token, current_app.secret_key, algorithms=["HS256"])
            if decoded_token.get("role") not in ["librarian", "administrator"]:
                return {"error": "Unauthorized. Only librarians or administrators can perform this action."}, 403
            return decoded_token
        except jwt.ExpiredSignatureError:
            return {"error": "Token expired"}, 401
        except jwt.InvalidTokenError:
            return {"error": "Invalid token"}, 401

    user = verify_librarian_admin()
    if isinstance(user, tuple):
        return jsonify({"error": "Unauthorized. Only librarians or administrators can perform this action."}), 403

    role = user.get("role")
    user_id = user.get("id")  # For librarians, this is used to filter results

    class_number = request.args.get('class')
    section = request.args.get('section')

    if not (class_number and section):
        return jsonify({"error": "Missing class or section parameters"}), 400

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        # Look up the class_section_id using the class and section values
        cursor.execute("""
            SELECT class_section_id FROM sms_class_section
            WHERE class_number = %s AND section = %s
        """, (class_number, section))
        cs = cursor.fetchone()
        if not cs:
            return jsonify({"error": "Class section not found"}), 404

        class_section_id = cs.get("class_section_id")
        # If the role is librarian, filter by librarian_id; if administrator, do not filter
        if role == "librarian":
            query = """
                SELECT lc.comment_id, lc.comment, lc.comment_type, lc.created_at, ss.name AS student_name
                FROM librarian_comments lc
                JOIN sms_students ss ON lc.student_id = ss.id
                JOIN sms_student_enrollments se ON ss.id = se.student_id
                WHERE se.class_section_id = %s AND lc.librarian_id = %s
                ORDER BY lc.created_at DESC
            """
            params = (class_section_id, user_id)
        else:  # administrator
            query = """
                SELECT lc.comment_id, lc.comment, lc.comment_type, lc.created_at, ss.name AS student_name, lc.librarian_id
                FROM librarian_comments lc
                JOIN sms_students ss ON lc.student_id = ss.id
                JOIN sms_student_enrollments se ON ss.id = se.student_id
                WHERE se.class_section_id = %s
                ORDER BY lc.created_at DESC
            """
            params = (class_section_id,)

        cursor.execute(query, params)
        comments = cursor.fetchall()
    except Exception as e:
        return jsonify({"error": "Failed to retrieve comments", "details": str(e)}), 500
    finally:
        cursor.close()

    if not comments:
        return jsonify({"message": "No comments found for this class section."}), 200

    return jsonify({
        "class_section_id": class_section_id,
        "comments": comments
    }), 200

@library_cmmnt.route('/admin-student-comments', methods=['GET'])
def admin_student_comments():
    # 1) Validate token in Authorization header
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith("Bearer "):
        return jsonify({"error": "Token is missing or invalid"}), 401

    token = auth_header.split(" ")[1]
    try:
        decoded = jwt.decode(token, current_app.secret_key, algorithms=["HS256"])
        role = decoded.get('role')
        # Only allow administrator or teacher
        if role not in ["administrator", "teacher"]:
            return jsonify({"error": "Unauthorized access"}), 403
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Token has expired"}), 401
    except jwt.InvalidTokenError as e:
        return jsonify({"error": f"Invalid token: {str(e)}"}), 401

    # 2) Get admission_no and session_id from query parameters
    admission_no = request.args.get('admission_no')
    session_id = request.args.get('session_id')
    if not admission_no or not session_id:
        return jsonify({"error": "Admission number and session ID are required"}), 400

    # 3) Look up student from sms_students by admission_no
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        cursor.execute("""
            SELECT id AS student_id, name
            FROM sms_students
            WHERE admission_no = %s
        """, (admission_no,))
        student_row = cursor.fetchone()
        if not student_row:
            return jsonify({"error": "Student not found"}), 404

        student_id = student_row['student_id']

        # 4) Find enrollment for that session (class_section_id, class_number, section)
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

        # 5) Retrieve all comments for this student
        cursor.execute("""
            SELECT comment_id, comment, comment_type, created_at, librarian_id
            FROM librarian_comments
            WHERE student_id = %s
            ORDER BY created_at DESC
        """, (student_id,))
        comments = cursor.fetchall()
    except Exception as e:
        return jsonify({"error": "Failed to retrieve comments", "details": str(e)}), 500
    finally:
        cursor.close()

    if not comments:
        return jsonify({"message": "No comments found for this student."}), 200

    return jsonify({
        "student_id": student_id,
        "admission_no": admission_no,
        "class_number": class_number,
        "section": section,
        "session_id": session_id,
        "comments": comments
    }), 200