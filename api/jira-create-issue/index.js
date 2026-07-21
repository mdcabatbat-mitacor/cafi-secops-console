const { DefaultAzureCredential } = require("@azure/identity");
const { SecretClient } = require("@azure/keyvault-secrets");

let cachedToken = null;
let cachedAt = 0;

async function getJiraToken() {
  if (cachedToken && (Date.now() - cachedAt) < 5 * 60 * 1000) return cachedToken;
  const credential = new DefaultAzureCredential();
  const client = new SecretClient(process.env.KEY_VAULT_URI, credential);
  const secret = await client.getSecret("jira-api-token");
  cachedToken = secret.value;
  cachedAt = Date.now();
  return cachedToken;
}

module.exports = async function (context, req) {
  const { summary, description } = req.body || {};

  if (!summary) {
    context.res = { status: 400, body: { error: "summary is required" } };
    return;
  }

  const site = process.env.JIRA_SITE;
  const email = process.env.JIRA_EMAIL;
  const token = await getJiraToken();

  const auth = Buffer.from(`${email}:${token}`).toString("base64");

  const jiraRes = await fetch(`https://${site}.atlassian.net/rest/api/3/issue`, {
    method: "POST",
    headers: {
      "Authorization": `Basic ${auth}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      fields: {
        project: { key: "CAFI" },
        summary: summary,
        description: {
          type: "doc",
          version: 1,
          content: [
            { type: "paragraph", content: [{ type: "text", text: description || "Created via CAFI SecOps console" }] }
          ]
        },
        issuetype: { name: "Task" }
      }
    })
  });

  const data = await jiraRes.json();

  if (!jiraRes.ok) {
    context.res = { status: jiraRes.status, body: { error: "Jira API error", details: data } };
    return;
  }

  context.res = {
    status: 200,
    headers: { "Content-Type": "application/json" },
    body: { key: data.key, id: data.id, self: data.self }
  };
};
