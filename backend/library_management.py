from flask import Blueprint, request, jsonify, current_app, send_file
from flask_mysqldb import MySQL
import MySQLdb.cursors
import jwt
import datetime
import csv
import io
import MySQLdb

library_app = Blueprint('library_app', __name__)
mysql = MySQL()
secret_key = None


ALLOWED_EXTENSIONS = {'csv'}


# 🔹 Utility Function to Verify JWT Token & Librarian Role
def verify_librarian():
    """ Verify if the request comes from a Librarian user """
    token = request.headers.get("Authorization")

    if not token:
        return {"error": "Token is missing"}, 401

    try:
        token = token.split(" ")[1]  # Remove "Bearer " prefix
        decoded_token = jwt.decode(token, current_app.secret_key, algorithms=["HS256"])
        if decoded_token.get("role") != "librarian":
            return {"error": "Unauthorized. Only librarians can perform this action."}, 403
        return decoded_token  # Valid librarian
    except jwt.ExpiredSignatureError:
        return {"error": "Token expired"}, 401
    except jwt.InvalidTokenError:
        return {"error": "Invalid token"}, 401



def verify_administrator():
    """ Verify if the request comes from an Administrator user """
    token = request.headers.get("Authorization")

    if not token:
        return {"error": "Token is missing"}, 401

    try:
        token = token.split(" ")[1]  # Remove "Bearer " prefix
        decoded_token = jwt.decode(token, current_app.secret_key, algorithms=["HS256"])
        if decoded_token.get("role") != "administrator":
            return {"error": "Unauthorized. Only administrators can perform this action."}, 403
        return decoded_token  # Valid administrator
    except jwt.ExpiredSignatureError:
        return {"error": "Token expired"}, 401
    except jwt.InvalidTokenError:
        return {"error": "Invalid token"}, 401




def allowed_file(filename):
    """Check if the uploaded file is a CSV"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS





@library_app.route('/add_book', methods=['POST'])
def add_book():
    """ Librarians and Administrators can add books to the library via JSON or CSV file """
    librarian_check = verify_librarian()
    admin_check = verify_administrator()

    # Determine the role of the user making the request
    if isinstance(librarian_check, dict):  
        user_role = "librarian"
    elif isinstance(admin_check, dict):  
        user_role = "administrator"
    else:
        return jsonify({"error": "Unauthorized. Only librarians or administrators can perform this action."}), 403

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if 'file' in request.files:
        file = request.files['file']
        if file and allowed_file(file.filename):
            return process_csv_upload(file, cursor, user_role)
        else:
            return jsonify({"error": "Invalid file format. Only CSV files are allowed."}), 400

    # JSON Input Handling
    data = request.json
    return process_json_data(data, cursor, user_role)

def process_json_data(data, cursor, user_role):
    """ Process JSON input and add books while preventing duplicate copies for the same book """
    isbn = data.get('isbn')
    barcode = data.get('barcode')
    title = data.get('title')
    author = data.get('author')
    publisher = data.get('publisher')
    price = data.get('price', 0.00)
    pages = data.get('pages')
    copies = data.get('copies', 1)  # Number of copies to add
    class_ = data.get('class')
    section = data.get('section')
    location = data.get('location')
    tags = data.get('tags')
    status = data.get('status', 'Available')
    accession_number = data.get('accession_number', '')  # Use provided accession number

    # Validate required fields
    if not (isbn and barcode):
        return jsonify({"error": "ISBN and Barcode are required fields."}), 400

    # Check if book already exists based on Barcode
    cursor.execute("SELECT book_id, title, barcode  FROM library_books WHERE barcode = %s", (barcode,))
    existing_book = cursor.fetchone()

    if existing_book:
        # Return message about duplicate book
        return jsonify({
            "status": "Duplicate",
            "message": f"Book already exists with Barcode ({existing_book['barcode']}).",
            "details": {
                "book_id": existing_book['book_id'],
                "barcode": barcode,
                "isbn": isbn
            }
        }), 200
    else:
        # Insert new book entry
        cursor.execute(""" 
            INSERT INTO library_books (
                title, author, publisher, isbn, price, pages, copies, 
                accession_number, created_by, barcode, class, section, 
                tags, location, status
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """, (
            title, author, publisher, isbn, price, pages, copies, 
            accession_number, user_role, barcode, class_, section, 
            tags, location, status
        ))
        
        # Commit the changes to the database
        mysql.connection.commit()
        
        return jsonify({
            "message": f"New book (Barcode : {barcode}) added successfully.",
            "status": "Success"
        }), 200
    


    
def process_csv_upload(file, cursor, user_role):
    """ Process CSV file and add books while tracking success and failure status """
    stream = io.StringIO(file.stream.read().decode("utf-8"))
    reader = csv.DictReader(stream)

    added_books = 0
    added_copies = 0
    upload_status = {
        'successful_uploads': [],
        'failed_uploads': [],
        'duplicate_entries': []
    }

    for row in reader:
        isbn = row.get('isbn', '').strip()  # Required
        barcode = row.get('barcode', '').strip()  # Required
        title = row.get('title', '').strip()  # Optional
        author = row.get('author', '').strip()  # Optional
        publisher = row.get('publisher', '').strip()  # Optional
        price = row.get('price', '0.00').strip()  # Optional, default 0.00
        pages = row.get('pages', '').strip()  # Optional
        copies = int(row.get('copies', '1').strip())  # Number of copies (default is 1)
        class_ = row.get('class', '').strip()  # Optional
        section = row.get('section', '').strip()  # Optional
        tags = row.get('tags', '').strip()  # Optional
        location = row.get('location', '').strip()  # Optional
        status = row.get('status', 'Available').strip()  # Optional, default is 'Available'
        accession_number = row.get('accession_number', '').strip()  # Use provided accession number

        # Default missing ISBN/title handling for failure logging
        failed_entry = {
            'isbn': isbn if isbn else 'N/A',
            'barcode': barcode if barcode else 'N/A'
        }

        try:
            # Check for missing required data (both ISBN and Barcode must be provided)
            if not (isbn and barcode):
                failed_entry['reason'] = 'Missing required fields: ISBN and Barcode are mandatory.'
                upload_status['failed_uploads'].append(failed_entry)
                continue

            # Check if book already exists by Barcode
            cursor.execute("SELECT book_id, copies, title, barcode FROM library_books WHERE barcode = %s", (barcode,))
            existing_book = cursor.fetchone()

            if existing_book:
                # Instead of updating, just mark as duplicate
                upload_status['duplicate_entries'].append({
                    'barcode': barcode,
                    'isbn': isbn,
                    'title': existing_book['title'],
                    'message': f"Book already exists with {existing_book['barcode']}"
                })
            else:
                # Insert new book entry
                cursor.execute(""" 
                    INSERT INTO library_books (
                        title, author, publisher, isbn, price, pages, copies, 
                        accession_number, created_by, barcode, class, section, 
                        tags, location, status
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """, (
                    title, author, publisher, isbn, price, pages, copies, 
                    accession_number, user_role, barcode, class_, section, 
                    tags, location, status
                ))
                
                added_books += 1
                added_copies += copies
                
                upload_status['successful_uploads'].append({
                    'isbn': isbn,
                    'barcode': barcode,
                    'copies_added': copies
                })

        except Exception as e:
            failed_entry['reason'] = str(e)
            upload_status['failed_uploads'].append(failed_entry)

    # Commit all changes at the end for better efficiency
    mysql.connection.commit()

    response = {
        "summary": {
            "total_books_added": added_books,
            "total_copies_added": added_copies,
            "total_successful": len(upload_status['successful_uploads']),
            "total_failed": len(upload_status['failed_uploads']),
            "total_duplicates": len(upload_status['duplicate_entries'])
        },
        "details": upload_status
    }

    return jsonify(response), 200


def allowed_file(filename):
    """Check if uploaded file has allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'csv'


@library_app.route('/delete_multiple_books', methods=['DELETE'])
def delete_multiple_books():
    """ Delete multiple books by barcodes """
    librarian_check = verify_librarian()
    admin_check = verify_administrator()

    # Check authorization
    if isinstance(librarian_check, dict):  
        user_role = "librarian"
    elif isinstance(admin_check, dict):  
        user_role = "administrator"
    else:
        return jsonify({"error": "Unauthorized. Only librarians or administrators can perform this action."}), 403

    data = request.json
    barcodes_to_delete = data.get('barcodes', [])  # Expecting a list of barcodes

    if not barcodes_to_delete:
        return jsonify({"error": "No barcodes provided for deletion."}), 400

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Create placeholders for SQL query
    placeholders = ', '.join(['%s'] * len(barcodes_to_delete))
    
    # Get all books with the given barcodes
    query = f"SELECT book_id, barcode, title, status FROM library_books WHERE barcode IN ({placeholders})"
    cursor.execute(query, barcodes_to_delete)
    books = cursor.fetchall()
    
    if not books:
        return jsonify({"error": "No books found with the provided barcodes."}), 404

    deleted_books = []
    failed_books = {}

    for book in books:
        # Check if book is currently borrowed
        if book['status'] == 'Borrowed':
            failed_books[book['barcode']] = "Book is currently borrowed and cannot be deleted"
            continue
            
        deleted_books.append({
            "barcode": book['barcode'],
            "title": book['title'],
            "book_id": book['book_id']
        })

    # Delete eligible books in a single query
    if deleted_books:
        barcodes_to_delete = [book['barcode'] for book in deleted_books]
        placeholders = ', '.join(['%s'] * len(barcodes_to_delete))
        delete_query = f"DELETE FROM library_books WHERE barcode IN ({placeholders})"
        cursor.execute(delete_query, barcodes_to_delete)

    # Commit changes
    mysql.connection.commit()

    return jsonify({
        "message": f"{len(deleted_books)} books deleted.",
        "deleted_books": deleted_books,
        "failed_books": failed_books
    }), 200


@library_app.route('/get_all_books', methods=['GET'])
def get_all_books():
    """ Fetches books with their details in paginated batches for infinite scroll """
    
    # Get the page number and page size from the query parameters (defaults to 1 and 1000 if not provided)
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 500, type=int)
    
    # Calculate the offset based on the current page
    offset = (page - 1) * page_size

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    cursor.execute("""
        SELECT 
            title, author, 
            barcode, status,accession_number
        FROM library_books
        ORDER BY title ASC
        LIMIT %s OFFSET %s
    """, (page_size, offset))
    
    books = cursor.fetchall()
    
    if not books:
        return jsonify({"error": "No more books found"}), 404
    
    # Convert MySQL timestamp objects to strings for JSON serialization
    # for book in books:
    #     if 'created_at' in book and book['created_at']:
    #         book['created_at'] = book['created_at'].strftime('%Y-%m-%d %H:%M:%S')
    #     if 'updated_at' in book and book['updated_at']:
    #         book['updated_at'] = book['updated_at'].strftime('%Y-%m-%d %H:%M:%S')
    
    return jsonify({"books": books}), 200




@library_app.route('/issue_book', methods=['POST'])
def issue_book():
    """ Librarians and Administrators can issue books to students """
    librarian_check = verify_librarian()
    admin_check = verify_administrator()

    # Check authorization
    if isinstance(librarian_check, tuple) and isinstance(admin_check, tuple):
        return jsonify({"error": "Unauthorized. Only librarians or administrators can perform this action."}), 403

    data = request.json
    admission_no = data.get('admission_no')  # Student Admission Number
    student_name_input = data.get('student_name', '').strip().lower()  # Normalize for comparison
    barcode = data.get('barcode')  # Use barcode instead of isbn
    issuer_session_id = data.get('session_id')  # ✅ Get issuer's session_id from request
    session_name = data.get('session_name', 'Unknown Session')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    try:
        # 🔹 Step 1: Fetch `session_id`, `class_section_id`, and `roll_no` for the student
        cursor.execute("""
            SELECT se.student_id, se.session_id, se.class_section_id, se.roll_no, 
                   s.name AS student_name, sc.section
            FROM sms_student_enrollments se
            JOIN sms_students s ON se.student_id = s.id
            JOIN sms_class_section sc ON se.class_section_id = sc.class_section_id
            WHERE s.admission_no = %s
            ORDER BY se.session_id DESC LIMIT 1
        """, (admission_no,))

        student_record = cursor.fetchone()

        if not student_record:
            return jsonify({"error": "Student details do not match our records. Please verify and try again."}), 400

        student_id = student_record['student_id']
        student_name_db = student_record['student_name'].strip().lower()
        section = student_record['section']
        student_session_id = student_record['session_id']  # ✅ Student's session ID
        class_section_id = student_record['class_section_id']
        roll_no = student_record['roll_no']

        # 🔹 Step 2: Verify Student Name Matches Admission Number
        if student_name_db != student_name_input:
            return jsonify({"error": "Student name does not match our records for this admission number"}), 400

        # 🔹 Step 3: Verify Issuer's Session Matches Student's Session
        if int(issuer_session_id) != int(student_session_id):
            return jsonify({"error": "Session ID mismatch! Book can only be issued in the same session."}), 400

        # 🔹 Step 4: Find `book_id` using `barcode`
        cursor.execute("SELECT book_id FROM library_books WHERE barcode = %s", (barcode,))
        book_record = cursor.fetchone()

        if not book_record:
            return jsonify({"error": "No book found with this barcode."}), 400

        book_id = book_record['book_id']

        # 🔹 Step 5: Check if the Book Copy Exists and is Available using `barcode`
        cursor.execute("""
            SELECT barcode, status FROM library_books 
            WHERE barcode = %s AND book_id = %s
        """, (barcode, book_id))
        book_copy = cursor.fetchone()

        # Check if the book copy exists and is available for issue
        if not book_copy:
            return jsonify({"error": "No book found with this barcode."}), 400
        if book_copy['status'] != 'Available':
            return jsonify({"error": "Book copy is not available for issue."}), 400

        # 🔹 Step 6: Check if Student Already Borrowed 3 Books
        cursor.execute("""
            SELECT COUNT(*) AS total_issued 
            FROM library_book_issues 
            WHERE student_id = %s AND status = 'issued'
        """, (student_id,))
        issued_count = cursor.fetchone()['total_issued']

        if issued_count >= 3:
            return jsonify({"error": "Student has already reached the borrowing limit (3 books)"}), 400

        # 🔹 Step 7: Calculate Due Date (Default: 14 Days from Today)
        issue_date = datetime.date.today()
        due_date = issue_date + datetime.timedelta(days=14)

        # Start Transaction
        cursor.execute("START TRANSACTION")

        # 🔹 Step 8: Insert into `library_book_issues`
        cursor.execute("""
            INSERT INTO library_book_issues 
            (book_id, barcode, student_id, session_id, session_name, class_section_id, roll_no, 
             admission_no, student_name, section, issue_date, due_date, status) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'issued')
        """, (book_id, barcode, student_id, student_session_id, session_name, class_section_id, roll_no, 
              admission_no, student_name_db, section, issue_date, due_date))

        # 🔹 Step 9: Update `library_books` to Mark as Borrowed
        cursor.execute("""
            UPDATE library_books
            SET status = 'Borrowed' 
            WHERE barcode = %s AND book_id = %s
        """, (barcode, book_id))

        # 🔹 Step 10: Decrease `copies` in `library_books`
        cursor.execute("""
            UPDATE library_books 
            SET copies = copies - 1 
            WHERE book_id = %s AND copies > 0
        """, (book_id,))

        # Commit the transaction
        mysql.connection.commit()

        return jsonify({
            "message": "Book issued successfully",
            "admission_no": admission_no,
            "student_name": student_name_db,
            "session_id": student_session_id,
            "session_name": session_name, 
            "class_section_id": class_section_id,
            "roll_no": roll_no,
            "barcode": barcode,  # Include barcode in response
            "issue_date": str(issue_date),
            "due_date": str(due_date)
        }), 200

    except Exception as e:
        mysql.connection.rollback()  # Rollback in case of error
        return jsonify({"error": f"An error occurred while issuing the book: {str(e)}"}), 500

    finally:
        cursor.close()



@library_app.route('/get_borrowed_books', methods=['GET'])
def get_borrowed_books():
    """ Fetch all books a student has borrowed and not yet returned using GET method """

    admission_no = request.args.get('admission_no')  # 🔹 Student Admission Number
    student_name_input = request.args.get('student_name')  # 🔹 Student Name for verification

    if not admission_no or not student_name_input:
        return jsonify({"error": "Missing required parameters: admission_no and student_name"}), 400

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # 🔹 Step 1: Validate Student Exists and Fetch `student_id`
    cursor.execute("""
        SELECT id AS student_id, name AS student_name
        FROM sms_students
        WHERE admission_no = %s
    """, (admission_no,))

    student_record = cursor.fetchone()

    if not student_record:
        return jsonify({"error": "No student found with this admission number"}), 404

    student_id = student_record['student_id']
    student_name_db = student_record['student_name']

    # 🔹 Step 2: Verify Student Name Matches Admission Number
    if student_name_db.lower() != student_name_input.lower():
        return jsonify({"error": "Student name does not match our records for this admission number"}), 400

    # 🔹 Step 3: Fetch All Books Borrowed by the Student and Not Yet Returned
    cursor.execute("""
        SELECT 
            lbi.issue_id,
            lb.isbn,
            lb.author,
            lb.publisher,
            lb.accession_number,
            lb.title,
            lb.barcode,  -- Using barcode to identify the copy
            lbi.issue_date,
            lbi.due_date,
            CASE 
                WHEN CURDATE() > lbi.due_date THEN 'Overdue'
                ELSE 'On Time'
            END AS status,
            CASE 
                WHEN CURDATE() > lbi.due_date THEN DATEDIFF(CURDATE(), lbi.due_date) * 5
                ELSE 0
            END AS fine_amount
        FROM library_book_issues lbi
        JOIN library_books lb ON lbi.book_id = lb.book_id
        WHERE lbi.student_id = %s AND lbi.status = 'issued'
        ORDER BY lbi.due_date ASC
    """, (student_id,))

    borrowed_books = cursor.fetchall()

    if not borrowed_books:
        return jsonify({"message": "No borrowed books found"}), 200

    mysql.connection.commit()

    return jsonify({
        "message": "Borrowed books fetched successfully",
        "admission_no": admission_no,
        "student_name": student_name_db,
        "borrowed_books": borrowed_books
    }), 200



@library_app.route('/return_book', methods=['POST'])
def return_book():
    """ Handles book return, fine calculation, and storing fine details if applicable """
    librarian_check = verify_librarian()
    admin_check = verify_administrator()

    if isinstance(librarian_check, tuple) and isinstance(admin_check, tuple):
        return jsonify({"error": "Unauthorized. Only librarians or administrators can perform this action."}), 403

    data = request.json
    admission_no = data.get('admission_no')
    barcode = data.get('barcode')  # Changed from accession_number to barcode
    # isbn = data.get('isbn')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # 🔹 Step 1: Fetch data from `library_book_issues` and verify both barcode and admission number match
    cursor.execute("""
        SELECT issue_id, student_id, session_id, class_section_id, roll_no, 
               admission_no, student_name, issue_date, due_date, return_date, book_id, barcode
        FROM library_book_issues
        WHERE barcode = %s AND admission_no = %s AND status = 'issued'
    """, (barcode, admission_no))
    
    issue_record = cursor.fetchone()
    
    if not issue_record:
        return jsonify({"error": "No active issue record found for this barcode and admission number"}), 404

    # Extract data from the issue record
    issue_id = issue_record['issue_id']
    student_id = issue_record['student_id']
    session_id = issue_record['session_id']  # 🔹 Retains original session_id
    class_section_id = issue_record['class_section_id']  # 🔹 Retains original class_section_id
    roll_no = issue_record['roll_no']  # 🔹 Retains original roll_no
    admission_no = issue_record['admission_no']
    student_name_db = issue_record['student_name']  # 🔹 Retains original student_name
    issue_date = issue_record['issue_date']
    due_date = issue_record['due_date']
    return_date = datetime.date.today()
    book_id = issue_record['book_id']
    barcode_db = issue_record['barcode']

    # 🔹 Step 2: Check if Fine is Required
    fine_amount = 0
    if return_date > due_date:
        days_late = (return_date - due_date).days
        fine_amount = days_late * 5  # ₹5 per day

    cursor.execute("START TRANSACTION")

    # 🔹 Step 3: Update Book Issue Status to 'returned'
    cursor.execute("""
        UPDATE library_book_issues 
        SET return_date = %s, status = 'returned'
        WHERE issue_id = %s
    """, (return_date, issue_id))

    # 🔹 Step 4: Update Book Copy Status to "Available"
    cursor.execute("""
        UPDATE library_books 
        SET status = 'Available' 
        WHERE barcode = %s
    """, (barcode,))

    # 🔹 Step 5: Increase Copies in `library_books`
    cursor.execute("""
        UPDATE library_books 
        SET copies = copies + 1 
        WHERE book_id = %s
    """, (book_id,))

    # 🔹 Step 6: Insert Fine Record if Overdue
    if fine_amount > 0:
        cursor.execute("""
            INSERT INTO library_fines 
            (issue_id, student_id, student_name, admission_no, session_id, class_section_id, roll_no, 
             fine_amount, payment_status, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'unpaid', NOW())
        """, (issue_id, student_id, student_name_db, admission_no, session_id, class_section_id, roll_no, fine_amount))

    # 🔹 Step 7: Remove transactions older than 7 days (optional cleanup)
    cursor.execute("""
        DELETE FROM library_book_issues 
        WHERE status = 'returned' AND return_date <= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
    """)

    mysql.connection.commit()

    return jsonify({
        "message": "Book returned successfully",
        "admission_no": admission_no,
        "student_name": student_name_db,
        # "isbn": isbn,
        "barcode": barcode,  # Include barcode in response
        "issue_date": str(issue_date),
        "due_date": str(due_date),
        "return_date": str(return_date),
        "fine_amount": fine_amount
    }), 200


@library_app.route('/api/library_statistics', methods=['GET'])
def get_library_statistics():
    """
    Returns summary statistics of the library:
    - Total Books
    - Available Books
    - Issued Books
    - Fine Collected
    - Borrowed Books (same as Issued Books)
    """
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Total Books in Library
    cursor.execute("SELECT COUNT(*) AS total_books FROM library_books")
    total_books = cursor.fetchone()['total_books']
    
    # Total Available Books
    cursor.execute("""
        SELECT SUM(copies) AS total_available_copy
        FROM library_books
        WHERE status = 'Available'
    """)
    total_available_copy = cursor.fetchone()['total_available_copy'] or 0
    
    # Total Issued/Borrowed Books
    cursor.execute("SELECT COUNT(*) AS total_issued_copy FROM library_book_issues WHERE status = 'issued'")
    total_issued_copy = cursor.fetchone()['total_issued_copy']
    
    # Total Fine Collected
    cursor.execute("""
        SELECT SUM(fine_amount) AS total_fine_collected
        FROM library_fines
        WHERE payment_status = 'paid'
    """)
    total_fine_collected = cursor.fetchone()['total_fine_collected'] or 0
    
    return jsonify({
        "total_books": total_books,
        "available_books": total_available_copy,
        "issued_books": total_issued_copy,
        "borrowed_books": total_issued_copy,  # Same as issued books
        "fine_collected": total_fine_collected
    }), 200


@library_app.route('/api/books', methods=['GET'])
def get_books():
    """
    Returns available books with pagination support for infinite scrolling.
    
    Query parameters:
    - status: Filter by book status ('available', 'issued', or 'all')
    - page: Page number (default: 1)
    - per_page: Number of books per page (default: 200)
    """
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Get query parameters
    status = request.args.get('status', 'all').lower()
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 500))
    
    # Calculate offset for pagination
    offset = (page - 1) * per_page
    
    # Prepare base query
    if status == 'available':
        query = """
            SELECT
                lb.author, lb.title, 
                lb.barcode,
                lb.location
            FROM library_books lb
            WHERE lb.status = 'Available'
        """
    elif status == 'issued' or status == 'borrowed':
        query = """
            SELECT
                lb.author, lb.title,
                lb.barcode,
                lbi.issue_date, lbi.due_date,
                ss.name AS student_name,
                scs.class_number AS class,
                lbi.roll_no AS roll,
                scs.section
            FROM library_book_issues lbi
            JOIN library_books lb ON lbi.book_id = lb.book_id
            JOIN sms_students ss ON lbi.student_id = ss.id
            JOIN academic_sessions asess ON lbi.session_id = asess.session_id
            JOIN sms_class_section scs ON lbi.class_section_id = scs.class_section_id
            WHERE lbi.status = 'issued'
        """
    else:  # 'all'
        query = """
            SELECT 
                lb.author, lb.title, 
                lb.barcode,
                lb.location,
                lb.status
            FROM library_books lb
        """
    
    # Count total results for pagination metadata
    count_query = f"SELECT COUNT(*) as total FROM ({query}) as count_query"
    cursor.execute(count_query)
    total_books = cursor.fetchone()['total']
    
    # Add pagination to query
    query += f" LIMIT {per_page} OFFSET {offset}"
    
    # Execute final query
    cursor.execute(query)
    books = cursor.fetchall()
    
    # Calculate pagination metadata
    total_pages = (total_books + per_page - 1) // per_page
    has_more = page < total_pages
    
    return jsonify({
        "books": books,
        "pagination": {
            "current_page": page,
            "per_page": per_page,
            "total_books": total_books,
            "total_pages": total_pages,
            "has_more": has_more
        }
    }), 200



@library_app.route('/student_issued_books', methods=['GET'])
def student_issued_books():
    """ Returns only books that are currently issued to the logged-in student """

    # 🔹 Step 1: Get Student ID from JWT Token (Authorization Header)
    token = request.headers.get("Authorization")
    if not token:
        return jsonify({"error": "Token is missing"}), 401

    try:
        token = token.split(" ")[1]  # Remove "Bearer " prefix
        decoded_token = jwt.decode(token, current_app.secret_key, algorithms=["HS256"])  # ✅ Use `current_app.secret_key`
        student_id = decoded_token.get("id")  # Extract Student ID from Token
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Token expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Invalid token"}), 401

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # 🔹 Step 2: Fetch Only Books That Are Still Issued (Not Yet Returned) & Include ISBN
    cursor.execute("""
        SELECT 
            lb.isbn, lb.title, lb.author, lbi.barcode, lb.accession_number,
            lbi.issue_date, lbi.due_date,
            CASE 
                WHEN CURDATE() > lbi.due_date THEN 'Overdue'
                ELSE 'On Time'
            END AS status,
            CASE 
                WHEN CURDATE() > lbi.due_date THEN DATEDIFF(CURDATE(), lbi.due_date) * 5
                ELSE 0
            END AS fine_amount  -- ₹5 per day fine after the due date
        FROM library_book_issues lbi
        JOIN library_books lb ON lbi.book_id = lb.book_id  -- ✅ Fetching ISBN from `library_books`
        WHERE lbi.student_id = %s AND lbi.status = 'issued'
        ORDER BY lbi.due_date ASC
    """, (student_id,))

    issued_books = cursor.fetchall()

    if not issued_books:
        return jsonify({"message": "No currently issued books found"}), 200

    return jsonify({
        "student_id": student_id,
        "issued_books": issued_books
    }), 200


@library_app.route('/fetch_fine', methods=['GET'])
def fetch_fine():
    """ Fetch all unpaid fines across all students with class, section, and roll number """
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # 🔹 Fetch all unpaid fines with student details including class, section, and roll number
    cursor.execute("""
        SELECT lf.fine_id, lf.issue_id, lf.fine_amount, lf.session_id, lf.class_section_id, lf.roll_no,
               lf.created_at, lf.admission_no, ss.name AS student_name, 
               lb.title AS book_title, lbi.barcode,
               asess.session_name AS session, scs.class_number AS class, scs.section,
               COALESCE(SUM(lf.paid_amount), 0) AS total_paid_fine  -- Get total paid fines
        FROM library_fines lf
        JOIN library_book_issues lbi ON lf.issue_id = lbi.issue_id
        JOIN library_books lb ON lbi.book_id = lb.book_id
        JOIN sms_students ss ON lf.student_id = ss.id
        JOIN academic_sessions asess ON lf.session_id = asess.session_id
        JOIN sms_class_section scs ON lf.class_section_id = scs.class_section_id
        WHERE lf.payment_status = 'unpaid'
        GROUP BY lf.fine_id, lf.issue_id, lf.student_id, lf.admission_no, ss.name, lb.title, lbi.barcode, scs.class_number, scs.section
        ORDER BY lf.created_at DESC
    """)

    fines = cursor.fetchall()

    if not fines:
        return jsonify({"error": "No unpaid fines found"}), 404

    return jsonify({
        "unpaid_fines": fines
    }), 200


@library_app.route('/pay_fine', methods=['POST'])
def pay_fine():
    """ Allows the librarian to mark selected fines as paid """
    data = request.json
    fine_ids = data.get('fine_ids', [])  # List of specific fine IDs to be marked as paid
    payment_method = data.get('payment_method', 'cash')  # Default payment method

    if not fine_ids:
        return jsonify({"error": "No fine IDs provided"}), 400

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # 🔹 Step 1: Fetch fine details for validation
    cursor.execute("""
        SELECT lf.fine_id, lf.issue_id, lf.student_id, lf.fine_amount, lf.paid_amount, lf.payment_status,
               ss.name AS student_name, ss.admission_no
        FROM library_fines lf
        JOIN sms_students ss ON lf.student_id = ss.id
        WHERE lf.fine_id IN %s AND lf.payment_status = 'unpaid'
    """, (tuple(fine_ids),))

    fine_records = cursor.fetchall()

    if not fine_records:
        return jsonify({"error": "No valid unpaid fines found"}), 404

    total_fine_due = 0
    student_id = fine_records[0]['student_id']  # Fetch the student_id from the first record
    for fine_record in fine_records:
        total_fine_due += fine_record['fine_amount']

    # 🔹 Step 2: Mark selected fines as paid and store payment date (only date, no time)
    for fine_record in fine_records:
        cursor.execute("""
            UPDATE library_fines 
            SET paid_amount = paid_amount + %s, payment_status = 'paid', payment_date = CURDATE(),
                payment_method = %s
            WHERE fine_id = %s
        """, (fine_record['fine_amount'], payment_method, fine_record['fine_id']))

    # 🔹 Step 3: Commit the transaction
    mysql.connection.commit()

    cursor.close()

    return jsonify({
        "message": "Selected fines paid successfully",
        "total_fine_paid": total_fine_due,
        "payment_method": payment_method,
        "payment_date": str(datetime.date.today()),  # Only "YYYY-MM-DD"
        "paid_fine_ids": fine_ids,
        "student_name": fine_records[0]['student_name'],
        "admission_no": fine_records[0]['admission_no']
    }), 200


@library_app.route('/get_students_name', methods=['GET'])
def get_student_by_admission():
    admission_no = request.args.get('admission_no')

    if not admission_no:
        return jsonify({"error": "Admission number is required"}), 400

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Fetch the student from the database by admission_no
    cursor.execute("""
        SELECT name FROM sms_students WHERE admission_no = %s
    """, (admission_no,))

    student = cursor.fetchone()

    if student:
        return jsonify({"name": student['name']}), 200
    else:
        return jsonify({"error": "Student not found"}), 404




@library_app.route('/get_book_by_barcode', methods=['GET'])
def get_book_by_barcode():
    """ Fetches a book by its barcode """

    # Get the barcode from the query parameters
    barcode = request.args.get('barcode', None, type=str)
    
    if not barcode:
        return jsonify({"error": "Barcode is required"}), 400
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    cursor.execute("""
        SELECT 
            title, author, publisher, isbn, barcode, copies, status, accession_number
        FROM library_books
        WHERE barcode = %s
    """, (barcode,))
    
    book = cursor.fetchone()
    
    if not book:
        return jsonify({"error": "Book not found with the provided barcode"}), 404

    return jsonify({"book": book}), 200






