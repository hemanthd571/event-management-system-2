import os
from flask import Flask
from flask_login import LoginManager
from flask_mail import Mail
from config import Config

login_manager = LoginManager()
mail = Mail()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    login_manager.init_app(app)
    mail.init_app(app)

    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.events import events_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(admin_bp)
    
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    with app.app_context():
        from app.dal import get_db_connection
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS venue_waitlist (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id INT NOT NULL,
                        venue_id INT NOT NULL,
                        event_date DATE NOT NULL,
                        start_time TIME NULL,
                        end_time TIME NULL,
                        status VARCHAR(50) DEFAULT 'waiting',
                        reserved_until TIMESTAMP NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                        FOREIGN KEY (venue_id) REFERENCES venues(id) ON DELETE CASCADE
                    )
                ''')
                conn.commit()
            
            # Separate transaction for alter table to prevent transaction abort on error
            with conn.cursor() as cursor:
                try:
                    cursor.execute('ALTER TABLE venue_waitlist ADD COLUMN start_time TIME NULL')
                    conn.commit()
                except Exception:
                    conn.rollback()
                
                try:
                    cursor.execute('ALTER TABLE venue_waitlist ADD COLUMN end_time TIME NULL')
                    conn.commit()
                except Exception:
                    conn.rollback()
                    
                try:
                    cursor.execute('ALTER TABLE venue_waitlist ADD COLUMN reserved_until TIMESTAMP NULL')
                    conn.commit()
                except Exception:
                    conn.rollback()
                    
            conn.close()
        except Exception as e:
            print(f"Failed to create venue_waitlist table: {e}")

    if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        from apscheduler.schedulers.background import BackgroundScheduler
        import atexit
        
        scheduler = BackgroundScheduler()
        scheduler.add_job(func=check_and_send_reminders, args=[app], trigger="interval", hours=1)
        scheduler.add_job(func=check_waitlist_expiries, args=[app], trigger="interval", hours=1)
        scheduler.start()
        atexit.register(lambda: scheduler.shutdown())

    return app

def check_and_send_reminders(app):
    with app.app_context():
        from app.db_manager import get_db_connection
        from datetime import date, timedelta
        from app.routes.events import send_email_notification
        
        target_date = date.today() - timedelta(days=3)
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    '''SELECT e.id, e.title, e.event_date, u.email, u.username, e.organizer_id 
                       FROM events e 
                       JOIN users u ON e.organizer_id = u.id 
                       WHERE e.status = 'Approved' 
                       AND e.event_date <= %s 
                       AND e.reminder_sent = 0 
                       AND (e.post_event_report_path IS NULL OR e.post_event_report_path = '')''',
                    (target_date,)
                )
                events_to_remind = cursor.fetchall()
                
                for event in events_to_remind:
                    cursor.execute('UPDATE events SET reminder_sent = 1 WHERE id = %s', (event['id'],))
                    conn.commit()
                    
                    send_email_notification(
                        event['email'],
                        "Action Required: Missing Event Proof",
                        f"Dear {event['username']},\n\nPlease upload your event proof immediately for the event '{event['title']}' which occurred on {event['event_date']}."
                    )
        except Exception as e:
            pass
        finally:
            conn.close()

def check_waitlist_expiries(app):
    with app.app_context():
        from app.db_manager import get_db_connection
        from app.routes.events import send_email_notification
        from flask import url_for
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Find expired reservations
                cursor.execute("SELECT * FROM venue_waitlist WHERE status = 'reserved' AND reserved_until < NOW()")
                expired_reservations = cursor.fetchall()
                
                for res in expired_reservations:
                    # Mark expired
                    cursor.execute("UPDATE venue_waitlist SET status = 'expired' WHERE id = %s", (res['id'],))
                    
                    # Find the NEXT person in line for this same slot overlap
                    cursor.execute('''SELECT vw.id, u.email, u.username, v.name as venue_name, vw.start_time, vw.end_time
                                      FROM venue_waitlist vw
                                      JOIN users u ON vw.user_id = u.id
                                      JOIN venues v ON vw.venue_id = v.id
                                      WHERE vw.venue_id = %s AND vw.event_date = %s AND vw.status = 'waiting'
                                      AND (vw.start_time IS NULL OR vw.end_time IS NULL OR (vw.start_time < %s AND vw.end_time > %s))
                                      ORDER BY vw.created_at ASC
                                      LIMIT 1
                                   ''', (res['venue_id'], res['event_date'], res['end_time'], res['start_time']))
                    next_user = cursor.fetchone()
                    
                    if next_user:
                        # Reserve it for them
                        cursor.execute("UPDATE venue_waitlist SET status = 'reserved', reserved_until = DATE_ADD(NOW(), INTERVAL 24 HOUR) WHERE id = %s", (next_user['id'],))
                        
                        start_str = (str(next_user['start_time'])[:5] if next_user['start_time'] else "")
                        end_str = (str(next_user['end_time'])[:5] if next_user['end_time'] else "")
                        
                        # Generate link (we can't easily use url_for with _external outside request context without SERVER_NAME config, but we can try if it's set)
                        # Instead, since we don't have request context, we can just point them to the dashboard
                        send_email_notification(
                            next_user['email'],
                            "Venue Slot Reserved For You! (24 Hours)",
                            f"Dear {next_user['username']},\n\nGood news! The venue '{next_user['venue_name']}' is now available on {res['event_date']}. "
                            "Since the previous person did not claim it, we have locked this slot exclusively for you for the next 24 hours!\n\n"
                            f"Please log in and submit your event proposal immediately.\n\n"
                            "Note: If you do not submit your proposal within 24 hours, the reservation will expire and the slot will be passed to the next person."
                        )
                conn.commit()
        except Exception as e:
            print(f"Error checking waitlist expiries: {e}")
        finally:
            conn.close()
