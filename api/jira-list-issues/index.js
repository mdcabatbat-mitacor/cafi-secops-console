module.exports = async function (context, req) {
  try {
    const site = process.env.JIRA_SITE;
    const email = process.env.JIRA_EMAIL;
    const token = process.env.JIRA_API_TOKEN;
    const auth = Buffer.from(`${email}:${token}`).toString("base64");

    const jql = "project = CAFI ORDER BY created DESC";
    const url = `https://${site}.atlassian.net/rest/api/3/search/jql?jql=${encodeURIComponent(jql)}&fields=summary,status,created,updated,description&maxResults=50`;

    const jiraRes = await fetch(url, {
      method: "GET",
      headers: { "Authorization": `Basic ${auth}`, "Accept": "application/json" }
    });

    const data = await jiraRes.json();

    if (!jiraRes.ok) {
      context.res = { status: jiraRes.status, body: { error: "Jira API error", details: data } };
      return;
    }

    const flat = d => {
      if (!d || !Array.isArray(d.content)) return [];
      return d.content
        .map(p => (p.content || []).map(t => t.text || "").join(""))
        .filter(x => x.trim().length > 0);
    };

    const issues = (data.issues || []).map(i => ({
      key: i.key,
      descLines: flat(i.fields.description),
      summary: i.fields.summary,
      status: i.fields.status ? i.fields.status.name : "Unknown",
      created: i.fields.created,
      updated: i.fields.updated,
      url: `https://${site}.atlassian.net/browse/${i.key}`
    }));

    context.res = {
      status: 200,
      headers: { "Content-Type": "application/json" },
      body: { issues }
    };
  } catch (err) {
    context.res = { status: 500, body: { error: "Unhandled exception" } };
  }
};
