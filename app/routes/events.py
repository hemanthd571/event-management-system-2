from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, send_from_directory, current_app, make_response
from flask_login import login_required, current_user
from app.utils.decorators import role_required
from app.dal import get_db_connection, get_user_by_id, get_department
from app.models_raw import Event, Approval, EventComment
from datetime import datetime, date
import os
import pymysql

events_bp = Blueprint('events', __name__, url_prefix='/events')

def fetch_event(event_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('SELECT * FROM events WHERE id = %s', (event_id,))
            row = cursor.fetchone()
            if not row: return None
            event = Event(**row)
            
            event.organizer = get_user_by_id(event.organizer_id)
            event.department = get_department(event.department_id)
            
            cursor.execute('SELECT * FROM approvals WHERE event_id = %s ORDER BY level', (event_id,))
            event.approvals = [Approval(**a) for a in cursor.fetchall()]
            
            return event
    finally:
        conn.close()

def send_email_notification(to_email, subject, body):
    from flask_mail import Message
    from app import mail
    try:
        msg = Message(subject, recipients=[to_email], body=body)
        mail.send(msg)
    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")

@events_bp.route('/')
@login_required
def index():
    return redirect(url_for('dashboard.index'))

@events_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    conn = get_db_connection()
    try:
        if current_user.role not in ['Admin', 'VC', 'Pro VC']:
            with conn.cursor() as cursor:
                cursor.execute('''SELECT * FROM events 
                                  WHERE organizer_id = %s AND status = 'Approved' 
                                  AND event_date < %s 
                                  AND (post_event_report_path IS NULL OR post_event_report_path = '')''', 
                               (current_user.id, date.today()))
                missing_events = cursor.fetchall()
                if missing_events:
                    flash(f"You cannot create a new event. You have a past event ('{missing_events[0]['title']}') with missing completion proof.", "danger")
                    return redirect(url_for('dashboard.index'))

        if request.method == 'POST':
            # Simplified for brevity - parse form, insert into DB, add approvals
            title = request.form.get('title')
            event_type = request.form.get('event_type')
            event_date = request.form.get('event_date')
            
            with conn.cursor() as cursor:
                cursor.execute('SELECT COUNT(*) as c FROM events')
                event_count = cursor.fetchone()['c'] + 1
                event_id_str = f"EVT-{datetime.now().year}-{event_count:03d}"
                
                cursor.execute('''INSERT INTO events (event_id, title, event_type, organizer_name, faculty_coordinator, 
                                  event_date, department_id, organizer_id) 
                                  VALUES (%s, %s, %s, %s, %s, %s, %s, %s)''',
                               (event_id_str, title, event_type, request.form.get('organizer_name'), 
                                request.form.get('faculty_coordinator'), event_date, 
                                current_user.department_id, current_user.id))
                
                new_event_id = cursor.lastrowid
                
                # Add default approvals
                levels = [
                    (1, 'Faculty'),
                    (2, 'HOD'),
                    (3, 'Director'),
                    (4, 'Pro VC'),
                    (5, 'VC')
                ]
                for level, role in levels:
                    cursor.execute('INSERT INTO approvals (event_id, required_role, level) VALUES (%s, %s, %s)', 
                                   (new_event_id, role, level))
                                   
                conn.commit()
            
            flash('Event proposal submitted successfully.', 'success')
            return redirect(url_for('dashboard.index'))
            
    finally:
        conn.close()
        
    return render_template('events/create.html')

@events_bp.route('/<int:event_id>')
@login_required
def view(event_id):
    event = fetch_event(event_id)
    if not event:
        abort(404)
        
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('''SELECT ec.*, u.username as user_name 
                              FROM event_comments ec 
                              JOIN users u ON ec.user_id = u.id 
                              WHERE event_id = %s ORDER BY ec.created_at ASC''', (event_id,))
            chat_messages = cursor.fetchall()
            
            # MOCK objects for chat messages
            class ChatMsg: pass
            chats = []
            for m in chat_messages:
                c = ChatMsg()
                c.message = m['message']
                c.created_at = m['created_at']
                u = ChatMsg()
                u.username = m['user_name']
                u.id = m['user_id']
                c.user = u
                chats.append(c)
                
            clashing_events = []
    finally:
        conn.close()

    can_approve = False
    current_approval = None
    if current_user.role not in ['Student/Organizer', 'Admin']:
        for app in event.approvals:
            if app.status in ['Pending', 'Returned for Correction']:
                if app.required_role == current_user.role:
                    can_approve = True
                    current_approval = app
                break

    return render_template('events/view.html', event=event, approvals=event.approvals, 
                           can_approve=can_approve, current_approval=current_approval, 
                           chat_messages=chats, clashing_events=clashing_events)

@events_bp.route('/<int:event_id>/approve', methods=['POST'])
@login_required
def approve(event_id):
    # Simplified approval logic for brevity
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            action = request.form.get('action')
            comments = request.form.get('comments')
            cursor.execute('UPDATE approvals SET status=%s, comments=%s WHERE event_id=%s AND required_role=%s AND status=%s',
                           (action, comments, event_id, current_user.role, 'Pending'))
            
            if action == 'Approved':
                cursor.execute('UPDATE events SET status=%s WHERE id=%s', ('Approved', event_id))
            elif action == 'Rejected':
                cursor.execute('UPDATE events SET status=%s WHERE id=%s', ('Rejected', event_id))
                
            conn.commit()
    finally:
        conn.close()
    
    flash('Action recorded.', 'success')
    return redirect(url_for('events.view', event_id=event_id))

@events_bp.route('/<int:event_id>/chat', methods=['POST'])
@login_required
def post_chat(event_id):
    message_text = request.form.get('message')
    if message_text and message_text.strip():
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute('INSERT INTO event_comments (message, event_id, user_id) VALUES (%s, %s, %s)',
                               (message_text.strip(), event_id, current_user.id))
                conn.commit()
        finally:
            conn.close()
        flash('Message posted.', 'success')
    return redirect(url_for('events.view', event_id=event_id))

@events_bp.route('/<int:event_id>/delete', methods=['POST'])
@login_required
def delete_event(event_id):
    if not current_user.is_admin():
        flash('Permission denied.', 'danger')
        return redirect(url_for('dashboard.index'))
        
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('DELETE FROM event_comments WHERE event_id=%s', (event_id,))
            cursor.execute('DELETE FROM approvals WHERE event_id=%s', (event_id,))
            cursor.execute('DELETE FROM events WHERE id=%s', (event_id,))
            conn.commit()
    finally:
        conn.close()
    flash('Event deleted.', 'success')
    return redirect(url_for('dashboard.index'))
