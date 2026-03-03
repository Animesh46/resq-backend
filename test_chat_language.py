import httpx

r = httpx.post('http://127.0.0.1:8000/api/chat', json={'location':'Madurai','disaster':'flood','message':'Hello','language':'hi'})
print('status', r.status_code)
print('reply', r.json().get('reply'))
