#!/usr/bin/env python3
"""
Push fed_output/fedaudit_rows.json into CAFI_FedAudit_CL via the Logs
Ingestion API, reusing the cafi-dce Data Collection Endpoint from Step 4.

Requires environment variables (source ~/clouddrive/cafi-vars.sh first,
then add the two new ones this step introduces):
  CAFI_DCE_ENDPOINT     - e.g. https://cafi-dce-mi22.australiaeast-1.ingest.monitor.azure.com
  CAFI_FEDAUDIT_DCR_ID  - immutable ID of the NEW DCR created for CAFI_FedAudit_CL
                           (portal: DCR resource -> JSON view -> immutableId)
  CAFI_FEDAUDIT_STREAM  - stream name from that DCR, typically
                           "Custom-CAFI_FedAudit_CL" (check the DCR's
                           dataFlows[].streams value - do not assume, copy it)

Auth: uses `az account get-access-token` for the logs ingestion resource,
same as Step 4's ingestion call. If Step 4 used a different identity/service
principal for ingestion (check your notes), swap the token acquisition
below to match - the DCR's role assignment (Monitoring Metrics Publisher)
must be granted to whichever identity actually sends this request.
"""

import json
import os
import subprocess
import urllib.request

DCE_ENDPOINT = os.environ["CAFI_DCE_ENDPOINT"]
DCR_ID = os.environ["CAFI_FEDAUDIT_DCR_ID"]
STREAM_NAME = os.environ.get("CAFI_FEDAUDIT_STREAM", "Custom-CAFI_FedAudit_CL")

with open("fed_output/fedaudit_rows.json") as f:
    rows = json.load(f)

import datetime
now = datetime.datetime.utcnow()
for i, row in enumerate(rows):
    # space rounds out a few minutes apart so the console's time-series
    # chart renders a sensible x-axis instead of one instant
    row["TimeGenerated"] = (now - datetime.timedelta(minutes=(len(rows) - i) * 5)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

token = subprocess.run(
    ["az", "account", "get-access-token", "--scope", "https://monitor.azure.com/.default",
     "--query", "accessToken", "-o", "tsv"],
    capture_output=True, text=True, check=True,
).stdout.strip()

url = f"{DCE_ENDPOINT}/dataCollectionRules/{DCR_ID}/streams/{STREAM_NAME}?api-version=2023-01-01"
body = json.dumps(rows).encode("utf-8")

req = urllib.request.Request(url, data=body, method="POST", headers={
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
})

try:
    with urllib.request.urlopen(req) as resp:
        print(f"Ingestion accepted: HTTP {resp.status}")
except urllib.error.HTTPError as e:
    print(f"Ingestion failed: HTTP {e.code}\n{e.read().decode()}")
    raise
