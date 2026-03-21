import requests, time, json
with open('r.txt', 'w') as f: f.write('resume')
with open('j.txt', 'w') as f: f.write('jd')
resp = requests.post('http://localhost:8000/analyze', files={'resume': open('r.txt', 'rb'), 'jd': open('j.txt', 'rb')})
job_id = resp.json()['job_id']
while True:
    res = requests.get(f'http://localhost:8000/result/{job_id}').json()
    if res['status'] in ['completed', 'failed']:
        with open('error_desc.txt', 'w') as f:
            f.write(res.get('error', {}).get('details', {}).get('reason', str(res)))
        break
    time.sleep(0.5)
