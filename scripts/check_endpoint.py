import os
import sys

# Add project root to Python module search path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from flask import json

with app.test_client() as client:
    with client.session_transaction() as sess:
        sess['logged_in'] = True
        sess['is_admin'] = True
        sess['username'] = 'admin'
    
    res = client.get('/get_attendance_data')
    print('Status:', res.status_code)
    if res.status_code == 200:
        data = res.get_json()
        print('Students length:', len(data.get('students', [])))
        print('Attendance length:', len(data.get('attendance', [])))
        if data.get('attendance'):
            print('Sample Attendance Row:', data.get('attendance')[0])
    else:
        print(res.data[:500])
