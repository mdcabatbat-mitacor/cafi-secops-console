#!/usr/bin/env bash
# Uploads the simulation's raw artifacts into the four federation containers
# the console's ML & Federation view / Blob layout expects.
# Run after simulate_federation.py, from the same directory (./fed_output must exist).
# Requires $CAFI_STORAGE_ACCOUNT sourced from ~/clouddrive/cafi-vars.sh.

set -euo pipefail

STORAGE="${CAFI_STORAGE_ACCOUNT:?Set CAFI_STORAGE_ACCOUNT (e.g. cafistoragemichae)}"

# Using the account key instead of --auth-mode login: the logged-in user has
# control-plane access (can read the key) but wasn't separately granted
# Storage Blob Data Contributor for data-plane RBAC. Key auth sidesteps that.
STORAGE_KEY=$(az storage account keys list \
  --account-name "$STORAGE" \
  --query "[0].value" -o tsv)

az storage blob upload-batch \
  --account-name "$STORAGE" \
  --account-key "$STORAGE_KEY" \
  --destination fed-rounds \
  --source fed_output/fed-rounds \
  --overwrite

az storage blob upload-batch \
  --account-name "$STORAGE" \
  --account-key "$STORAGE_KEY" \
  --destination fed-weights \
  --source fed_output/fed-weights \
  --overwrite

az storage blob upload-batch \
  --account-name "$STORAGE" \
  --account-key "$STORAGE_KEY" \
  --destination fed-global-models \
  --source fed_output/fed-global-models \
  --overwrite

az storage blob upload-batch \
  --account-name "$STORAGE" \
  --account-key "$STORAGE_KEY" \
  --destination fed-audit \
  --source fed_output/fed-audit \
  --overwrite

echo "All federation artifacts uploaded to $STORAGE."
