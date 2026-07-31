from flask_login import UserMixin
from app.db_manager import get_db_connection


class Department:
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.name = kwargs.get('name')
        self.code = kwargs.get('code')

class User(UserMixin):
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.username = kwargs.get('username')
        self.email = kwargs.get('email')
        self.password_hash = kwargs.get('password_hash')
        self._is_active = kwargs.get('is_active', True)

        self.department_id = kwargs.get('department_id')
        
        # Relations
        self.role = kwargs.get('role')
        self.department = kwargs.get('department')
        
    def is_admin(self):
        return self.role == 'Admin'

from datetime import time, timedelta

class Event:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if isinstance(value, timedelta):
                s = int(value.total_seconds())
                value = time(hour=s//3600, minute=(s%3600)//60, second=s%60)
            setattr(self, key, value)
            
        # Relations
        self.organizer = kwargs.get('organizer')
        self.department = kwargs.get('department')
        self.approvals = kwargs.get('approvals', [])

class Approval:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        self.user = kwargs.get('user')

class Notification:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

class EventComment:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        self.user = kwargs.get('user')
