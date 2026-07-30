# Load script outputs into CAFI-LAW (automated report path)

Goal: after Entra sign-in, `lawSyncAll()` fills the console the same way
Manual Upload did — so the Security Report matches without re-uploading CSVs.

## What LAW already drives (today)

| LAW feed | Console kind | Status after your 10.14–10.16 work |
|----------|--------------|-------------------------------------|
| `CAFI_AnomalyScores_CL` | events | Active (lab L3) |
| `CAFI_Explanations_CL` | explanations | Active (lab L4) |
| `CAFI_FedAudit_CL` | fed | Active (lab L6) |
| `ContextualAlertScore` | events | Active (L2) |
| Watchlist `AssetInventory` | assets | Error until watchlist loaded |
| Watchlist `MaintenanceWindows` | maint | Error until watchlist loaded |
| Watchlist `ContextCatalogue` | changes | Error until watchlist loaded |

AI usage / tools / endpoints are **session** data today (Manual Upload or
config editors). They are not required for LAW auto-sync of L2–L6 + join quality.

## Step 1 — Watchlists (join quality + context status)

In Azure Portal → Microsoft Sentinel → **cafi-law** workspace → **Watchlist**:

1. Create / update **AssetInventory**
   - Source: `out/CAFI_assets_clean.csv`
   - SearchKey: `DeviceId`
   - Columns must match: DeviceId, Hostname, AssetRole, CriticalityTier,
     OwningSector, SiteCode, Vendor, Protocol

2. Create / update **MaintenanceWindows**
   - Source: `out/CAFI_maint_clean.csv`
   - SearchKey: `WindowId`

3. Create / update **ContextCatalogue**
   - Source: `out/CAFI_changes_clean.csv`
   - SearchKey: `ContextId`

CLI alternative (example for assets — adjust names):

```bash
# Upload CSV to a storage blob, then:
az sentinel watchlist create \
  --resource-group rg-cafi-lab \
  --workspace-name cafi-law \
  --watchlist-alias AssetInventory \
  --display-name "Asset Inventory" \
  --provider CAFI \
  --items-search-key DeviceId \
  --source-type Local file
# Prefer Portal upload for small lab CSVs (one-time).
```

After save, console **Refresh Data** (Entra signed-in) should show:
Asset Inventory / Maintenance / Context Catalogue → **Active**.

## Step 2 — Historical events into LAW (so cases populate on auto-sync)

Manual Upload put 588 events into the **browser session**. For the same
result after a fresh sign-in, those rows must live in a table `law-query`
already pulls — or a new feed.

### Option A — Prefer existing L3 table (fastest)

Map `CAFI_events_clean.csv` into columns compatible with how `ingest('events')`
reads L3 rows (TimeGenerated, DeviceRef/Computer, Severity, EventDetail, …).

If `CAFI_AnomalyScores_CL` already has lab rows that score into cases, you can
**append** historical-style rows via Log Analytics data collector API / DCR,
using the same column set the L3 job writes.

### Option B — Dedicated `CAFI_Events_CL` + one LAW_FEEDS entry (cleanest)

1. Create custom table `CAFI_Events_CL` (DCR or Azure Data Explorer-style
   custom log) with columns:
   `TimeGenerated, EventSource, DeviceRef, DeviceId, Severity, EventDetail`

2. Ingest `out/CAFI_events_clean.csv` into that table.

3. Add to console `LAW_FEEDS`:

```js
hist_events: {
  kind: 'events',
  label: 'Historical Events',
  query: 'CAFI_Events_CL | order by TimeGenerated desc | take 2000',
  timespan: 'P90D'
}
```

4. Redeploy SWA (same path as law-query / index.html).

Then Entra sign-in → auto-sync pulls historical events + L3/L4/L6 + watchlists.

## Step 3 — Explanations + Fed (if you want sample rows in LAW)

Lab already has L4/L6 rows. To mirror sample narratives/rounds in LAW:

- Append `CAFI_explanations_clean.csv` → `CAFI_Explanations_CL`
- Append `CAFI_fed_clean.csv` → `CAFI_FedAudit_CL` (map `round` → `Round`,
  `global_offset` → existing column names)

## Step 4 — AI governance (optional for full report parity)

`CAFI_aiusage_clean.csv` / aitools / aiendpoints still load via:

- Manual Upload, or
- Administration → Configuration Editors (tools / endpoints)

To fully automate AI sections, add custom tables + LAW_FEEDS the same way as
Option B (not required for L2–L6 + cases + join quality).

## Step 5 — Validate automated report

1. Sign out / clear session (or private window).
2. Sign in with Microsoft (Entra).
3. Confirm Data Sources → CAFI-LAW panel: feeds **Active** (including
   watchlists after Step 1).
4. Overview KPIs and Case Management populate without Manual Upload.
5. Generate Security Report — compare to `CAFI_SecurityReport_20260729-0702.html`.

## Mapping check (script → LAW → report)

| Script output | LAW target | Report section |
|---------------|------------|----------------|
| CAFI_events_clean.csv | AnomalyScores_CL and/or CAFI_Events_CL | KPIs, cases, disposition, IT/OT |
| CAFI_explanations_clean.csv | CAFI_Explanations_CL | L4 / case drawer |
| CAFI_fed_clean.csv | CAFI_FedAudit_CL | Federated chart |
| CAFI_assets_clean.csv | Watchlist AssetInventory | Join quality, Unknown asset |
| CAFI_maint_clean.csv | Watchlist MaintenanceWindows | InMaintenance |
| CAFI_changes_clean.csv | Watchlist ContextCatalogue | RecentlyChanged |
| CAFI_aiusage_clean.csv | (session or future table) | AI governance |
| CAFI_aitools / aiendpoints | (session / config) | Approved tools / endpoints |

Your manual report already proves the **script schemas are correct**.
Automation is only the durable load into the targets above.
