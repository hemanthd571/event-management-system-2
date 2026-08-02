from app.dal import get_db_connection

def test_decline():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # First, clean up waitlist table and populate it
            cursor.execute("DELETE FROM venue_waitlist")
            
            # Insert User 2 and User 3 into waitlist
            cursor.execute("INSERT INTO venue_waitlist (user_id, venue_id, event_date, start_time, end_time, status) VALUES (1, 1, '2026-11-03', '10:00:00', '12:00:00', 'waiting')")
            user2_id = cursor.lastrowid
            
            cursor.execute("INSERT INTO venue_waitlist (user_id, venue_id, event_date, start_time, end_time, status) VALUES (2, 1, '2026-11-03', '10:00:00', '12:00:00', 'waiting')")
            user3_id = cursor.lastrowid
            
            # Now simulate cancel_event (User 2 becomes reserved)
            cursor.execute("UPDATE venue_waitlist SET status = 'reserved', reserved_until = DATE_ADD(NOW(), INTERVAL 24 HOUR) WHERE id = %s", (user2_id,))
            
            # Now simulate User 2 decline
            cursor.execute('SELECT * FROM venue_waitlist WHERE id = %s', (user2_id,))
            entry = cursor.fetchone()
            
            cursor.execute("UPDATE venue_waitlist SET status = 'expired' WHERE id = %s", (user2_id,))
            
            # Find next person
            cursor.execute('''SELECT vw.id, vw.start_time, vw.end_time
                              FROM venue_waitlist vw
                              WHERE vw.venue_id = %s AND vw.event_date = %s AND vw.status = 'waiting'
                              AND (vw.start_time IS NULL OR vw.end_time IS NULL OR %s IS NULL OR %s IS NULL OR (vw.start_time < %s AND vw.end_time > %s))
                              ORDER BY vw.created_at ASC
                              LIMIT 1
                           ''', (entry['venue_id'], entry['event_date'], entry['start_time'], entry['end_time'], entry['end_time'], entry['start_time']))
            next_user = cursor.fetchone()
            print("Next user with times:", next_user)
            
            
            # NOW TEST WITH NULL TIMES
            cursor.execute("DELETE FROM venue_waitlist")
            cursor.execute("INSERT INTO venue_waitlist (user_id, venue_id, event_date, start_time, end_time, status) VALUES (1, 1, '2026-11-03', NULL, NULL, 'waiting')")
            user2_id = cursor.lastrowid
            
            cursor.execute("INSERT INTO venue_waitlist (user_id, venue_id, event_date, start_time, end_time, status) VALUES (2, 1, '2026-11-03', '10:00:00', '12:00:00', 'waiting')")
            user3_id = cursor.lastrowid
            
            # Now simulate cancel_event (User 2 becomes reserved)
            cursor.execute("UPDATE venue_waitlist SET status = 'reserved', reserved_until = DATE_ADD(NOW(), INTERVAL 24 HOUR) WHERE id = %s", (user2_id,))
            
            # Now simulate User 2 decline
            cursor.execute('SELECT * FROM venue_waitlist WHERE id = %s', (user2_id,))
            entry = cursor.fetchone()
            
            cursor.execute("UPDATE venue_waitlist SET status = 'expired' WHERE id = %s", (user2_id,))
            
            # Find next person
            cursor.execute('''SELECT vw.id, vw.start_time, vw.end_time
                              FROM venue_waitlist vw
                              WHERE vw.venue_id = %s AND vw.event_date = %s AND vw.status = 'waiting'
                              AND (vw.start_time IS NULL OR vw.end_time IS NULL OR %s IS NULL OR %s IS NULL OR (vw.start_time < %s AND vw.end_time > %s))
                              ORDER BY vw.created_at ASC
                              LIMIT 1
                           ''', (entry['venue_id'], entry['event_date'], entry['start_time'], entry['end_time'], entry['end_time'], entry['start_time']))
            next_user = cursor.fetchone()
            print("Next user when User 2 has NULL times:", next_user)
            conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    test_decline()
