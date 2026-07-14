GRAPH_SP_ID=$(az ad sp show --id 00000003-0000-0000-c000-000000000000 --query id -o tsv)
echo "Graph SP Object ID: $GRAPH_SP_ID"

az ad sp show --id 00000003-0000-0000-c000-000000000000 \
  --query "appRoles[?value=='User.ReadWrite.All']" -o json
