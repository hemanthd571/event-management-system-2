from app import create_app, db
from app.models import Role, User, Department

app = create_app()

def seed_db():
    with app.app_context():
        # Create Roles
        roles = ['Admin', 'Student/Organizer', 'Faculty', 'HOD', 'Director', 'Pro VC', 'VC']
        for role_name in roles:
            if not Role.query.filter_by(name=role_name).first():
                r = Role(name=role_name)
                db.session.add(r)
        
        # Create a default Department
        if not Department.query.filter_by(code='CSE').first():
            d = Department(name='Computer Science and Engineering', code='CSE')
            db.session.add(d)
        
        db.session.commit()

        # Create Admin User
        admin_role = Role.query.filter_by(name='Admin').first()
        if admin_role and not User.query.filter_by(username='admin').first():
            admin_user = User(
                username='admin',
                email='admin@college.edu',
                role_id=admin_role.id
            )
            admin_user.set_password('admin123')
            db.session.add(admin_user)
        
        db.session.commit()
        print("Database seeded successfully with Roles and Admin user.")

if __name__ == '__main__':
    seed_db()
