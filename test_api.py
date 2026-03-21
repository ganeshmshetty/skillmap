import requests, time, json

# Create realistic test files
resume_text = """
John Smith - Software Engineer
5 years of experience in Python, JavaScript, and React.
Built microservices with Docker and deployed on Kubernetes.
Experienced with PostgreSQL and Redis for data storage.
Familiar with Git, Linux, and CI/CD pipelines.
"""

jd_text = """
Senior Full-Stack Engineer
Requirements:
- 5+ years experience with Python and JavaScript
- Expert in React.js and Node.js
- Strong experience with Docker and Kubernetes
- Experience with PostgreSQL and MongoDB/NoSQL databases
- Knowledge of Apache Kafka for event-driven architecture
- Experience with TensorFlow or PyTorch for ML pipelines
- Proficiency with Git and Linux
- Cloud infrastructure (AWS/GCP)
"""

with open('test_resume.txt', 'w') as f:
    f.write(resume_text)
with open('test_jd.txt', 'w') as f:
    f.write(jd_text)

# Submit analysis
resp = requests.post(
    'http://localhost:8000/analyze',
    files={
        'resume': ('resume.txt', open('test_resume.txt', 'rb')),
        'jd': ('jd.txt', open('test_jd.txt', 'rb'))
    }
)
job_id = resp.json()['job_id']
print(f"Job ID: {job_id}")

# Poll for result
for _ in range(30):
    res = requests.get(f'http://localhost:8000/result/{job_id}').json()
    status = res['status']
    print(f"Status: {status}")
    if status in ['completed', 'failed']:
        break
    time.sleep(1)

print("\n" + "="*80)
print(json.dumps(res, indent=2))
