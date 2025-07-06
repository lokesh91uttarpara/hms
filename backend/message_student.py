from flask import jsonify
from MySQLdb.cursors import DictCursor
from zoneinfo import ZoneInfo
import datetime 
import firebase_admin
from firebase_admin import credentials, messaging


def send_push_notification(token, title, body):
    """
    Sends a push notification to a device with the given FCM token.
    
    Args:
        token (str): The FCM token of the device.
        title (str): The title of the notification.
        body (str): The notification body.
    
    Returns:
        The response from FCM.
    """
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            token=token,
        )
        response = messaging.send(message)
        print(f"Sending FCM notification to {token} with title '{title}' and body '{body}'")

        print("Push notification sent, response:", response)
        return response
    except Exception as e:
        print("Error sending push notification:", str(e))
        return None

def send_message_to_students(data, db_connection):
    """
    Sends a message to one or multiple students and pushes notifications.
    
    Args:
        data (dict): Contains `admission_no` (list) and `message` (string).
        db_connection: MySQL database connection object.
    
    Returns:
        JSON response indicating the success or failure of the operation.
    """
    try:
        # Extract admission numbers and message from the data
        admission_nos = data.get('admission_no', [])
        message_text = data.get('message', '').strip()

        if not admission_nos or not message_text:
            return jsonify({"error": "Admission numbers and message are required"}), 400

        # Ensure `admission_no` is a list
        if not isinstance(admission_nos, list):
            admission_nos = [admission_nos]

        # Include the FCM token in the query (assumes column name 'fcm_token')
        query = '''
            SELECT admission_no, name, mobile, email, fcm_token 
            FROM sms_students 
            WHERE admission_no IN (%s)
        ''' % ', '.join(['%s'] * len(admission_nos))

        cursor = db_connection.cursor(DictCursor)
        cursor.execute(query, admission_nos)
        students = cursor.fetchall()

        if not students:
            return jsonify({"error": "No students found for the provided admission numbers"}), 404

        # Simulate sending messages (e.g., SMS, email, etc.) and send push notifications
        for student in students:
            # Simulated message sending (e.g., logging or sending via SMS)
            print(f"Message sent to {student['name']} ({student['admission_no']}): {message_text}")

            # If the student has an FCM token, send a push notification
            fcm_token = student.get('fcm_token')
            if fcm_token:
                title = "New Message from Admin"
                send_push_notification(fcm_token, title, message_text)

        # Log messages in the database
        log_messages(admission_nos, message_text, db_connection)

        return jsonify({"message": "Messages sent successfully", "students": students}), 200

    except Exception as e:
        print("Error in send_message_to_students:", str(e))
        return jsonify({"error": "Server error occurred"}), 500


def log_messages(admission_nos, message, db_connection):
    """
    Logs messages sent to students in a `message_log` table.

    Args:
        admission_nos (list): List of admission numbers.
        message (str): The message sent.
        db_connection: MySQL database connection object.
    """
    try:
        # Compute current time in IST
        sent_time = datetime.datetime.now(ZoneInfo("Asia/Kolkata"))
        
        query = '''
            INSERT INTO message_log (admission_no, message, sent_time, read_unread) 
            VALUES (%s, %s, %s, 0)
        '''
        cursor = db_connection.cursor()
        for admission_no in admission_nos:
            cursor.execute(query, (admission_no, message, sent_time))
        db_connection.commit()
        cursor.close()
    except Exception as e:
        print("Error in log_messages:", str(e))        

def fetch_student_messages(admission_no, db_connection):
    """
    Fetches all messages sent to a specific student.

    Args:
        admission_no (int): The admission number of the student.
        db_connection: MySQL database connection object.

    Returns:
        JSON response with the list of messages.
    """
    try:
        query = '''
            SELECT id, message, sent_time, read_unread
            FROM message_log 
            WHERE admission_no = %s 
            ORDER BY sent_time DESC
        '''
        cursor = db_connection.cursor(DictCursor)
        cursor.execute(query, (admission_no,))
        messages = cursor.fetchall()
        cursor.close()

        if not messages:
            return jsonify({"messages": []}), 200

        return jsonify({"messages": messages}), 200

    except Exception as e:
        print("Error in fetch_student_messages:", str(e))
        return jsonify({"error": "Server error occurred"}), 500