import json
with open('contextual_alert_score.kql') as f:
    query = f.read()
body = {
    "properties": {
        "category": "CAFI SecOps",
        "displayName": "ContextualAlertScore",
        "query": query,
        "functionAlias": "ContextualAlertScore",
        "functionParameters": "",
        "tags": []
    }
}
with open('body.json', 'w') as f:
    json.dump(body, f)
print("Wrote body.json")
