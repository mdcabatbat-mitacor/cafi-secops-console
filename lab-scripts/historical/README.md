# CAFI historical → CAFI-LAW pipeline

**Start here for a plain explanation:** [HOW-IT-WORKS.md](./HOW-IT-WORKS.md)

## Scripts

| File | Purpose |
|------|---------|
| `cafi_historical_to_law.py` | Main transform: ISCX / IoT / Modbus / CAFI samples → `out/CAFI_*_clean.csv` |
| `cafi_csv_transform.py` | Optional single-CSV column alias mapper |
| `ingest_to_law.sh` | Cloud Shell: build JSON + `az rest` POST to DCR streams (verified) |
| `out/` | Generated clean CSVs (lab baseline) |

```bash
# Transform
python3 cafi_historical_to_law.py --indir /path/to/raw --outdir ./out

# Ingest (Cloud Shell, after az login --scope "https://monitor.azure.com/.default")
chmod +x ingest_to_law.sh
./ingest_to_law.sh events       ./out/CAFI_events_clean.csv
./ingest_to_law.sh explanations ./out/CAFI_explanations_clean.csv
./ingest_to_law.sh fed          ./out/CAFI_fed_clean.csv
./ingest_to_law.sh aiusage      ./out/CAFI_aiusage_clean.csv
```

Watchlists (assets / maint / changes / aitools / aiendpoints) are updated in the
**portal** (Update watchlist ← clean CSV), not via this script.

## Outputs (`out/`)

| File | LAW target | Verified lab load |
|------|------------|-------------------|
| `CAFI_events_clean.csv` | `CAFI_Events_CL` | 588 rows |
| `CAFI_explanations_clean.csv` | `CAFI_Explanations_CL` (mapped Drivers) | DC01+ rows |
| `CAFI_fed_clean.csv` | `CAFI_FedAudit_CL` | 6 rounds |
| `CAFI_assets_clean.csv` | Watchlist AssetInventory | Active |
| `CAFI_maint_clean.csv` | Watchlist MaintenanceWindows | Active |
| `CAFI_changes_clean.csv` | Watchlist ContextCatalogue | Active |
| `CAFI_aiusage_clean.csv` | `CAFI_AIUsage_CL` | 10 rows |
| `CAFI_aitools_clean.csv` | Watchlist ApprovedAITools | Active |
| `CAFI_aiendpoints_clean.csv` | Watchlist ControlledAIEndpoints | Active |

Column names match console `TEMPLATES` / `ingest()` so LAW auto-sync populates
the Security Report without mismatched fields.

## Tunables (`cafi_historical_to_law.py`)

- `--max-iscx-per-label` (default 40)
- `--max-iot-rows` (default 50)
- `--max-modbus-per-type` (default 30)

## Related lab docs

- Production guide: Steps **10.13–10.20** in `CAFI_Production_Lab_Reference_Guide_Steps_1-10_v25.docx`
- Console package: `../api/law-query`, `../index.html` (LAW_FEEDS)
