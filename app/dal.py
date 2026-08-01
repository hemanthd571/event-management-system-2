from app.db_manager import get_db_connection
from app.models_raw import User, Department, Event, Approval, Notification, EventComment
from werkzeug.security import check_password_hash, generate_password_hash
import datetime
import datetime


def get_users_by_role(role, department_id=None):
    """Fetch users by role, handling both 'role' column and 'roles' table schemas."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            try:
                # Try the new schema (with roles table)
                if department_id:
                    cursor.execute('''
                        SELECT u.id, u.email 
                        FROM users u 
                        JOIN roles r ON u.role_id = r.id 
                        WHERE r.name = %s AND u.department_id = %s
                    ''', (role, department_id))
                else:
                    cursor.execute('''
                        SELECT u.id, u.email 
                        FROM users u 
                        JOIN roles r ON u.role_id = r.id 
                        WHERE r.name = %s
                    ''', (role,))
                users = cursor.fetchall()
                if users:
                    return users
                # If it didn't throw an error but returned empty, it means the roles table exists 
                # but no users match. However, just in case the role column is ALSO used, fallback.
            except Exception:
                pass
            
            # Fallback to old schema (role column in users table)
            if department_id:
                cursor.execute('SELECT id, email FROM users WHERE role = %s AND department_id = %s', (role, department_id))
            else:
                cursor.execute('SELECT id, email FROM users WHERE role = %s', (role,))
            return cursor.fetchall()
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
            try:
                cursor.execute('''
                    SELECT u.*, r.name as role 
                    FROM users u 
                    LEFT JOIN roles r ON u.role_id = r.id 
                    WHERE u.id = %s
                ''', (user_id,))
                row = cursor.fetchone()
            except Exception:
                # Fallback if roles table or role_id column doesn't exist
                cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
                row = cursor.fetchone()

            if not row: return None
            
            user = User(**row)
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
            cursor.execute('''
                SELECT u.*, r.name as role 
                FROM users u 
                LEFT JOIN roles r ON u.role_id = r.id 
                WHERE u.email = %s
            ''', (email,))
            row = cursor.fetchone()
            if not row: return None
            
            user = User(**row)
            user.department = get_department(user.department_id)
            
            user.get_id = lambda: str(user.id)
            
            # Helper for auth
            def check_password(password):
                return check_password_hash(user.password_hash, password)
            user.check_password = check_password
            
            return user
    finally:
        conn.close()
