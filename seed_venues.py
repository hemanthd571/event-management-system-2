from app import create_app, db
from app.models import Venue

app = create_app()

def seed_venues():
    with app.app_context():
        venues = [
            Venue(name="Main Auditorium", capacity=500, type="Auditorium"),
            Venue(name="Seminar Hall A", capacity=100, type="Seminar Hall"),
            Venue(name="Seminar Hall B", capacity=100, type="Seminar Hall"),
            Venue(name="CSE Lab 1", capacity=60, type="Lab"),
            Venue(name="ECE Lab 1", capacity=60, type="Lab"),
            Venue(name="Open Grounds", capacity=1000, type="Ground"),
        ]
        
        for v in venues:
            # Check if exists
            existing = Venue.query.filter_by(name=v.name).first()
            if not existing:
                db.session.add(v)
        
        db.session.commit()
        print("Venues seeded successfully!")

if __name__ == '__main__':
    seed_venues()
