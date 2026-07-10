# Step 5 — Layer 6: Federated Training Audit

Scripts for simulating federated retraining across 4 sector nodes (plant-edge,
grid-rtu, it-soc, vendor-ext-04) with FedAvg + a Byzantine gradient-norm /
cosine-similarity outlier filter, then ingesting the per-round audit into
`CAFI_FedAudit_CL`.

## Run order

```bash
source ../cafi-vars.sh
python3 simulate_federation.py          # -> ./fed_output/
export CAFI_STORAGE_ACCOUNT=cafistoragemichae
bash upload_fed_artifacts.sh            # -> fed-rounds / fed-weights / fed-global-models / fed-audit containers

# after creating CAFI_FedAudit_CL via cafi-law -> Tables -> New custom log (DCR-based),
# using sample_fedaudit_record.json as the schema sample:
export CAFI_DCE_ENDPOINT=https://cafi-dce-mi22.australiaeast-1.ingest.monitor.azure.com
export CAFI_FEDAUDIT_DCR_ID=dcr-663e866b2976489fbac21e4abd827b03
export CAFI_FEDAUDIT_STREAM=Custom-CAFI_FedAudit_CL
python3 ingest_fedaudit.py
```

Confirmed result: 6 rounds, `GlobalOffset` decreasing every round
(0.4053 → 0.3768 → 0.3707 → 0.3685 → 0.3678 → 0.3663), `vendor-ext-04`
genuinely rejected by the outlier filter only at round 5.

## Known gotchas

- **Token audience:** same as Step 4 — `az account get-access-token --scope
  "https://monitor.azure.com/.default"`, not `--resource`.
- **RBAC:** Owner/Global Admin does not grant blob or DCR data-plane access.
  `upload_fed_artifacts.sh` uses the storage account key (control-plane read)
  to sidestep needing Storage Blob Data Contributor. The DCR needs Monitoring
  Metrics Publisher granted explicitly (assigned to both
  m.cabatbat@mitacor.net and SysAD@mitacor.net on `cafi-fedaudit-dcr`; SysAD's
  grant is currently unused but harmless).
- **Re-running the ingestion script** creates duplicate rows (no upsert on
  the Logs Ingestion API). Query with dedup, not a plain `order by`:
  ```kql
  CAFI_FedAudit_CL
  | summarize arg_max(TimeGenerated, *) by Round
  | order by Round asc
  ```
