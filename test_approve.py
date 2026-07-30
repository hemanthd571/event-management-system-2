from app import create_app, db
from app.models import Event, User, Role, Approval

app = create_app()
with app.app_context():
    # Find any pending approval
    pending_app = Approval.query.filter_by(status='Pending').first()
    if not pending_app:
        print("No pending approvals")
        exit()
        
    event = Event.query.get(pending_app.event_id)
    user = User.query.filter_by(role_id=Role.query.filter_by(name=pending_app.required_role).first().id).first()
    
    if not user:
        print(f"No user found for role {pending_app.required_role}")
        exit()
        
    print(f"Approving event {event.id} by user {user.username} ({pending_app.required_role})")
    
    current_approval = pending_app
    action = 'Approved'
    comments = 'Looks good'
    
    current_approval.status = action
    current_approval.comments = comments
    current_approval.approver_id = user.id
    from datetime import datetime
    current_approval.action_date = datetime.utcnow()
    
    approvals = Approval.query.filter_by(event_id=event.id).order_by(Approval.level).all()
    
    next_app = None
    for app_obj in approvals:
        if app_obj.status in ['Pending', 'Returned for Correction']:
            next_app = app_obj
            break
            
    if next_app:
        event.status = f"Pending {next_app.required_role} Approval"
        from app.routes.events import notify_approvers
        notify_approvers(event, next_app.required_role)
    else:
        event.status = 'Approved'
        
    from app.models import Notification
    notif = Notification(user_id=event.organizer_id, message=f"Event '{event.title}' was {action} by {user.role.name}")
    db.session.add(notif)
    
    from app.routes.events import send_email_notification
    organizer_user = User.query.get(event.organizer_id)
    if organizer_user:
        send_email_notification(organizer_user.email, f"Proposal {action}", f"Your proposal '{event.title}' was {action} by {user.role.name}.\nComments: {comments or 'None'}")
        
    try:
        db.session.commit()
        print("Committed successfully")
    except Exception as e:
        print(f"Error committing: {e}")
        db.session.rollback()
