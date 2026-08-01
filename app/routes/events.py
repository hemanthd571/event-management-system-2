from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, send_from_directory, current_app, make_response, jsonify
from flask_login import login_required, current_user
from app.utils.decorators import role_required
from app.dal import get_db_connection, get_user_by_id, get_department
from app.models_raw import Event, Approval, EventComment
from datetime import datetime, date
import os
import pymysql
import io
import uuid
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from flask import send_file


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
            
            if event.venue_id:
                cursor.execute('SELECT * FROM venues WHERE id = %s', (event.venue_id,))
                venue_row = cursor.fetchone()
                if venue_row:
                    class DummyVenue: pass
                    v = DummyVenue()
                    v.name = venue_row.get('name')
                    v.capacity = venue_row.get('capacity')
                    event.venue_obj = v
            
            cursor.execute('SELECT * FROM approvals WHERE event_id = %s ORDER BY level', (event_id,))
            event.approvals = [Approval(**a) for a in cursor.fetchall()]
            
            return event
    finally:
        conn.close()

def send_email_notification(to_email, subject, body):
    from flask_mail import Message
    from app import mail
    from flask import current_app
    import threading

    app = current_app._get_current_object()

    def send_async_email(app, msg):
        with app.app_context():
            try:
                mail.send(msg)
            except Exception as e:
                print(f"Failed to send email to {to_email}: {e}")

    try:
        msg = Message(subject, recipients=[to_email], body=body)
        thread = threading.Thread(target=send_async_email, args=(app, msg))
        thread.start()
    except Exception as e:
        print(f"Failed to start email thread for {to_email}: {e}")

def add_notification(user_id, message, link):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('INSERT INTO notifications (user_id, message, link, is_read) VALUES (%s, %s, %s, 0)', (user_id, message, link))
        conn.commit()
    except Exception as e:
        print(f"Failed to add notification: {e}")
    finally:
        conn.close()

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
                                  AND (post_event_report_path IS NULL OR post_event_report_path = '' OR post_event_bill_path IS NULL OR post_event_bill_path = '')''', 
                               (current_user.id, date.today()))
                missing_events = cursor.fetchall()
                if missing_events:
                    flash(f"You cannot create a new event. You have a past event ('{missing_events[0]['title']}') with missing completion proofs (report or bill).", "danger")
                    return redirect(url_for('dashboard.index'))

        if request.method == 'POST':
            # Simplified for brevity - parse form, insert into DB, add approvals
            title = request.form.get('title')
            event_type = request.form.get('event_type')
            event_category = request.form.get('event_category')
            if event_category == 'Other':
                event_category = request.form.get('other_event_category')
            event_date = request.form.get('event_date')
            start_time = request.form.get('start_time')
            end_time = request.form.get('end_time')
            venue_id = request.form.get('venue_id')
            budget = request.form.get('budget')
            funding_source = request.form.get('funding_source')
            expected_participants = request.form.get('expected_participants')
            chief_guest = request.form.get('chief_guest')
            objectives = request.form.get('objectives')
            description = request.form.get('description')
            department_id = request.form.get('department_id')
            organizer_name = request.form.get('organizer_name')
            faculty_coordinator = request.form.get('faculty_coordinator')
            
            with conn.cursor() as cursor:
                # 1. Check for any approved University Level event on the entire date
                cursor.execute('''
                    SELECT title FROM events 
                    WHERE event_date = %s 
                    AND status = 'Approved' 
                    AND event_type = 'University Level'
                ''', (event_date,))
                uni_clash = cursor.fetchone()
                if uni_clash:
                    flash(f"Failed to submit: An approved University Level event ('{uni_clash['title']}') is scheduled on this date. No other events are allowed.", 'danger')
                    return redirect(url_for('events.create'))

                # 2. Venue clash check with 1-hour gap for Department Level
                if event_type == 'Department Level':
                    cursor.execute('''
                        SELECT title FROM events 
                        WHERE venue_id = %s 
                        AND event_date = %s 
                        AND status != 'Rejected'
                        AND SUBTIME(start_time, '01:00:00') < %s 
                        AND ADDTIME(end_time, '01:00:00') > %s
                    ''', (venue_id, event_date, end_time, start_time))
                else:
                    cursor.execute('''
                        SELECT title FROM events 
                        WHERE venue_id = %s 
                        AND event_date = %s 
                        AND status != 'Rejected'
                        AND start_time < %s 
                        AND end_time > %s
                    ''', (venue_id, event_date, end_time, start_time))
                    
                clash = cursor.fetchone()
                if clash:
                    if event_type == 'Department Level':
                        flash(f"Failed to submit: Department Level events require a 1-hour gap. There is a clash with '{clash['title']}'.", 'danger')
                    else:
                        flash(f"Failed to submit proposal: There is a venue clash with '{clash['title']}' at this time!", 'danger')
                    return redirect(url_for('events.create'))

                cursor.execute('SELECT MAX(id) as max_id FROM events')
                max_id_row = cursor.fetchone()
                max_id = max_id_row['max_id'] if max_id_row['max_id'] is not None else 0
                event_count = max_id + 1
                event_id_str = f"EVT-{datetime.now().year}-{event_count:03d}"
                
                cursor.execute('SELECT name FROM venues WHERE id = %s', (venue_id,))
                venue_row = cursor.fetchone()
                venue_name = venue_row['name'] if venue_row else None
                
                cursor.execute('''INSERT INTO events (
                                      event_id, title, event_type, event_category, organizer_name, 
                                      faculty_coordinator, event_date, start_time, end_time, venue_id, venue,
                                      budget, funding_source, expected_participants, chief_guest, 
                                      objectives, description, department_id, organizer_id, status
                                  ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                               (
                                   event_id_str, title, event_type, event_category, organizer_name, 
                                   faculty_coordinator, event_date, start_time, end_time, venue_id, venue_name,
                                   budget, funding_source, expected_participants, chief_guest, 
                                   objectives, description, department_id, current_user.id, 'Pending'
                               ))
                
                new_event_id = cursor.lastrowid
                
                # Add default approvals
                if event_type == 'Department Level':
                    levels = [
                        (1, 'Faculty'),
                        (2, 'HOD')
                    ]
                else:
                    levels = [
                        (1, 'Faculty'),
                        (2, 'HOD'),
                        (3, 'Director'),
                        (4, 'Pro VC'),
                        (5, 'VC')
                    ]
                for level, role in levels:
                    cursor.execute('INSERT INTO approvals (event_id, required_role, level, status) VALUES (%s, %s, %s, %s)', 
                                   (new_event_id, role, level, 'Pending'))
                                   
                conn.commit()
            
            flash('Event proposal submitted successfully.', 'success')
            try:
                from app.routes.events import send_email_notification, add_notification
                send_email_notification(
                    current_user.email,
                    "Event Proposal Submitted",
                    f"Your event proposal '{title}' has been successfully submitted and is pending approval."
                )
                add_notification(current_user.id, f"Your event proposal '{title}' has been submitted.", f"/events/{new_event_id}")
                
                # Notify next approver
                conn_inner = get_db_connection()
                try:
                    with conn_inner.cursor() as cursor_inner:
                        cursor_inner.execute('SELECT required_role FROM approvals WHERE event_id=%s AND status=%s ORDER BY level ASC LIMIT 1', (new_event_id, 'Pending'))
                        next_app = cursor_inner.fetchone()
                        if next_app:
                            next_role = next_app['required_role']
                            if next_role in ['Faculty', 'HOD']:
                                cursor_inner.execute('SELECT id, email FROM users WHERE role=%s AND department_id=%s', (next_role, department_id))
                            else:
                                cursor_inner.execute('SELECT id, email FROM users WHERE role=%s', (next_role,))
                            
                            next_users = cursor_inner.fetchall()
                            for u in next_users:
                                if u['email']:
                                    send_email_notification(
                                        u['email'],
                                        "Event Proposal Needs Approval",
                                        f"An event proposal '{title}' requires your approval as {next_role}."
                                    )
                                add_notification(u['id'], f"Event '{title}' requires your approval.", f"/events/{new_event_id}")
                finally:
                    conn_inner.close()
            except Exception as e:
                print(f"Failed to send email/notification: {e}")
            return redirect(url_for('dashboard.index'))
            
        with conn.cursor() as cursor:
            cursor.execute('SELECT * FROM departments')
            from app.models_raw import Department
            departments = [Department(**d) for d in cursor.fetchall()]
            
            cursor.execute('SELECT * FROM venues')
            venues = cursor.fetchall()
            
    finally:
        conn.close()
        
    return render_template('events/create.html', departments=departments, venues=venues)

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
                
            if event.event_type == 'Department Level':
                cursor.execute('''
                    SELECT title FROM events 
                    WHERE venue_id = %s 
                    AND event_date = %s 
                    AND id != %s 
                    AND status != 'Rejected'
                    AND SUBTIME(start_time, '01:00:00') < %s 
                    AND ADDTIME(end_time, '01:00:00') > %s
                ''', (event.venue_id, event.event_date, event.id, event.end_time, event.start_time))
            else:
                cursor.execute('''
                    SELECT title FROM events 
                    WHERE venue_id = %s 
                    AND event_date = %s 
                    AND id != %s 
                    AND status != 'Rejected'
                    AND start_time < %s 
                    AND end_time > %s
                ''', (event.venue_id, event.event_date, event.id, event.end_time, event.start_time))
            clashing_events = cursor.fetchall()
            
            cursor.execute('SELECT * FROM event_registrations WHERE event_id = %s AND user_id = %s', (event_id, current_user.id))
            user_registration = cursor.fetchone()
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
                           chat_messages=chats, clashing_events=clashing_events,
                           user_registration=user_registration)

@events_bp.route('/<int:event_id>/approve', methods=['POST'])
@login_required
def approve(event_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            action = request.form.get('action')
            comments = request.form.get('comments')
            cursor.execute('UPDATE approvals SET status=%s, comments=%s WHERE event_id=%s AND required_role=%s AND status=%s',
                           (action, comments, event_id, current_user.role, 'Pending'))
            
            if action == 'Approved':
                # Check if all approvals are done
                cursor.execute('SELECT COUNT(*) as c FROM approvals WHERE event_id=%s AND status!=%s', (event_id, 'Approved'))
                remaining = cursor.fetchone()['c']
                if remaining == 0:
                    cursor.execute('UPDATE events SET status=%s WHERE id=%s', ('Approved', event_id))
            elif action == 'Rejected':
                cursor.execute('UPDATE events SET status=%s WHERE id=%s', ('Rejected', event_id))
                
            conn.commit()
    finally:
        conn.close()
    
    flash('Action recorded.', 'success')
    try:
        from app.routes.events import send_email_notification, add_notification
        event = fetch_event(event_id)
        if event:
            if action == 'Rejected':
                if event.organizer:
                    add_notification(event.organizer.id, f"Your event proposal '{event.title}' has been rejected by {current_user.role}.", f"/events/{event.id}")
                    if event.organizer.email:
                        send_email_notification(
                            event.organizer.email,
                            f"Event Proposal Rejected",
                            f"Your event proposal '{event.title}' has been rejected by {current_user.role}."
                        )
            elif action == 'Approved':
                # Notify organizer if fully approved
                if event.status == 'Approved':
                    if event.organizer:
                        add_notification(event.organizer.id, f"Your event proposal '{event.title}' has been fully approved!", f"/events/{event.id}")
                        if event.organizer.email:
                            send_email_notification(
                                event.organizer.email,
                                f"Event Proposal Approved",
                                f"Your event proposal '{event.title}' has been fully approved!"
                            )
                else:
                    # Notify next approver
                    conn = get_db_connection()
                    try:
                        with conn.cursor() as cursor:
                            cursor.execute('SELECT required_role FROM approvals WHERE event_id=%s AND status=%s ORDER BY level ASC LIMIT 1', (event_id, 'Pending'))
                            next_app = cursor.fetchone()
                            if next_app:
                                next_role = next_app['required_role']
                                if next_role in ['Faculty', 'HOD']:
                                    cursor.execute('SELECT id, email FROM users WHERE role=%s AND department_id=%s', (next_role, event.department_id))
                                else:
                                    cursor.execute('SELECT id, email FROM users WHERE role=%s', (next_role,))
                                
                                next_users = cursor.fetchall()
                                for u in next_users:
                                    if u['email']:
                                        send_email_notification(
                                            u['email'],
                                            "Event Proposal Needs Approval",
                                            f"An event proposal '{event.title}' requires your approval as {next_role}."
                                        )
                                    add_notification(u['id'], f"Event '{event.title}' requires your approval.", f"/events/{event.id}")
                    finally:
                        conn.close()
    except Exception as e:
        print(f"Failed to send email/notification: {e}")
        
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
import os
from werkzeug.utils import secure_filename
from flask import current_app, send_from_directory

@events_bp.route('/uploads/<filename>')
@login_required
def download_uploaded_file(filename):
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    return send_from_directory(upload_folder, filename, as_attachment=True)

@events_bp.route('/<int:event_id>/upload_report', methods=['POST'])
@login_required
def upload_report(event_id):
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)

    report_files = request.files.getlist('report_files')
    bill_file = request.files.get('post_event_bill')
    
    report_paths = []
    if report_files:
        for file in report_files:
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                file_path = os.path.join(upload_folder, f"{event_id}_report_{filename}")
                file.save(file_path)
                report_paths.append(f"{event_id}_report_{filename}")
                
    bill_path = None
    if bill_file and bill_file.filename != '':
        filename = secure_filename(bill_file.filename)
        file_path = os.path.join(upload_folder, f"{event_id}_bill_{filename}")
        bill_file.save(file_path)
        bill_path = f"{event_id}_bill_{filename}"
        
    if not report_paths and not bill_path:
        flash('No files selected', 'danger')
        return redirect(url_for('events.view', event_id=event_id))
        
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            if report_paths:
                cursor.execute('UPDATE events SET post_event_report_path = %s WHERE id = %s', 
                               (",".join(report_paths), event_id))
            if bill_path:
                cursor.execute('UPDATE events SET post_event_bill_path = %s WHERE id = %s', 
                               (bill_path, event_id))
        conn.commit()
        flash('Files uploaded successfully.', 'success')
    except Exception as e:
        flash(f'Database error: {e}', 'danger')
    finally:
        conn.close()
        
    return redirect(url_for('events.view', event_id=event_id))

@events_bp.route('/download_pdf/<int:event_id>')
def download_pdf(event_id):
    event = fetch_event(event_id)
    if not event:
        abort(404)
        
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(300, 700, "Event Certificate")
    
    c.setFont("Helvetica", 16)
    c.drawCentredString(300, 600, "This is to certify that the event")
    
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(300, 550, event.title)
    
    c.setFont("Helvetica", 16)
    c.drawCentredString(300, 500, "was successfully approved and organized.")
    
    c.setFont("Helvetica", 12)
    c.drawCentredString(300, 400, f"Date: {event.event_date.strftime('%Y-%m-%d') if event.event_date else 'N/A'}")
    c.drawCentredString(300, 380, f"Organizer: {event.organizer_name}")
    
    c.showPage()
    c.save()
    
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"certificate_{event_id}.pdf", mimetype='application/pdf')

@events_bp.route('/<int:event_id>/register', methods=['POST'])
@login_required
def register_event(event_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Check if event exists and is Approved
            cursor.execute('SELECT status FROM events WHERE id = %s', (event_id,))
            ev = cursor.fetchone()
            if not ev or ev['status'] != 'Approved':
                flash('Cannot register for this event.', 'danger')
                return redirect(url_for('events.view', event_id=event_id))
            
            # Check if already registered
            cursor.execute('SELECT id FROM event_registrations WHERE event_id = %s AND user_id = %s', (event_id, current_user.id))
            if cursor.fetchone():
                flash('You are already registered for this event.', 'info')
                return redirect(url_for('events.view', event_id=event_id))
            
            qr_token = str(uuid.uuid4())
            cursor.execute('''
                INSERT INTO event_registrations (event_id, user_id, qr_token) 
                VALUES (%s, %s, %s)
            ''', (event_id, current_user.id, qr_token))
            conn.commit()
            flash('Successfully registered! Your QR code ticket is ready.', 'success')
    except Exception as e:
        flash(f'Error registering: {str(e)}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('events.view', event_id=event_id))

@events_bp.route('/<int:event_id>/scan/<qr_token>')
@login_required
def scan_ticket(event_id, qr_token):
    # Only Admin or Organizer can scan
    event = fetch_event(event_id)
    if not event:
        abort(404)
        
    if current_user.id != event.organizer_id and not current_user.is_admin():
        abort(403)
        
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Find the registration
            cursor.execute('SELECT r.id, r.attended, u.username FROM event_registrations r JOIN users u ON r.user_id = u.id WHERE r.event_id = %s AND r.qr_token = %s', (event_id, qr_token))
            reg = cursor.fetchone()
            if not reg:
                flash('Invalid or expired QR code.', 'danger')
                return redirect(url_for('events.view', event_id=event_id))
            
            if reg['attended']:
                flash(f"Student {reg['username']} has already checked in.", 'info')
            else:
                cursor.execute('UPDATE event_registrations SET attended = TRUE WHERE id = %s', (reg['id'],))
                conn.commit()
                flash(f"Success! Student {reg['username']} marked as Present.", 'success')
    finally:
        conn.close()
        
    return render_template('events/scan.html', event=event)

@events_bp.route('/<int:event_id>/live_stats', methods=['GET'])
@login_required
def get_event_stats(event_id):
    event = fetch_event(event_id)
    if not event:
        return jsonify({'error': 'Event not found'}), 404
        
    if current_user.id != event.organizer_id and not current_user.is_admin() and current_user.role not in ['Director', 'VC', 'Pro VC', 'HOD', 'Faculty']:
        return jsonify({'error': 'Forbidden'}), 403
        
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('SELECT COUNT(*) as total FROM event_registrations WHERE event_id = %s', (event_id,))
            total = cursor.fetchone()['total']
            
            cursor.execute('SELECT COUNT(*) as attended FROM event_registrations WHERE event_id = %s AND attended = TRUE', (event_id,))
            attended = cursor.fetchone()['attended']
            
            return jsonify({
                'total_registered': total,
                'total_attended': attended
            })
    finally:
        conn.close()

@events_bp.route('/<int:event_id>/feedback', methods=['POST'])
@login_required
def submit_feedback(event_id):
    rating = request.form.get('rating')
    comments = request.form.get('comments')
    
    if not rating:
        flash('Rating is required.', 'danger')
        return redirect(url_for('events.view', event_id=event_id))
        
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('SELECT id, attended, feedback_submitted FROM event_registrations WHERE event_id = %s AND user_id = %s', (event_id, current_user.id))
            reg = cursor.fetchone()
            
            if not reg:
                flash('You must register for this event first.', 'danger')
            elif not reg['attended']:
                flash('You must attend the event and be checked in to leave feedback.', 'danger')
            elif reg['feedback_submitted']:
                flash('You have already submitted feedback for this event.', 'info')
            else:
                cursor.execute('''
                    UPDATE event_registrations 
                    SET rating = %s, feedback_text = %s, feedback_submitted = TRUE 
                    WHERE id = %s
                ''', (rating, comments, reg['id']))
                conn.commit()
                flash('Thank you for your feedback!', 'success')
    finally:
        conn.close()
        
    return redirect(url_for('events.view', event_id=event_id))
