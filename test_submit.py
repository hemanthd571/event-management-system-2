import requests

url = 'http://127.0.0.1:5000/auth/login'
session = requests.Session()

# 1. Login
login_data = {
    'email': 'student1@test.com',
    'password': 'password123'
}
r_login = session.post(url, data=login_data)
print("Login Status:", r_login.status_code)

# 2. Submit Proposal
url_create = 'http://127.0.0.1:5000/events/create'
event_data = {
    'title': 'Test Event API',
    'event_type': 'Department Level',
    'department_id': '1',
    'organizer_name': 'student1',
    'faculty_coordinator': 'Prof. Smith',
    'event_date': '2026-10-10',
    'start_time': '10:00',
    'end_time': '12:00',
    'venue_id': '1',
    'budget': '500.00',
    'funding_source': 'Department',
    'expected_participants': '50',
    'objectives': 'Test objective',
    'description': 'Test description'
}

r_create = session.post(url_create, data=event_data, allow_redirects=False)
print("Create Event Status:", r_create.status_code)
if r_create.status_code != 302:
    print(r_create.text)
