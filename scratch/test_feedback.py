import requests

session = requests.Session()
login_data = {'email': 'student1@example.com', 'password': 'password'}
res = session.post('http://127.0.0.1:5000/auth/login', data=login_data)

feedback_data = {'rating': '5', 'comments': 'Great!'}
res = session.post('http://127.0.0.1:5000/events/1/feedback', data=feedback_data)
print("Status Code:", res.status_code)
if res.status_code == 500:
    print("500 ERROR CAUGHT!")
    print(res.text)
else:
    print("SUCCESS")
