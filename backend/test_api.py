"""Quick API test script."""
import urllib.request
import json

BASE = "http://127.0.0.1:8001"

def get(path):
    r = urllib.request.urlopen(f"{BASE}{path}")
    return json.loads(r.read())

def post(path):
    req = urllib.request.Request(f"{BASE}{path}", method="POST", data=b"")
    r = urllib.request.urlopen(req)
    return json.loads(r.read())

# Get a corrective event
events = get("/api/service-events/?page=1&page_size=1&event_category=corrective")
event_id = events["items"][0]["id"]
print(f"Event: {event_id}")
print(f"Description: {events['items'][0]['order_description']}")

# Generate recommendation
rec = post(f"/api/recommendations/generate/{event_id}")
print(f"\nConfidence: {rec['confidence_score']}")
print(f"Similar cases: {rec['similar_case_count']}")
print(f"Most frequent action: {rec['most_frequent_action']}")
print(f"\nReasoning:\n{rec['reasoning']}")
print(f"\nWorkflow ({len(rec['workflow_steps'])} steps):")
for step in rec["workflow_steps"]:
    print(f"  {step['step_number']}. {step['instruction']}")

if rec["similar_cases"]:
    print(f"\nSimilar cases shown: {len(rec['similar_cases'])}")
    for sc in rec["similar_cases"][:3]:
        print(f"  Score: {sc['similarity_score']} - {sc['match_reason'][:80]}")
