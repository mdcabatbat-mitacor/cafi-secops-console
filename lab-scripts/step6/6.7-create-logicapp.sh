az logic workflow create \
  --resource-group rg-cafi-lab \
  --name cafi-ai-dlp-response \
  --location australiaeast \
  --definition lab-scripts/step6/ai-dlp-response-def.json \
  --mi-system-assigned
