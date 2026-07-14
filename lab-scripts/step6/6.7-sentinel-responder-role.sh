IDENTITY_OBJECT_ID="5196c4ec-28fc-43d5-8fe5-b0714eb45e21"

az role assignment create \
  --assignee-object-id "$IDENTITY_OBJECT_ID" \
  --assignee-principal-type ServicePrincipal \
  --role "Microsoft Sentinel Responder" \
  --scope "/subscriptions/e611ddeb-8426-40fd-9488-2da64c5d95b5/resourceGroups/rg-cafi-lab"

az role assignment create \
  --assignee-object-id "$IDENTITY_OBJECT_ID" \
  --assignee-principal-type ServicePrincipal \
  --role "Microsoft Sentinel Responder" \
  --scope "/subscriptions/e611ddeb-8426-40fd-9488-2da64c5d95b5/resourceGroups/rg-cafi-lab/providers/Microsoft.OperationalInsights/workspaces/cafi-law"
