#!/usr/bin/env bash
# Uploads the simulation's raw artifacts into the four federation containers
# the console's ML & Federation view / Blob layout expects.
# Run after simulate_federation.py, from the same directory (./fed_output must exist).
# Requires $CAFI_STORAGE_ACCOUNT sourced from ~/clouddrive/cafi-vars.sh.

set -euo pipefail

STORAGE="${CAFI_STORAGE_ACCOUNT:?Set CAFI_STORAGE_ACCOUNT (e.g. cafistoragemichae)}"

az storage blob upload-batch \
  --account-name "$STORAGE" \
  --destination fed-rounds \
  --source fed_output/fed-rounds \
  --auth-mode login \
  --overwrite

az storage blob upload-batch \
  --account-name "$STORAGE" \
  --destination fed-weights \
  --source fed_output/fed-weights \
  --auth-mode login \
  --overwrite

az storage blob upload-batch \
  --account-name "$STORAGE" \
  --destination fed-global-models \
  --source fed_output/fed-global-models \
  --auth-mode login \
  --overwrite

az storage blob upload-batch \
  --account-name "$STORAGE" \
  --destination fed-audit \
  --source fed_output/fed-audit \
  --auth-mode login \
  --overwrite

echo "All federation artifacts uploaded to $STORAGE."
