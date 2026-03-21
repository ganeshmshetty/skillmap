from app.main import JOBS
import json

# Print the most recent job result
if not JOBS:
    print("No jobs found in current session.")
else:
    last_id = list(JOBS.keys())[-1]
    last_job = JOBS[last_id]
    print(f"--- Job ID: {last_id} ---")
    print(json.dumps(last_job, indent=2))
