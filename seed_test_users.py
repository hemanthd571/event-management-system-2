from app import create_app, db
from app.models import Role, User, Department

app = create_app()

def seed_test_users():
    with app.app_context():
        dept = Department.query.filter_by(code='CSE').first()
        
        test_accounts = [
            {'username': 'student', 'role': 'Student/Organizer', 'email': 'student@college.edu'},
            {'username': 'faculty', 'role': 'Faculty', 'email': 'faculty@college.edu'},
            {'username': 'hod', 'role': 'HOD', 'email': 'hod@college.edu'},
            {'username': 'director', 'role': 'Director', 'email': 'director@college.edu'},
            {'username': 'provc', 'role': 'Pro VC', 'email': 'provc@college.edu'},
            {'username': 'vc', 'role': 'VC', 'email': 'vc@college.edu'},
        ]
        
        for account in test_accounts:
            # Check if user exists
            if not User.query.filter_by(username=account['username']).first():
                role = Role.query.filter_by(name=account['role']).first()
                if role:
                    user = User(
                        username=account['username'],
                        email=account['email'],
                        role_id=role.id,
                        department_id=dept.id if dept else None
                    )
                    # Everyone gets the same easy password for testing
                    user.set_password('1234')
                    db.session.add(user)
                    
        db.session.commit()
        print("Test hierarchy users seeded successfully! Password for all is '1234'")

if __name__ == '__main__':
    seed_test_users()
