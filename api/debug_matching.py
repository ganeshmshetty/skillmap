import json

cat = json.load(open('../data/catalog/modules.json'))
cat_skills = set()
for m in cat:
    cat_skills.update(m['skill_ids'])

onet = json.load(open('../data/onet_skills.json'))
onet_by_id = {n['id']: n for n in onet}

print("=== Catalog skill_ids and their O*NET titles ===")
for sid in sorted(cat_skills)[:30]:
    node = onet_by_id.get(sid)
    title = node['title'] if node else '???'
    print(f"  {sid} -> {title}")

# Now check: for the skills the LLM extracts (e.g. "Python", "Docker"), 
# does our anchor_to_onet match them to IDs in the catalog?
print("\n=== Testing anchor_to_onet matching ===")
test_skills = ["Python", "Docker", "Kubernetes", "NoSQL", "PostgreSQL", "Go", "Java", "REST APIs", "Machine Learning"]
onet_titles_lower = {}
alias_map = {}
for n in onet:
    onet_titles_lower[n['title'].lower()] = n['id']
    for alias in n.get('aliases', []):
        alias_map[alias.lower()] = n['id']

for skill_name in test_skills:
    lower = skill_name.lower()
    matched_id = onet_titles_lower.get(lower) or alias_map.get(lower)
    in_catalog = matched_id in cat_skills if matched_id else False
    print(f"  '{skill_name}' -> onet_id={matched_id}, in_catalog={in_catalog}")
