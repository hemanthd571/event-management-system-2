from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.utils.decorators import role_required
from app.models import User, Role, Department
from app import db

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/users')
@login_required
@role_required('Admin')
def manage_users():
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@role_required('Admin')
def create_user():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role_id = request.form.get('role_id')
        department_id = request.form.get('department_id')

        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return redirect(url_for('admin.create_user'))

        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'danger')
            return redirect(url_for('admin.create_user'))

        new_user = User(
            username=username,
            email=email,
            role_id=role_id,
            department_id=department_id if department_id else None
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash('User created successfully.', 'success')
        return redirect(url_for('admin.manage_users'))

    roles = Role.query.all()
    departments = Department.query.all()
    return render_template('admin/create_user.html', roles=roles, departments=departments)

@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@role_required('Admin')
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.username == 'admin':
        flash('Cannot delete the master admin account.', 'danger')
        return redirect(url_for('admin.manage_users'))
        
    db.session.delete(user)
    db.session.commit()
    flash(f'User {user.username} deleted.', 'success')
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('Admin')
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role_id = request.form.get('role_id')
        department_id = request.form.get('department_id')

        # Check for unique constraints if username/email changed
        if username != user.username and User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return redirect(url_for('admin.edit_user', user_id=user.id))

        if email != user.email and User.query.filter_by(email=email).first():
            flash('Email already exists.', 'danger')
            return redirect(url_for('admin.edit_user', user_id=user.id))

        user.username = username
        user.email = email
        
        # Don't change admin role to prevent locking out the admin
        if user.username != 'admin':
            user.role_id = role_id
            
        user.department_id = department_id if department_id else None

        if password:  # Only change password if a new one is typed
            user.set_password(password)

        db.session.commit()
        flash(f'User {user.username} updated successfully.', 'success')
        return redirect(url_for('admin.manage_users'))

    roles = Role.query.all()
    departments = Department.query.all()
    return render_template('admin/edit_user.html', user=user, roles=roles, departments=departments)
