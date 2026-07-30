from datetime import datetime
from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    users = db.relationship('User', backref='role', lazy=True)

class Department(db.Model):
    __tablename__ = 'departments'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)
    code = db.Column(db.String(10), unique=True, nullable=False)
    users = db.relationship('User', backref='department', lazy=True)
    events = db.relationship('Event', backref='department', lazy=True)

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    def is_admin(self):
        return self.role.name == 'Admin'

class Venue(db.Model):
    __tablename__ = 'venues'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), unique=True, nullable=False)
    capacity = db.Column(db.Integer)
    type = db.Column(db.String(100))
    events = db.relationship('Event', backref='venue_obj', lazy=True)

class Event(db.Model):
    __tablename__ = 'events'
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.String(20), unique=True, nullable=False) # e.g. EVT-2023-001
    title = db.Column(db.String(200), nullable=False)
    event_type = db.Column(db.String(50), nullable=False) # 'University Level' or 'Department Level'
    
    organizer_name = db.Column(db.String(100), nullable=False)
    faculty_coordinator = db.Column(db.String(100), nullable=False)
    contact_number = db.Column(db.String(20))
    email = db.Column(db.String(120))
    
    event_date = db.Column(db.Date, nullable=False)
    event_time = db.Column(db.String(20)) # Legacy
    start_time = db.Column(db.Time)
    end_time = db.Column(db.Time)
    venue = db.Column(db.String(200)) # Legacy
    venue_id = db.Column(db.Integer, db.ForeignKey('venues.id'), nullable=True)
    budget = db.Column(db.Float, default=0.0)
    funding_source = db.Column(db.String(100))
    expected_participants = db.Column(db.Integer)
    chief_guest = db.Column(db.String(200))
    
    objectives = db.Column(db.Text)
    description = db.Column(db.Text)
    schedule = db.Column(db.Text)
    required_resources = db.Column(db.Text)
    
    proposal_pdf_path = db.Column(db.Text(16777215))
    budget_pdf_path = db.Column(db.Text(16777215))
    supporting_docs_path = db.Column(db.Text(16777215))
    post_event_report_path = db.Column(db.Text(16777215))
    reminder_sent = db.Column(db.Boolean, default=False)
    
    status = db.Column(db.String(50), default='Submitted') # Submitted, Pending Faculty Approval, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    organizer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    approvals = db.relationship('Approval', backref='event', lazy=True, cascade="all, delete-orphan")
    
class Approval(db.Model):
    __tablename__ = 'approvals'
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(50), nullable=False) # Pending, Approved, Rejected, Returned for Correction
    comments = db.Column(db.Text)
    action_date = db.Column(db.DateTime)
    
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    approver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True) # The actual person who approved
    required_role = db.Column(db.String(64), nullable=False) # Which role is needed for this stage
    level = db.Column(db.Integer, nullable=False) # Order of approval (1: Faculty, 2: HOD, 3: Director, 4: Pro VC, 5: VC)
    
class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(255), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    link = db.Column(db.String(255))
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

class EventComment(db.Model):
    __tablename__ = 'event_comments'
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    user = db.relationship('User', backref='event_comments', lazy=True)
    event = db.relationship('Event', backref='chat_messages', lazy=True)
