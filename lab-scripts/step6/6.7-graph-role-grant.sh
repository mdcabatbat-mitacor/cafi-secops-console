az rest --method POST \
  --uri "https://graph.microsoft.com/v1.0/servicePrincipals/5196c4ec-28fc-43d5-8fe5-b0714eb45e21/appRoleAssignments" \
  --headers "Content-Type=application/json" \
  --body '{
    "principalId": "5196c4ec-28fc-43d5-8fe5-b0714eb45e21",
    "resourceId": "e945aabc-0c07-4af4-8d16-747f28fd7cf1",
    "appRoleId": "741f803b-c850-494e-b5df-cde7c675a1ca"
  }'
