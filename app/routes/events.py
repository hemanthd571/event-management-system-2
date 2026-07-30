import os
import uuid
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from app.models import Event, Approval, Notification, EventComment
from app import db
from werkzeug.utils import secure_filename
from app.utils.pdf_report import generate_approval_pdf, generate_post_event_pdf
from flask import make_response, send_from_directory
from flask_mail import Message
from app import mail
from threading import Thread
events_bp = Blueprint('events', __name__, url_prefix='/events')

def notify_approvers(event, required_role):
    from app.models import User, Role
    role = Role.query.filter_by(name=required_role).first()
    if not role:
        return
        
    query = User.query.filter_by(role_id=role.id)
    # If the role is department specific, only notify the approvers in the same department
    if required_role in ['Faculty', 'HOD']:
        query = query.filter_by(department_id=event.department_id)
        
    approvers = query.all()
    for approver in approvers:
        send_email_notification(
            approver.email, 
            "Action Required: New Event Proposal", 
            f"A new event proposal '{event.title}' requires your ({required_role}) approval."
        )

def save_file(file):
    if not file or file.filename == '':
        return None
    filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4().hex}_{filename}"
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
    file.save(filepath)
    return unique_filename

def send_async_email(app, msg):
    with app.app_context():
        try:
            mail.send(msg)
            print(f"\n--- ASYNC EMAIL SENT SUCCESSFULLY ---")
            print(f"TO: {msg.recipients}")
            print(f"SUBJECT: {msg.subject}")
            print("------------------------------------\n")
        except Exception as e:
            print(f"Async Email failed: {e}")

def send_email_notification(to_email, subject, body):
    try:
        if not current_app.config.get('MAIL_USERNAME'):
            print(f"\n--- EMAIL SIMULATION (NOT CONFIGURED) ---")
            print(f"TO: {to_email}")
            print(f"SUBJECT: {subject}")
            print("-----------------------------------------\n")
            return
            
        msg = Message(subject, recipients=[to_email])
        msg.body = body
        
        # Send in background thread to prevent Gunicorn timeout
        app = current_app._get_current_object()
        Thread(target=send_async_email, args=(app, msg)).start()
        
    except Exception as e:
        print(f"Email failed to process for {to_email}: {e}")

@events_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    from datetime import date
    from sqlalchemy import or_
    
    # Check if the user has any past approved events without completion proof
    past_missing_events = Event.query.filter(
        Event.organizer_id == current_user.id,
        Event.status == 'Approved',
        Event.event_date < date.today(),
        or_(Event.post_event_report_path == None, Event.post_event_report_path == '')
    ).all()

    missing_events = [e for e in past_missing_events if not e.post_event_report_path]
    
    if missing_events:
        flash(f"You cannot create a new event. You have a past event ('{missing_events[0].title}') with missing completion proof. Please upload the proof first.", "danger")
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        # Auto generate Event ID
        current_year = datetime.now().year
        event_count = Event.query.count() + 1
        while True:
            event_id_str = f"EVT-{current_year}-{event_count:03d}"
            existing_event = Event.query.filter_by(event_id=event_id_str).first()
            if not existing_event:
                break
            event_count += 1
        
        # Save files
        proposal_pdf = request.files.get('proposal_pdf')
        budget_pdf = request.files.get('budget_pdf')
        proposal_path = save_file(proposal_pdf)
        budget_path = save_file(budget_pdf)

        try:
            event_date = datetime.strptime(request.form.get('event_date'), '%Y-%m-%d').date()
            budget = float(request.form.get('budget', 0.0))
            expected_participants = int(request.form.get('expected_participants', 0))
        except ValueError:
            flash('Invalid date or number format provided.', 'danger')
            return redirect(url_for('events.create'))

        venue_id = request.form.get('venue_id')
        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')
        
        try:
            start_time = datetime.strptime(start_time_str, '%H:%M').time() if start_time_str else None
            end_time = datetime.strptime(end_time_str, '%H:%M').time() if end_time_str else None
        except ValueError:
            flash('Invalid time format provided.', 'danger')
            return redirect(url_for('events.create'))

        if venue_id and start_time and end_time:
            # If a University Level event is on this date, block ANY new bookings
            blocking_univ_event = Event.query.filter(
                Event.event_date == event_date,
                Event.event_type == 'University Level',
                Event.status != 'Rejected'
            ).first()
            
            if blocking_univ_event:
                flash(f'A University Level event ({blocking_univ_event.title}) is scheduled for this date. No other events (Department or University level) can be booked on this day.', 'danger')
                return redirect(url_for('events.create'))

            # Apply a 1-hour buffer for cleaning/setup between events
            from datetime import timedelta
            start_dt = datetime.combine(event_date, start_time)
            end_dt = datetime.combine(event_date, end_time)
            
            start_time_buf = (start_dt - timedelta(minutes=60)).time()
            end_time_buf = (end_dt + timedelta(minutes=60)).time()

            # Check for venue overlaps
            overlapping_events = Event.query.filter(
                Event.event_date == event_date,
                Event.venue_id == venue_id,
                Event.status != 'Rejected',
                Event.start_time < end_time_buf,
                Event.end_time > start_time_buf
            ).first()
            
            if overlapping_events:
                # Calculate when the venue is free (end_time + 1 hour buffer)
                overlapping_end_dt = datetime.combine(event_date, overlapping_events.end_time)
                free_from_time = (overlapping_end_dt + timedelta(minutes=60)).strftime('%I:%M %p')
                
                flash(f'This venue is already booked for the selected time slot. It will be free from {free_from_time} (including a mandatory 1-hour setup/cleaning buffer). Please choose a different time or venue.', 'danger')
                return redirect(url_for('events.create'))
                
        from app.models import Venue
        venue_obj = Venue.query.get(venue_id) if venue_id else None
        venue_name = venue_obj.name if venue_obj else request.form.get('venue')

        new_event = Event(
            event_id=event_id_str,
            title=request.form.get('title'),
            event_type=request.form.get('event_type'),
            organizer_name=request.form.get('organizer_name'),
            faculty_coordinator=request.form.get('faculty_coordinator'),
            event_date=event_date,
            start_time=start_time,
            end_time=end_time,
            venue_id=venue_id,
            venue=venue_name, # Legacy fallback
            budget=budget,
            funding_source=request.form.get('funding_source'),
            expected_participants=expected_participants,
            chief_guest=request.form.get('chief_guest'),
            objectives=request.form.get('objectives'),
            description=request.form.get('description'),
            proposal_pdf_path=proposal_path,
            budget_pdf_path=budget_path,
            status='Pending', # Will update based on event_type below
            department_id=int(request.form.get('department_id', current_user.department_id or 1)),
            organizer_id=current_user.id
        )
        db.session.add(new_event)
        db.session.flush() # Get new_event.id

        # Create Approval Workflow with Auto-Approval Logic
        HIERARCHY = {
            'Student/Organizer': 0,
            'Faculty': 1,
            'HOD': 2,
            'Director': 3,
            'Pro VC': 4,
            'VC': 5,
            'Admin': 99
        }
        user_level = HIERARCHY.get(current_user.role.name, 0)
        
        roles_to_create = []
        if new_event.event_type == 'University Level':
            roles_to_create = ['Faculty', 'HOD', 'Director', 'Pro VC', 'VC']
        else:
            roles_to_create = ['Faculty', 'HOD']

        approvals = []
        for i, required_role in enumerate(roles_to_create):
            req_level = HIERARCHY.get(required_role, 0)
            status = 'Pending'
            comments = None
            action_date = None
            approver_id = None
            
            # Auto-approve if the submitter is at or above this role level
            if user_level >= req_level:
                status = 'Approved'
                comments = f'Auto-approved by system (Submitter is {current_user.role.name})'
                action_date = datetime.utcnow()
                approver_id = current_user.id
                
            approvals.append(Approval(
                event_id=new_event.id, 
                required_role=required_role, 
                level=i+1, 
                status=status,
                comments=comments,
                action_date=action_date,
                approver_id=approver_id
            ))

        db.session.bulk_save_objects(approvals)
        
        # Determine the overall event status by finding the first pending approval
        next_pending_role = None
        for app_obj in approvals:
            if app_obj.status == 'Pending':
                next_pending_role = app_obj.required_role
                break
                
        if next_pending_role:
            new_event.status = f'Pending {next_pending_role} Approval'
        else:
            new_event.status = 'Approved'
        
        # Notification for organizer
        notif = Notification(user_id=current_user.id, message=f"Your proposal '{new_event.title}' has been submitted.")
        db.session.add(notif)
        
        # Email to organizer
        send_email_notification(current_user.email, "Proposal Submitted", f"Your event proposal '{new_event.title}' was submitted successfully.")

        # Notify the first actual pending approver (if any)
        if next_pending_role:
            notify_approvers(new_event, next_pending_role)

        db.session.commit()
        flash('Event proposal submitted successfully!', 'success')
        return redirect(url_for('dashboard.index'))

    from app.models import Department, Venue
    departments = Department.query.all()
    venues = Venue.query.all()
    
    return render_template('events/create.html', departments=departments, venues=venues)

@events_bp.route('/<int:event_id>', methods=['GET', 'POST'])
@login_required
def view(event_id):
    event = Event.query.get_or_404(event_id)
    approvals = Approval.query.filter_by(event_id=event.id).order_by(Approval.level).all()
    chat_messages = EventComment.query.filter_by(event_id=event.id).order_by(EventComment.created_at).all()
    
    # Determine which approval is currently active in the hierarchy
    current_approval = None
    for app in approvals:
        if app.status in ['Pending', 'Returned for Correction']:
            current_approval = app
            break

    can_approve = False
    if current_approval:
        if current_user.is_admin():
            can_approve = True
        elif current_user.role.name == current_approval.required_role:
            can_approve = True

    # Handle approval action
    if request.method == 'POST' and can_approve:
        action = request.form.get('action') # Approved, Rejected, Returned for Correction
        comments = request.form.get('comments')
        
        current_approval.status = action
        current_approval.comments = comments
        current_approval.approver_id = current_user.id
        current_approval.action_date = datetime.utcnow()

        if action == 'Rejected':
            event.status = 'Rejected'
        elif action == 'Returned for Correction':
            event.status = 'Returned for Correction'
        elif action == 'Approved':
            # Check if there's any pending approval left in the hierarchy
            next_app = None
            for app in approvals: # approvals is already ordered by level
                if app.status in ['Pending', 'Returned for Correction']:
                    next_app = app
                    break
                    
            if next_app:
                event.status = f"Pending {next_app.required_role} Approval"
                # Notify the next approver in line
                notify_approvers(event, next_app.required_role)
            else:
                event.status = 'Approved'
                
        notif = Notification(user_id=event.organizer_id, message=f"Event '{event.title}' was {action} by {current_user.role.name}")
        db.session.add(notif)
        
        # Email organizer about status change
        from app.models import User
        organizer_user = User.query.get(event.organizer_id)
        if organizer_user:
            send_email_notification(organizer_user.email, f"Proposal {action}", f"Your proposal '{event.title}' was {action} by {current_user.role.name}.\nComments: {comments or 'None'}")
        
        db.session.commit()
        flash('Action recorded successfully.', 'success')
        return redirect(url_for('events.view', event_id=event.id))

    return render_template('events/view.html', event=event, approvals=approvals, can_approve=can_approve, current_approval=current_approval, chat_messages=chat_messages)

@events_bp.route('/<int:event_id>/chat', methods=['POST'])
@login_required
def post_chat(event_id):
    from app.models import EventComment
    event = Event.query.get_or_404(event_id)
    message_text = request.form.get('message')
    
    if message_text and message_text.strip():
        new_msg = EventComment(message=message_text.strip(), event_id=event.id, user_id=current_user.id)
        db.session.add(new_msg)
        db.session.commit()
        flash('Message posted.', 'success')
    else:
        flash('Message cannot be empty.', 'warning')
        
    return redirect(url_for('events.view', event_id=event.id))

@events_bp.route('/<int:event_id>/download_pdf')
@login_required
def download_pdf(event_id):
    event = Event.query.get_or_404(event_id)
    approvals = Approval.query.filter_by(event_id=event.id).order_by(Approval.level).all()
    
    pdf_data = generate_approval_pdf(event, approvals)
    
    response = make_response(pdf_data)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=event_{event.event_id}.pdf'
    return response

@events_bp.route('/attachment/<filename>')
@login_required
def download_attachment(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)

@events_bp.route('/<int:event_id>/delete', methods=['POST'])
@login_required
def delete_event(event_id):
    if not current_user.is_admin():
        flash('You do not have permission to delete events.', 'danger')
        return redirect(url_for('dashboard.index'))
        
    event = Event.query.get_or_404(event_id)
    
    # The admin can delete any event, regardless of status.
        
    # Delete associated comments and approvals
    from app.models import EventComment, Approval
    EventComment.query.filter_by(event_id=event.id).delete()
    Approval.query.filter_by(event_id=event.id).delete()
    
    db.session.delete(event)
    db.session.commit()
    flash(f"Event '{event.title}' was successfully deleted.", 'success')
    return redirect(url_for('dashboard.index'))

@events_bp.route('/<int:event_id>/upload_report', methods=['POST'])
@login_required
def upload_report(event_id):
    event = Event.query.get_or_404(event_id)
    
    # Ensure only the organizer (or admin) can upload the report
    if event.organizer_id != current_user.id and not current_user.is_admin():
        flash("Only the event organizer can generate the post-event report.", "danger")
        return redirect(url_for('events.view', event_id=event.id))
        
    if event.status != 'Approved':
        flash("You can only generate a report for an approved event.", "warning")
        return redirect(url_for('events.view', event_id=event.id))
        
    if 'report_files' not in request.files:
        flash("No file part", "danger")
        return redirect(url_for('events.view', event_id=event.id))
        
    files = request.files.getlist('report_files')
    if not files or files[0].filename == '':
        flash("No selected file", "danger")
        return redirect(url_for('events.view', event_id=event.id))
        
    upload_folder = current_app.config['UPLOAD_FOLDER']
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
        
    saved_files_data = []
    allowed_extensions = {'.pdf', '.jpg', '.jpeg', '.png'}
    
    import base64
    for file in files:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext in allowed_extensions:
            file_data = file.read()
            mime_type = "application/octet-stream"
            if ext == '.pdf':
                mime_type = "application/pdf"
            elif ext in {'.jpg', '.jpeg'}:
                mime_type = "image/jpeg"
            elif ext == '.png':
                mime_type = "image/png"
            
            base64_str = f"data:{mime_type};base64," + base64.b64encode(file_data).decode('utf-8')
            saved_files_data.append(base64_str)
            
    if saved_files_data:
        new_files_str = "|||".join(saved_files_data)
        if event.post_event_report_path:
            event.post_event_report_path += "|||" + new_files_str
        else:
            event.post_event_report_path = new_files_str
        db.session.commit()
        flash("Post-event proof/images uploaded successfully!", "success")
    else:
        flash("Only PDF and Image files (.jpg, .png) are allowed.", "danger")
        
    return redirect(url_for('events.view', event_id=event.id))
