from flask import Blueprint, render_template, jsonify, request, url_for, Response
from flask_login import login_required, current_user
from app.dal import get_db_connection
from app.models_raw import Event, Department, Approval
import csv
import io
import datetime

dashboard_bp = Blueprint('dashboard', __name__)

def fetch_events_from_db(query, params=None):
    conn = get_db_connection()
    events = []
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, params or ())
            for row in cursor.fetchall():
                event = Event(**row)
                
                # Fetch approvals for this event
                cursor.execute('SELECT * FROM approvals WHERE event_id = %s ORDER BY level', (event.id,))
                event.approvals = [Approval(**arow) for arow in cursor.fetchall()]
                
                events.append(event)
    finally:
        conn.close()
    return events

@dashboard_bp.route('/')
@login_required
def index():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Calculate Total Approved Budget
            cursor.execute('SELECT SUM(budget) as total FROM events WHERE status = %s', ('Approved',))
            row = cursor.fetchone()
            total_budget = float(row['total'] or 0.0) if row else 0.0

            # Get Budget by Department
            cursor.execute('''SELECT d.name, SUM(e.budget) as total 
                              FROM events e JOIN departments d ON e.department_id = d.id 
                              WHERE e.status = %s GROUP BY d.name''', ('Approved',))
            dept_budgets = cursor.fetchall()
            chart_labels = [row['name'] for row in dept_budgets]
            chart_data = [float(row['total'] or 0) for row in dept_budgets]
            
            # Get Budget by Event Category
            cursor.execute('''SELECT event_category, SUM(budget) as total 
                              FROM events WHERE status = %s GROUP BY event_category''', ('Approved',))
            cat_budgets = cursor.fetchall()
            cat_chart_labels = [row['event_category'] for row in cat_budgets]
            cat_chart_data = [float(row['total'] or 0) for row in cat_budgets]
            
            # Basic counts
            cursor.execute('SELECT COUNT(*) as c FROM events')
            total_events = cursor.fetchone()['c']
            
            cursor.execute('SELECT COUNT(*) as c FROM events WHERE status != %s AND status != %s', ('Approved', 'Rejected'))
            pending_events = cursor.fetchone()['c']
            
            cursor.execute('SELECT COUNT(*) as c FROM events WHERE status = %s', ('Approved',))
            approved_events = cursor.fetchone()['c']
            
            cursor.execute('SELECT COUNT(*) as c FROM events WHERE status = %s', ('Rejected',))
            rejected_events = cursor.fetchone()['c']
            
    finally:
        conn.close()

    # If the user is a Student/Organizer, only show their own events
    if current_user.role.name == 'Student/Organizer':
        all_events = fetch_events_from_db('SELECT * FROM events WHERE organizer_id = %s ORDER BY created_at DESC', (current_user.id,))
    else:
        all_events = fetch_events_from_db('SELECT * FROM events ORDER BY created_at DESC')

    pending_my_approval = []
    if current_user.role.name in ['Faculty', 'HOD', 'Director', 'Pro VC', 'VC', 'Admin']:
        candidate_events = [e for e in all_events if e.status not in ['Approved', 'Rejected']]
        for event in candidate_events:
            current_app = None
            for app in event.approvals:
                if app.status in ['Pending', 'Returned for Correction']:
                    current_app = app
                    break
            
            if current_app:
                if current_user.is_admin():
                    pending_my_approval.append(event)
                elif current_user.role.name == current_app.required_role:
                    pending_my_approval.append(event)
        
    context = {
        'total_events': total_events,
        'pending_events': pending_events,
        'approved_events': approved_events,
        'rejected_events': rejected_events,
        'all_events': all_events,
        'pending_my_approval': pending_my_approval,
        'total_budget': total_budget,
        'chart_labels': chart_labels,
        'chart_data': chart_data,
        'cat_chart_labels': cat_chart_labels,
        'cat_chart_data': cat_chart_data
    }
    return render_template('dashboard/index.html', **context)

@dashboard_bp.route('/calendar')
@login_required
def calendar():
    return render_template('dashboard/calendar.html')

@dashboard_bp.route('/api/events/calendar')
@login_required
def api_calendar_events():
    event_type = request.args.get('type')
    
    query = 'SELECT * FROM events WHERE status = %s'
    params = ['Approved']
    
    if event_type:
        query += ' AND event_type = %s'
        params.append(event_type)
        
    approved_events = fetch_events_from_db(query, tuple(params))
    
    events_data = []
    for event in approved_events:
        events_data.append({
            'id': event.id,
            'title': event.title,
            'start': event.event_date.strftime('%Y-%m-%d') if event.event_date else '',
            'url': url_for('events.view', event_id=event.id)
        })
    return jsonify(events_data)

@dashboard_bp.route('/export')
@login_required
def export_events():
    if current_user.role.name == 'Student/Organizer':
        events = fetch_events_from_db('SELECT * FROM events WHERE organizer_id = %s ORDER BY created_at DESC', (current_user.id,))
    else:
        events = fetch_events_from_db('SELECT * FROM events ORDER BY created_at DESC')
        
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
