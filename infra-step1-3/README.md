# CAFI SecOps — Steps 1-3 Infrastructure Source

This folder holds the confirmed infrastructure-as-code artifacts for Steps 1-3
of the Production Lab Build Guide (Foundation; Sentinel/Watchlists/Storage/
Connectors; ContextualAlertScore L2 KQL Fusion), committed here so they live
alongside Step 4's ML pipeline (../lab-scripts/) and Step 8's console app
(repo root). All files in this folder are the original source files used
during the actual deployment, as confirmed live in Sentinel.

## Step 1 — Foundation
- Resource group rg-cafi-lab (Australia East)
- Key Vault cafi-keyvault + access policy for the signed-in user
- Monthly budget alert (cafi-lab-monthly, $75, 80% threshold)

## Step 2 — Sentinel, Watchlists, Storage, Connectors
- Nine resource providers registered
- Log Analytics workspace cafi-law, Sentinel onboarded
- Storage account cafistoragemichae with 10 blob containers
- Five watchlists populated via the portal wizard (the az rest path creates
  the container but leaves it with zero items — portal upload is the
  confirmed-working method). Source CSVs in watchlists/:
  - AssetInventory.csv (10 rows)
  - MaintenanceWindows.csv (4 rows)
  - ContextCatalogue.csv (4 rows)
  - ApprovedAITools.csv (4 rows)
  - ControlledAIEndpoints.csv (4 rows)
- Data connectors: Microsoft Defender XDR, Microsoft Entra ID (requires a
  P1/P2 licence for SignInLogs export), Microsoft Defender for Cloud Apps

## Step 3 — ContextualAlertScore (L2 KQL Fusion)
- test_contextual_alert_score.kql — Section 3.1 logic validation query
- contextual_alert_score.kql — the confirmed production scoring query, saved
  as the Sentinel function ContextualAlertScore
- generate_body_json.py / body.json — saves the KQL as the Sentinel function
  via az rest PUT
- alert_rule_body.json — scheduled analytics rule ("CAFI ContextualAlertScore
  - Escalate")

Full command-by-command detail with verified results is in the Working
Commands docx (Steps 1-3 sections).
