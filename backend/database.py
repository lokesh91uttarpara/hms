from flask_mysqldb import MySQL

mysql = MySQL()

def init_db(app):
    """Initialize the database with the Flask app"""
    app.config['MYSQL_HOST'] = 'localhost'
    app.config['MYSQL_USER'] = 'root'
    app.config['MYSQL_PASSWORD'] = 'Rahul@12345'
    app.config['MYSQL_DB'] = 'hotel_db'
    
    mysql.init_app(app)