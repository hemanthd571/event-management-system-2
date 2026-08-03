from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required
from app.utils.decorators import role_required
from app.dal import get_db_connection, get_user_by_id, get_user_by_email, get_department
from app.models_raw import User, Department
from werkzeug.security import generate_password_hash
import pymysql

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/users')
@login_required
@role_required('Admin')
def manage_users():
    conn = get_db_connection()
    users = []
    try:
        with conn.cursor() as cursor:
            cursor.execute('''
                SELECT * 
                FROM users 
            ''')
            for row in cursor.fetchall():
                user = User(**row)
                user.department = get_department(user.department_id)
                users.append(user)
    finally:
        conn.close()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@role_required('Admin')
def create_user():
    conn = get_db_connection()
    try:
        if request.method == 'POST':
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            role = request.form.get('role')
            department_id = request.form.get('department_id')

            with conn.cursor() as cursor:
                cursor.execute('SELECT id FROM users WHERE username = %s', (username,))
                if cursor.fetchone():
                    flash('Username already exists.', 'danger')
                    return redirect(url_for('admin.create_user'))

                cursor.execute('SELECT id FROM users WHERE email = %s', (email,))
                if cursor.fetchone():
                    flash('Email already exists.', 'danger')
                    return redirect(url_for('admin.create_user'))

                cursor.execute(
                    'INSERT INTO users (username, email, password_hash, role, department_id) VALUES (%s, %s, %s, %s, %s)',
                    (username, email, generate_password_hash(password), role, department_id if department_id else None)
                )
                conn.commit()
                flash('User created successfully.', 'success')
                return redirect(url_for('admin.manage_users'))

        roles = ['Admin', 'Student/Organizer', 'Faculty', 'HOD', 'Director', 'Pro VC', 'VC']
        departments = []
        with conn.cursor() as cursor:
            cursor.execute('SELECT * FROM departments')
            departments = [Department(**d) for d in cursor.fetchall()]
            
        return render_template('admin/create_user.html', roles=roles, departments=departments)
    finally:
        conn.close()

@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@role_required('Admin')
def delete_user(user_id):
    user = get_user_by_id(user_id)
    if not user:
        abort(404)
        
    if user.username == 'admin':
        flash('Cannot delete the master admin account.', 'danger')
        return redirect(url_for('admin.manage_users'))
        
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('DELETE FROM users WHERE id = %s', (user_id,))
            conn.commit()
            flash(f'User {user.username} deleted.', 'success')
    except pymysql.err.IntegrityError:
        conn.rollback()
        flash(f'Cannot delete user {user.username} because they have associated events or records.', 'danger')
    finally:
        conn.close()
        
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('Admin')
def edit_user(user_id):
    user = get_user_by_id(user_id)
    if not user:
        abort(404)
        
    conn = get_db_connection()
    try:
        if request.method == 'POST':
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            role = request.form.get('role')
            department_id = request.form.get('department_id')

            with conn.cursor() as cursor:
                if username != user.username:
                    cursor.execute('SELECT id FROM users WHERE username = %s', (username,))
                    if cursor.fetchone():
                        flash('Username already exists.', 'danger')
                        return redirect(url_for('admin.edit_user', user_id=user.id))

                if email != user.email:
                    cursor.execute('SELECT id FROM users WHERE email = %s', (email,))
                    if cursor.fetchone():
                        flash('Email already exists.', 'danger')
                        return redirect(url_for('admin.edit_user', user_id=user.id))
                
                # Check admin override
                final_role = user.role if user.username == 'admin' else role
                
                if password:
                    pwd_hash = generate_password_hash(password)
                    cursor.execute('''UPDATE users SET username=%s, email=%s, role=%s, department_id=%s, password_hash=%s WHERE id=%s''',
                                   (username, email, final_role, department_id if department_id else None, pwd_hash, user_id))
                else:
                    cursor.execute('''UPDATE users SET username=%s, email=%s, role=%s, department_id=%s WHERE id=%s''',
                                   (username, email, final_role, department_id if department_id else None, user_id))
                
                conn.commit()
                flash(f'User {username} updated successfully.', 'success')
                return redirect(url_for('admin.manage_users'))

        roles = ['Admin', 'Student/Organizer', 'Faculty', 'HOD', 'Director', 'Pro VC', 'VC']
        departments = []
        with conn.cursor() as cursor:
            cursor.execute('SELECT * FROM departments')
            departments = [Department(**d) for d in cursor.fetchall()]
            
        return render_template('admin/edit_user.html', user=user, roles=roles, departments=departments)
    finally:
        conn.close()
