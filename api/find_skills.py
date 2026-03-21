"""
Build a proper course catalog with modules mapped to real O*NET skill IDs
for common tech skills like Python, Docker, Kubernetes, etc.
"""
import json

# Load O*NET data to find real IDs
with open('../data/onet_skills.json') as f:
    onet = json.load(f)

# Build lookup maps
title_to_id = {}
for n in onet:
    title_to_id[n['title'].lower()] = n['id']
    for alias in n.get('aliases', []):
        title_to_id[alias.lower()] = n['id']

# Find IDs for common skills
target_skills = [
    "Python", "Java", "JavaScript", "Go", "C++", "Ruby", "TypeScript", "Rust", "C#",
    "Docker", "Kubernetes", "Git", "Linux",
    "SQL", "PostgreSQL", "MySQL", "MongoDB", "NoSQL", "Redis",
    "React", "Angular", "Node.js",
    "Machine learning", "TensorFlow", "PyTorch",
    "Amazon Web Services", "Microsoft Azure", "Google Cloud Platform",
    "REST APIs", "GraphQL", "gRPC",
    "HTML", "CSS",
    "Apache Kafka", "RabbitMQ",
    "Jenkins", "Terraform", "Ansible",
    "Agile", "Scrum",
    "Data analysis", "Data visualization",
    "Cybersecurity", "Network security",
    "DevOps", "CI/CD",
]

found = {}
not_found = []
for skill in target_skills:
    sid = title_to_id.get(skill.lower())
    if sid:
        found[skill] = sid
    else:
        not_found.append(skill)

print("=== Found O*NET IDs ===")
for name, sid in sorted(found.items()):
    print(f"  {name}: {sid}")

print(f"\n=== Not Found ({len(not_found)}) ===")
for name in not_found:
    print(f"  {name}")

# Save the mapping
with open('skill_mapping.json', 'w') as f:
    json.dump(found, f, indent=2)
