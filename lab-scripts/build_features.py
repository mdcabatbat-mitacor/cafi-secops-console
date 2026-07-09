import pandas as pd, subprocess, json, random
from datetime import datetime, timedelta, timezone

CUSTOMER_ID = subprocess.run(
    ["az","monitor","log-analytics","workspace","show","-g","rg-cafi-lab","-n","cafi-law",
     "--query","customerId","-o","tsv"], capture_output=True, text=True).stdout.strip()

def run_kql(query):
    result = subprocess.run(
        ["az","monitor","log-analytics","query","-w",CUSTOMER_ID,"--analytics-query",query,"-o","json"],
        capture_output=True, text=True)
    out = result.stdout
    return pd.DataFrame(json.loads(out)) if out.strip() else pd.DataFrame()

live = run_kql("ContextualAlertScore")

if not live.empty:
    live["DataSource"] = "Live"
    features = live
else:
    assets = run_kql('''
        Watchlist
        | where WatchlistAlias == "AssetInventory" and _DTItemType == "watchlist-item"
        | summarize arg_max(TimeGenerated, *) by tostring(WatchlistItem["DeviceId"])
        | project DeviceId = tostring(WatchlistItem["DeviceId"]),
                   Hostname = tostring(WatchlistItem["Hostname"]),
                   CriticalityTier = toint(WatchlistItem["CriticalityTier"]),
                   SiteCode = tostring(WatchlistItem["SiteCode"]),
                   OwningSector = tostring(WatchlistItem["OwningSector"])
    ''')
    maintenance = run_kql('''
        Watchlist
        | where WatchlistAlias == "MaintenanceWindows" and _DTItemType == "watchlist-item"
        | summarize arg_max(TimeGenerated, *) by tostring(WatchlistItem["WindowId"])
        | project SiteCode = tostring(WatchlistItem["SiteCode"]),
                   OwningSector = tostring(WatchlistItem["OwningSector"]),
                   MaintStart = todatetime(WatchlistItem["StartTime"]),
                   MaintEnd = todatetime(WatchlistItem["EndTime"])
    ''')
    changes = run_kql('''
        Watchlist
        | where WatchlistAlias == "ContextCatalogue" and _DTItemType == "watchlist-item"
        | summarize arg_max(TimeGenerated, *) by tostring(WatchlistItem["ContextId"])
        | project DeviceId = tostring(WatchlistItem["DeviceId"]),
                   ChangeTs = todatetime(WatchlistItem["ChangeTimestamp"])
    ''')

    now = datetime.now(timezone.utc)
    severities = ["Critical","High","Medium","Low"]
    rows = []
    sample_assets = assets.sample(min(8, len(assets)), random_state=42) if not assets.empty else pd.DataFrame()
    for _, a in sample_assets.iterrows():
        rows.append({
            "TimeGenerated": (now - timedelta(minutes=random.randint(0,55))).isoformat(),
            "DeviceRef": a["Hostname"] or a["DeviceId"],
            "Severity": random.choice(severities),
            "SiteCode": a["SiteCode"], "OwningSector": a["OwningSector"],
            "DeviceId": a["DeviceId"], "CriticalityTier": a["CriticalityTier"],
        })
    for fake in ["GHOST-101", "GHOST-102"]:
        rows.append({
            "TimeGenerated": (now - timedelta(minutes=random.randint(0,55))).isoformat(),
            "DeviceRef": fake, "Severity": random.choice(severities),
            "SiteCode": None, "OwningSector": None, "DeviceId": None, "CriticalityTier": None,
        })
    events = pd.DataFrame(rows)

    def score_row(r):
        is_known = pd.notna(r["DeviceId"])
        crit = r["CriticalityTier"] if is_known else -1
        in_maint = False
        if is_known and not maintenance.empty:
            m = maintenance[(maintenance.SiteCode == r["SiteCode"]) & (maintenance.OwningSector == r["OwningSector"])]
            if not m.empty:
                t = pd.Timestamp(r["TimeGenerated"])
                in_maint = any((t >= pd.Timestamp(row.MaintStart)) and (t <= pd.Timestamp(row.MaintEnd)) for _, row in m.iterrows())
        recent_change = False
        if is_known and not changes.empty:
            c = changes[changes.DeviceId == r["DeviceId"]]
            if not c.empty:
                t = pd.Timestamp(r["TimeGenerated"])
                recent_change = any((pd.Timestamp(row.ChangeTs) <= t) and (t - pd.Timestamp(row.ChangeTs) <= timedelta(hours=48)) for _, row in c.iterrows())

        context_status = "UnknownAsset" if not is_known else ("InMaintenance" if in_maint else ("RecentlyChanged" if recent_change else "NormalOps"))
        score_crit = 0 if not is_known else (40 if crit == 0 else (20 if crit == 1 else 5))
        score_maint = -25 if in_maint else 0
        score_change = -10 if recent_change else (5 if is_known else 0)
        score_unknown = 30 if not is_known else 0
        score_sev = {"Critical":50,"High":30,"Medium":15}.get(r["Severity"], 0)
        total = score_crit + score_maint + score_change + score_unknown + score_sev
        disposition = "Escalate" if total >= 70 else "Investigate" if total >= 40 else "Monitor" if total >= 15 else "Suppress"
        return pd.Series({"ContextStatus": context_status, "ContextualAlertScore": total, "Disposition": disposition})

    scored = events.join(events.apply(score_row, axis=1))
    scored["DataSource"] = "Simulated-Seed"
    features = scored[["TimeGenerated","DeviceRef","DeviceId","Severity","ContextStatus","ContextualAlertScore","Disposition","DataSource"]]

features.to_parquet("features.parquet", index=False)
print(f"Wrote {len(features)} rows, DataSource={features['DataSource'].unique().tolist()}")
