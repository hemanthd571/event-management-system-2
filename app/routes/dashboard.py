from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from app.models import Event, Notification, Department
from app import db
from sqlalchemy import func

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def index():
    # Calculate Total Approved Budget
    total_budget = db.session.query(func.sum(Event.budget)).filter(Event.status == 'Approved').scalar() or 0.0

    # Get Budget by Department for Chart
    dept_budgets = db.session.query(
        Department.name, 
        func.sum(Event.budget)
    ).join(Event, Department.id == Event.department_id).filter(Event.status == 'Approved').group_by(Department.name).all()
    
    chart_labels = [row[0] for row in dept_budgets]
    chart_data = [float(row[1] or 0) for row in dept_budgets]

    # If the user is a Student/Organizer, only show their own events
    if current_user.role.name == 'Student/Organizer':
        events_query = Event.query.filter_by(organizer_id=current_user.id)
    else:
        events_query = Event.query

    pending_my_approval = []
    if current_user.role.name in ['Faculty', 'HOD', 'Director', 'Pro VC', 'VC', 'Admin']:
        candidate_events = Event.query.filter(Event.status.notin_(['Approved', 'Rejected'])).all()
        for event in candidate_events:
            sorted_approvals = sorted(event.approvals, key=lambda a: a.level)
            current_app = None
            
            # Find the first pending approval in the hierarchy
            for app in sorted_approvals:
                if app.status in ['Pending', 'Returned for Correction']:
                    current_app = app
                    break
            
            if current_app:
                if current_user.is_admin():
                    pending_my_approval.append(event)
                elif current_user.role.name == current_app.required_role:
                    pending_my_approval.append(event)
        
    context = {
        'total_events': Event.query.count(),
        'pending_events': Event.query.filter(Event.status != 'Approved', Event.status != 'Rejected').count(),
        'approved_events': Event.query.filter_by(status='Approved').count(),
        'rejected_events': Event.query.filter_by(status='Rejected').count(),
        'all_events': events_query.order_by(Event.created_at.desc()).all(),
        'pending_my_approval': pending_my_approval,
        'total_budget': total_budget,
        'chart_labels': chart_labels,
        'chart_data': chart_data
    }
    return render_template('dashboard/index.html', **context)

from flask import url_for

@dashboard_bp.route('/calendar')
@login_required
def calendar():
    return render_template('dashboard/calendar.html')

@dashboard_bp.route('/api/events/calendar')
@login_required
def api_calendar_events():
    event_type = request.args.get('type')
    
    # Only show approved events on the calendar
    query = Event.query.filter_by(status='Approved')
    
    if event_type:
        query = query.filter_by(event_type=event_type)
        
    approved_events = query.all()
    events_data = []
    for event in approved_events:
        events_data.append({
            'id': event.id,
            'title': event.title,
            'start': event.event_date.strftime('%Y-%m-%d'),
            'url': url_for('events.view', event_id=event.id)
        })
    return jsonify(events_data)

import csv
import io
from flask import Response

@dashboard_bp.route('/export')
@login_required
def export_events():
    if current_user.role.name == 'Student/Organizer':
        events = Event.query.filter_by(organizer_id=current_user.id).order_by(Event.created_at.desc()).all()
    else:
        events = Event.query.order_by(Event.created_at.desc()).all()
        
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['Event ID', 'Title', 'Type', 'Organizer', 'Faculty Coordinator', 'Date', 'Time', 'Venue', 'Budget', 'Status', 'Created At'])
    
    for event in events:
        writer.writerow([
            event.event_id,
            event.title,
            event.event_type,
            event.organizer_name,
            event.faculty_coordinator,
            event.event_date.strftime('%Y-%m-%d') if event.event_date else '',
            event.event_time,
            event.venue,
            event.budget,
            event.status,
            event.created_at.strftime('%Y-%m-%d %H:%M:%S') if event.created_at else ''
        ])
        
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=events_export.csv"}
    )
