# How the CAFI historical filter / transform works

## Big picture (one sentence)

Raw historical files (ISCX, IoT pcaps-as-CSV, ToN Modbus, CAFI samples) are **rewritten** into nine small CSVs whose **column names exactly match** what the console and CAFI-LAW expect — then those CSVs are loaded into watchlists or custom tables so Entra sign-in auto-fills the dashboard and Security Report.

```
Raw history (ISCX / IoT / samples)
        │
        ▼
  cafi_historical_to_law.py
        │
        ▼
  out/CAFI_*_clean.csv   ← fixed schemas
        │
        ├──► Sentinel watchlists (assets, maint, changes, AI tools, endpoints)
        └──► LAW custom tables via DCR + Logs Ingestion API
                    │
                    ▼
              /api/law-query  →  console LAW_FEEDS  →  report / KPIs
```

## Why a script is needed

Historical datasets do **not** look like CAFI:

| Source | Typical columns | Problem |
|--------|-----------------|---------|
| ISCX CIC | Flow features + `Label` | No DeviceRef, Severity, EventDetail |
| IoT pcap CSVs | Packet features; attack in **filename** | No CAFI event schema |
| ToN Modbus | date, time, label, type | Different names and time format |
| CAFI samples | Already correct | Used as the **contract** for other rows |

The script does three jobs:

1. **Extract** — read each file type (CSV / XLSX).
2. **Transform** — map labels → Severity, invent stable DeviceRef/DeviceId from a lab asset pool, build EventDetail text, normalize times to ISO UTC.
3. **Structure** — write only the columns the console `ingest()` and report template use (no extra junk columns).

## What each output feeds

| Output file | Goes into | Console / report use |
|-------------|-----------|----------------------|
| `CAFI_events_clean.csv` | Table `CAFI_Events_CL` | Historical Events, triage, cases, KPIs |
| `CAFI_assets_clean.csv` | Watchlist `AssetInventory` | Join quality, Unknown asset |
| `CAFI_maint_clean.csv` | Watchlist `MaintenanceWindows` | InMaintenance context |
| `CAFI_changes_clean.csv` | Watchlist `ContextCatalogue` | RecentlyChanged context |
| `CAFI_explanations_clean.csv` | Table `CAFI_Explanations_CL` | L4 narratives (mapped drivers on ingest) |
| `CAFI_fed_clean.csv` | Table `CAFI_FedAudit_CL` | L6 federation chart |
| `CAFI_aiusage_clean.csv` | Table `CAFI_AIUsage_CL` | AI governance usage |
| `CAFI_aitools_clean.csv` | Watchlist `ApprovedAITools` | Allow-list |
| `CAFI_aiendpoints_clean.csv` | Watchlist `ControlledAIEndpoints` | Endpoint control |

## How event rows are built (example)

From an ISCX row with `Label = DDoS`:

1. Severity ← map `DDoS` → `Critical` (lookup table in the script).
2. DeviceRef / DeviceId ← cycle through lab assets (`DC01`, `plc-reactor-01`, …) so join quality works against AssetInventory.
3. EventSource ← `IT` or `OT` from asset sector.
4. EventDetail ← short text including label and key flow fields.
5. TimeGenerated ← synthetic UTC timestamp in the lab window (or parsed if present).

Caps (`--max-iscx-per-label`, etc.) keep the lab volume practical (~588 events), not millions of flows.

## Scripts in this folder

| File | Role |
|------|------|
| `cafi_historical_to_law.py` | **Main** transform: samples + ISCX + IoT + Modbus → all `out/CAFI_*_clean.csv` |
| `cafi_csv_transform.py` | Optional single-file / alias mapper when headers already almost match |
| `ingest_to_law.sh` | Verified Cloud Shell commands: JSON build + `az rest` POST to DCRs |
| `out/` | Last generated clean CSVs (safe to commit for lab reproducibility) |

## Run transform locally

```bash
cd lab-scripts/historical   # or wherever you place this folder in the repo
python3 cafi_historical_to_law.py \
  --indir /path/to/raw/csvs \
  --outdir ./out
ls -la out/
```

## Run ingest (Cloud Shell, after clean CSVs exist)

See `ingest_to_law.sh` and Step 10.15–10.19 in the lab guide. Summary:

1. Watchlists → Portal Update watchlist (clean CSV).
2. Tables → `az login --scope "https://monitor.azure.com/.default"` then `az rest` POST to DCR stream (Publisher role on DCR + `cafi-dce`).
3. Console → Entra sign-in → Refresh Data → feeds Active.

## Mapping on ingest (important)

- **Explanations:** table stream expects `Driver1`…`Driver5` strings and `AnomalyScore`. The clean CSV has `Driver1_Feature` + `Driver1_SHAPValue`; `ingest_to_law.sh` maps them to `Driver1 = "Feature (+0.410)"` style before POST.
- **Fed:** CSV `round` / `global_offset` → stream `Round` / `GlobalOffset` (PascalCase + types).

Without that mapping, API can return HTTP 204 but rows never appear in Logs.
