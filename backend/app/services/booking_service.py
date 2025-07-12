def get_all_bookings(conn):
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM bookings")
        return cursor.fetchall()