

from flask_mail import Mail, Message
import MySQLdb.cursors
from datetime import datetime, timedelta
import threading
import time
import logging
from flask import current_app

# Initialize Flask-Mail
mail = Mail()

def init_app(app):
    """ Initialize Flask-Mail with app settings """
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = 'scabca2020@gmail.com'  # 🔹 Replace with env variable
    app.config['MAIL_PASSWORD'] = 'cjdd ogze qfaa ftaj'     # 🔹 Replace with env variable
    app.config['MAIL_DEFAULT_SENDER'] = 'scabca2020@gmail.com' # 🔹Replace with env variable
    mail.init_app(app)


def send_email(to_email, subject, message):
    """ Sends an email to the student """
    try:
        msg = Message(
            subject, 
            sender=current_app.config['MAIL_DEFAULT_SENDER'],  # ✅ Set sender
            recipients=[to_email]
        )
        msg.body = message
        mail.send(msg)
        logging.info(f"✅ Email sent to {to_email}")
    except Exception as e:
        logging.error(f"❌ Error sending email to {to_email}: {str(e)}")



def check_due_dates(app, mysql):
    """ Fetch students with books due soon or overdue and send email reminders """
    with app.app_context():
        try:
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

            # 🔹 Get Books Due in 2 Days
            cursor.execute("""
                SELECT 
                    ss.email, ss.name AS student_name, 
                    lb.title, lb.author, 
                    lbi.due_date, lbi.issue_date
                FROM library_book_issues lbi
                JOIN sms_students ss ON lbi.student_id = ss.id
                JOIN library_books lb ON lbi.book_id = lb.book_id
                WHERE lbi.status = 'issued'
                AND lbi.return_date IS NULL  -- ✅ Exclude returned books
                AND DATEDIFF(lbi.due_date, CURDATE()) = 2
            """)
            books_due_soon = cursor.fetchall()

            for book in books_due_soon:
                subject = f"📚 Library Reminder: Book Due in 2 Days"
                message = (f"Hello {book['student_name']},\n\n"
                          f"Your book '{book['title']}' by {book['author']}' is due on {book['due_date']}.\n"
                          f"Please return it on time to avoid fines.\n\n"
                          f"Thanks,\nLibrary Team")
                send_email(book['email'], subject, message)

            # 🔹 Get Overdue Books (Reminder in Every 7 Days)
            cursor.execute("""
                SELECT 
                    ss.email, ss.name AS student_name, 
                    lb.title, lb.author, 
                    lbi.due_date, lbi.issue_date, 
                    DATEDIFF(CURDATE(), lbi.due_date) * 5 AS fine_amount
                FROM library_book_issues lbi
                JOIN sms_students ss ON lbi.student_id = ss.id
                JOIN library_books lb ON lbi.book_id = lb.book_id
                WHERE lbi.status = 'issued'
                AND lbi.return_date IS NULL  -- ✅ Exclude returned books
                AND DATEDIFF(CURDATE(), lbi.due_date) > 0
                AND MOD(DATEDIFF(CURDATE(), lbi.due_date), 7) = 0
            """)
            overdue_books = cursor.fetchall()

            for book in overdue_books:
                subject = f"⚠️ Overdue Library Book: {book['title']}"
                message = (f"Dear {book['student_name']},\n\n"
                          f"Your book '{book['title']}' by {book['author']}' was due on {book['due_date']}.\n"
                          f"You now have a fine of ₹{book['fine_amount']}.\n"
                          f"Please return the book and pay the fine as soon as possible.\n\n"
                          f"Thanks,\nLibrary Team")
                send_email(book['email'], subject, message)

            cursor.close()

        except Exception as e:
            logging.error(f"❌ Error in check_due_dates: {str(e)}")



def run_scheduler(app, mysql):
    """ Runs `check_due_dates()` every 24 hours in the background """
    while True:
        try:
            check_due_dates(app, mysql)
        except Exception as e:
            logging.error(f"❌ Error in scheduler: {str(e)}")
        time.sleep(86400)  # ✅ Runs every 24 hours



def start_scheduler(app, mysql):
    """ Initialize the scheduler thread """
    thread = threading.Thread(target=run_scheduler, args=(app, mysql))
    thread.daemon = True
    thread.start()
    logging.info("📬 Email scheduler started successfully")
