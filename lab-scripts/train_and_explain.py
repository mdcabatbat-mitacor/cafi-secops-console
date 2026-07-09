import pandas as pd, joblib, shap, json

df = pd.read_parquet("features.parquet")

X = pd.get_dummies(df[["Severity", "ContextStatus"]])
X["ContextualAlertScore"] = df["ContextualAlertScore"]

from sklearn.ensemble import IsolationForest
model = IsolationForest(n_estimators=200, contamination=0.2, random_state=42).fit(X)
joblib.dump(model, "iforest.pkl")

raw_scores = -model.score_samples(X)
anomaly = (raw_scores - raw_scores.min()) / (raw_scores.max() - raw_scores.min() + 1e-9)

explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X)

anomaly_rows, explanation_rows = [], []
for i in range(len(df)):
    top5 = sorted(zip(X.columns, shap_values[i]), key=lambda p: abs(p[1]), reverse=True)[:5]
    tag = "[Simulated seed] " if df.iloc[i]["DataSource"] == "Simulated-Seed" else ""
    anomaly_rows.append({
        "TimeGenerated": df.iloc[i]["TimeGenerated"],
        "DeviceRef": df.iloc[i]["DeviceRef"],
        "AnomalyScore": round(float(anomaly[i]), 4),
    })
    explanation_rows.append({
        "TimeGenerated": df.iloc[i]["TimeGenerated"],
        "DeviceRef": df.iloc[i]["DeviceRef"],
        "AnomalyScore": round(float(anomaly[i]), 4),
        "ContextStatus": df.iloc[i]["ContextStatus"],
        "NarrativeSummary": f"{tag}Top driver: {top5[0][0]} ({top5[0][1]:+.3f})",
        "PivotSteps": "Review asset criticality and recent change window for this device.",
        **{f"Driver{n+1}": f"{feat} ({val:+.3f})" for n, (feat, val) in enumerate(top5)},
    })

json.dump(anomaly_rows, open("anomaly_scores.json", "w"), indent=2)
json.dump(explanation_rows, open("explanations.json", "w"), indent=2)
print(f"Trained on {len(df)} rows. Wrote anomaly_scores.json and explanations.json.")
