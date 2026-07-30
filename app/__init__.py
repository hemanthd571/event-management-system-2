import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from config import Config

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
mail = Mail()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
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
    
    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Automatically apply database migrations on startup
    with app.app_context():
        from flask_migrate import upgrade
        try:
            upgrade()
        except Exception as e:
            print(f"Auto-migration failed: {e}")

    # Start the background scheduler for automated reminders
    if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        from apscheduler.schedulers.background import BackgroundScheduler
        import atexit
        
        scheduler = BackgroundScheduler()
        scheduler.add_job(func=check_and_send_reminders, args=[app], trigger="interval", hours=1)
        scheduler.start()
        atexit.register(lambda: scheduler.shutdown())

    return app

def check_and_send_reminders(app):
    with app.app_context():
        from app.models import Event, User
        from app import db
        from datetime import date, timedelta
        from app.routes.events import send_email_notification
        
        target_date = date.today() - timedelta(days=3)
        
        events_to_remind = Event.query.filter(
            Event.status == 'Approved',
            Event.event_date <= target_date,
            Event.reminder_sent == False
        ).all()
        
        for event in events_to_remind:
            if not event.post_event_report_path:
                organizer = User.query.get(event.organizer_id)
                if organizer:
                    # Mark as sent first to prevent race conditions
                    event.reminder_sent = True
                    db.session.commit()
                    
                    send_email_notification(
                        organizer.email,
                        "Action Required: Missing Event Proof",
                        f"Dear {organizer.username},\n\nPlease upload your event proof immediately for the event '{event.title}' which occurred on {event.event_date}."
                    )
