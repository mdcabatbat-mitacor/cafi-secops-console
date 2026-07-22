module.exports = async function (context, req) {
  try {
    const caseId = (req.query.caseId || "").trim();

    if (!/^CASE-\d+$/.test(caseId)) {
      context.res = { status: 400, body: { error: "caseId must match CASE-<number>" } };
      return;
    }

    const site = process.env.JIRA_SITE;
    const email = process.env.JIRA_EMAIL;
    const token = process.env.JIRA_API_TOKEN;

    const auth = Buffer.from(`${email}:${token}`).toString("base64");

    const jql = `project = CAFI AND summary ~ "\\"${caseId}\\"" ORDER BY created DESC`;
    const url = `https://${site}.atlassian.net/rest/api/3/search/jql?jql=${encodeURIComponent(jql)}&fields=summary,status&maxResults=1`;

    const jiraRes = await fetch(url, {
      method: "GET",
      headers: {
        "Authorization": `Basic ${auth}`,
        "Accept": "application/json"
      }
    });

    const data = await jiraRes.json();

    if (!jiraRes.ok) {
      context.res = { status: jiraRes.status, body: { error: "Jira API error", details: data } };
      return;
    }

    const issue = (data.issues || [])[0];

    if (!issue) {
      context.res = { status: 200, body: { found: false } };
      return;
    }

    context.res = {
      status: 200,
      headers: { "Content-Type": "application/json" },
      body: {
        found: true,
        key: issue.key,
        summary: issue.fields.summary,
        status: issue.fields.status ? issue.fields.status.name : "Unknown",
        url: `https://${site}.atlassian.net/browse/${issue.key}`
      }
    };
  } catch (err) {
    context.res = { status: 500, body: { error: "Unhandled exception" } };
  }
};
