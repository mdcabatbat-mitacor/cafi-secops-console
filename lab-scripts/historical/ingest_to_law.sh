#!/usr/bin/env bash
# CAFI — verified Logs Ingestion helpers (Cloud Shell)
# Prerequisite: Monitoring Metrics Publisher on the target DCR and on cafi-dce
# Auth: az login --scope "https://monitor.azure.com/.default"
#
# Usage:
#   ./ingest_to_law.sh events      /path/to/CAFI_events_clean.csv
#   ./ingest_to_law.sh explanations /path/to/CAFI_explanations_clean.csv
#   ./ingest_to_law.sh fed         /path/to/CAFI_fed_clean.csv
#   ./ingest_to_law.sh aiusage     /path/to/CAFI_aiusage_clean.csv
set -euo pipefail

DCE="${DCE:-https://cafi-dce-mi22.australiaeast-1.ingest.monitor.azure.com}"
API_VER="2023-01-01"

# Lab DCR immutableIds (rg-cafi-lab)
DCR_EVENTS="dcr-a1c9febd71194b3faad4e55baf688931"
DCR_EXPL="dcr-cbf3ee5b479b41d682e1e09780128f8d"
DCR_FED="dcr-663e866b2976489fbac21e4abd827b03"
DCR_AIUSAGE="dcr-65b1d82059864c0fba4cab26d2bd027c"

STREAM_EVENTS="Custom-CAFI_Events_CL"
STREAM_EXPL="Custom-CAFI_Explanations_CL"
STREAM_FED="Custom-CAFI_FedAudit_CL"
STREAM_AIUSAGE="Custom-CAFI_AIUsage_CL"

KIND="${1:-}"
CSV="${2:-}"

if [[ -z "$KIND" || -z "$CSV" || ! -f "$CSV" ]]; then
  echo "Usage: $0 {events|explanations|fed|aiusage} /path/to/clean.csv" >&2
  exit 1
fi

JSON="/tmp/cafi_ingest_${KIND}.json"

build_events() {
  python3 - "$CSV" "$JSON" <<'PY'
import csv, json, sys
src, dst = sys.argv[1], sys.argv[2]
rows = []
with open(src, newline="", encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        rows.append({
            "TimeGenerated": (r.get("TimeGenerated") or "").strip(),
            "EventSource": (r.get("EventSource") or "").strip(),
            "DeviceRef": (r.get("DeviceRef") or "").strip(),
            "DeviceId": (r.get("DeviceId") or "").strip(),
            "Severity": (r.get("Severity") or "").strip(),
            "EventDetail": (r.get("EventDetail") or "").strip(),
        })
open(dst, "w").write(json.dumps(rows))
print("rows", len(rows))
PY
}

build_explanations() {
  # Map Feature+SHAP → DriverN string; include AnomalyScore (required by stream)
  python3 - "$CSV" "$JSON" <<'PY'
import csv, json, sys

def drv(feat, val):
    f = (feat or "").strip()
    v = (val or "").strip()
    if not f and not v:
        return ""
    try:
        n = float(v)
        return f"{f} ({n:+.3f})" if f else f"({n:+.3f})"
    except Exception:
        return f"{f} ({v})" if f else v

src, dst = sys.argv[1], sys.argv[2]
rows = []
with open(src, newline="", encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        rows.append({
            "TimeGenerated": (r.get("TimeGenerated") or "").strip(),
            "DeviceRef": (r.get("DeviceRef") or "").strip(),
            "AnomalyScore": (r.get("AnomalyScore") or "").strip(),
            "ContextStatus": (r.get("ContextStatus") or "").strip(),
            "NarrativeSummary": (r.get("NarrativeSummary") or "").strip(),
            "PivotSteps": (r.get("PivotSteps") or "").strip(),
            "Driver1": drv(r.get("Driver1_Feature"), r.get("Driver1_SHAPValue")),
            "Driver2": drv(r.get("Driver2_Feature"), r.get("Driver2_SHAPValue")),
            "Driver3": drv(r.get("Driver3_Feature"), r.get("Driver3_SHAPValue")),
            "Driver4": drv(r.get("Driver4_Feature"), r.get("Driver4_SHAPValue")),
            "Driver5": drv(r.get("Driver5_Feature"), r.get("Driver5_SHAPValue")),
        })
open(dst, "w").write(json.dumps(rows))
print("rows", len(rows))
PY
}

build_fed() {
  python3 - "$CSV" "$JSON" <<'PY'
import csv, json, sys
from datetime import datetime, timezone
src, dst = sys.argv[1], sys.argv[2]
rows = []
with open(src, newline="", encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        try:
            go = float(r.get("global_offset") or r.get("GlobalOffset") or 0)
        except Exception:
            go = 0.0
        rows.append({
            "TimeGenerated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "Round": int(float(r.get("round") or r.get("Round") or 0)),
            "GlobalOffset": go,
            "AcceptedNodes": (r.get("accepted_nodes") or r.get("AcceptedNodes") or "").strip(),
            "RejectedNodes": (r.get("rejected_nodes") or r.get("RejectedNodes") or "").strip(),
            "RejectionDetail": "",
            "DataSource": "CAFI_fed_clean",
        })
open(dst, "w").write(json.dumps(rows))
print("rows", len(rows))
PY
}

build_aiusage() {
  python3 - "$CSV" "$JSON" <<'PY'
import csv, json, sys
src, dst = sys.argv[1], sys.argv[2]
rows = []
with open(src, newline="", encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        rows.append({k: (v or "").strip() for k, v in r.items()})
open(dst, "w").write(json.dumps(rows))
print("rows", len(rows))
PY
}

case "$KIND" in
  events)       build_events;       DCR="$DCR_EVENTS";  STREAM="$STREAM_EVENTS" ;;
  explanations) build_explanations; DCR="$DCR_EXPL";    STREAM="$STREAM_EXPL" ;;
  fed)          build_fed;          DCR="$DCR_FED";     STREAM="$STREAM_FED" ;;
  aiusage)      build_aiusage;      DCR="$DCR_AIUSAGE"; STREAM="$STREAM_AIUSAGE" ;;
  *) echo "Unknown kind: $KIND" >&2; exit 1 ;;
esac

echo "POST $STREAM via $DCR"
az rest --method POST \
  --url "${DCE}/dataCollectionRules/${DCR}/streams/${STREAM}?api-version=${API_VER}" \
  --resource https://monitor.azure.com \
  --body @"${JSON}" \
  --headers "Content-Type=application/json"

echo "Done (empty HTTP body = success). Verify in Logs with a wide time range."
