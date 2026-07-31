import re

with open('d:/project3/app/models.py', 'r') as f:
    content = f.read()

# Remove db.ForeignKey(...)
content = re.sub(r',\s*db\.ForeignKey\([^)]+\)', '', content)

# Add import foreign at the top
content = content.replace('from app import db, login_manager', 'from app import db, login_manager\nfrom sqlalchemy.orm import foreign')

# Fix relationships
content = content.replace(
    "users = db.relationship('User', backref='role', lazy=True)",
    "users = db.relationship('User', backref='role', lazy=True, primaryjoin='Role.id == foreign(User.role_id)')"
)

content = content.replace(
    "users = db.relationship('User', backref='department', lazy=True)",
    "users = db.relationship('User', backref='department', lazy=True, primaryjoin='Department.id == foreign(User.department_id)')"
)

content = content.replace(
    "events = db.relationship('Event', backref='department', lazy=True)",
    "events = db.relationship('Event', backref='department', lazy=True, primaryjoin='Department.id == foreign(Event.department_id)')"
)

content = content.replace(
    "events = db.relationship('Event', backref='venue_obj', lazy=True)",
    "events = db.relationship('Event', backref='venue_obj', lazy=True, primaryjoin='Venue.id == foreign(Event.venue_id)')"
)

content = content.replace(
    "approvals = db.relationship('Approval', backref='event', lazy=True, cascade=\"all, delete-orphan\")",
    "approvals = db.relationship('Approval', backref='event', lazy=True, cascade=\"all, delete-orphan\", primaryjoin='Event.id == foreign(Approval.event_id)')"
)

content = content.replace(
    "user = db.relationship('User', backref='event_comments', lazy=True)",
    "user = db.relationship('User', backref='event_comments', lazy=True, primaryjoin='User.id == foreign(EventComment.user_id)')"
)

content = content.replace(
    "event = db.relationship('Event', backref='chat_messages', lazy=True)",
    "event = db.relationship('Event', backref='chat_messages', lazy=True, primaryjoin='Event.id == foreign(EventComment.event_id)')"
)

with open('d:/project3/app/models.py', 'w') as f:
    f.write(content)
