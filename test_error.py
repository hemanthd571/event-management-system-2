from app import create_app
import traceback

app = create_app()
app.config['TESTING'] = True
client = app.test_client()

try:
    # We bypass login decorator by mocking the current_user, or we can just mock the session
    with app.test_request_context():
        # Login
        resp = client.post('/auth/login', data={'username': 'admin', 'password': 'password'}) # replace password if needed
        # GET edit user
        res = client.get('/admin/users/1/edit', follow_redirects=True)
        print("Status:", res.status_code)
        if res.status_code == 500:
            print(res.data.decode('utf-8'))
except Exception as e:
    traceback.print_exc()
