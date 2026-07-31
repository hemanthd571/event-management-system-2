from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from app.dal import get_user_by_id, get_db_connection
from werkzeug.security import check_password_hash
from app.models_raw import User
from app import login_manager

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@login_manager.user_loader
def load_user(user_id):
    return get_user_by_id(int(user_id))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
                row = cursor.fetchone()
                
                if row and check_password_hash(row['password_hash'], password):
                    user = get_user_by_id(row['id'])
                    login_user(user)
                    return redirect(url_for('dashboard.index'))
                flash('Invalid username or password', 'danger')
        finally:
            conn.close()
            
    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
