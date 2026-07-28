import os
import uuid
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from app.models import Event, Approval, Notification, EventComment
from app import db
from werkzeug.utils import secure_filename
from app.utils.pdf_report import generate_approval_pdf
from flask import make_response
from flask_mail import Message
from app import mail

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

def send_email_notification(to_email, subject, body):
    try:
        msg = Message(subject, recipients=[to_email])
        msg.body = body
        
        # Actually send through SMTP
        mail.send(msg) 
        
        print(f"\n--- REAL EMAIL SENT SUCCESSFULLY ---")
        print(f"TO: {to_email}")
        print(f"SUBJECT: {subject}")
        print("------------------------------------\n")
    except Exception as e:
        print(f"Email failed to process for {to_email}: {e}")

@events_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        # Auto generate Event ID
        event_count = Event.query.count() + 1
        event_id_str = f"EVT-{datetime.now().year}-{event_count:03d}"
        
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
            # Check for overlaps
            overlapping_events = Event.query.filter(
                Event.event_date == event_date,
                Event.venue_id == venue_id,
                Event.status != 'Rejected',
                Event.start_time < end_time,
                Event.end_time > start_time
            ).first()
            
            if overlapping_events:
                flash('This venue is already booked for the selected time slot. Please choose a different time or venue.', 'danger')
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

        # Create Approval Workflow
        approvals = []
        if new_event.event_type == 'University Level':
            # Faculty -> HOD -> Director -> Pro VC -> VC
            approvals.append(Approval(event_id=new_event.id, required_role='Faculty', level=1, status='Pending'))
            approvals.append(Approval(event_id=new_event.id, required_role='HOD', level=2, status='Pending'))
            approvals.append(Approval(event_id=new_event.id, required_role='Director', level=3, status='Pending'))
            approvals.append(Approval(event_id=new_event.id, required_role='Pro VC', level=4, status='Pending'))
            approvals.append(Approval(event_id=new_event.id, required_role='VC', level=5, status='Pending'))
            new_event.status = 'Pending Faculty Approval'
        else:
            # Department Level: Faculty -> HOD
            approvals.append(Approval(event_id=new_event.id, required_role='Faculty', level=1, status='Pending'))
            approvals.append(Approval(event_id=new_event.id, required_role='HOD', level=2, status='Pending'))
            new_event.status = 'Pending Faculty Approval'

        db.session.bulk_save_objects(approvals)
        
        # Notification for organizer
        notif = Notification(user_id=current_user.id, message=f"Your proposal '{new_event.title}' has been submitted.")
        db.session.add(notif)
        
        # Email to organizer
        send_email_notification(current_user.email, "Proposal Submitted", f"Your event proposal '{new_event.title}' was submitted successfully.")

        # Notify the first approver
        notify_approvers(new_event, approvals[0].required_role)

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
    
    # Determine which approval is currently active
    current_approval = None
    for app in approvals:
        if app.status in ['Pending', 'Returned for Correction']:
            current_approval = app
            break

    can_approve = False
    if current_approval and current_user.role.name == current_approval.required_role:
        if current_user.role.name in ['Faculty', 'HOD']:
            if current_user.department_id == event.department_id:
                can_approve = True
        else:
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
            next_app = Approval.query.filter_by(event_id=event.id, level=current_approval.level + 1).first()
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
