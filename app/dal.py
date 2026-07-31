from app.db_manager import get_db_connection
from app.models_raw import User, Role, Department, Event, Approval, Notification, EventComment
from werkzeug.security import check_password_hash, generate_password_hash
import datetime

def get_role(role_id):
    if not role_id: return None
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('SELECT * FROM roles WHERE id = %s', (role_id,))
            row = cursor.fetchone()
            if row: return Role(**row)
            return None
    finally:
        conn.close()

def get_department(dept_id):
    if not dept_id: return None
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('SELECT * FROM departments WHERE id = %s', (dept_id,))
            row = cursor.fetchone()
            if row: return Department(**row)
            return None
    finally:
        conn.close()

def get_user_by_id(user_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
            row = cursor.fetchone()
            if not row: return None
            
            user = User(**row)
            user.role = get_role(user.role_id)
            user.department = get_department(user.department_id)
            
            # Flask login requires id as string
            user.get_id = lambda: str(user.id)
            return user
    finally:
        conn.close()

def get_user_by_email(email):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
            row = cursor.fetchone()
            if not row: return None
            
            user = User(**row)
            user.role = get_role(user.role_id)
            user.department = get_department(user.department_id)
            
            user.get_id = lambda: str(user.id)
            
            # Helper for auth
            def check_password(password):
                return check_password_hash(user.password_hash, password)
            user.check_password = check_password
            
            return user
    finally:
        conn.close()
