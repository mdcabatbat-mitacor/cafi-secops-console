module.exports = async function (context, req) {
  try {
    const caseId = (req.query.caseId || "").trim();
    if (!/^CASE-[A-Za-z0-9-]+$/.test(caseId)) {
      context.res = { status: 400, body: { error: "caseId must match CASE-<id>" } };
      return;
    }
    const site = process.env.JIRA_SITE;
    const email = process.env.JIRA_EMAIL;
    const token = process.env.JIRA_API_TOKEN;
    const auth = Buffer.from(`${email}:${token}`).toString("base64");
    const authHeaders = {
      "Authorization": `Basic ${auth}`,
      "Accept": "application/json"
    };

    const jql = `project = CAFI AND summary ~ "\\"${caseId}\\"" ORDER BY created DESC`;
    // Added "assignee" to the fields list -- same call, no extra request, just one more field.
    const url = `https://${site}.atlassian.net/rest/api/3/search/jql?jql=${encodeURIComponent(jql)}&fields=summary,status,assignee&maxResults=1`;
    const jiraRes = await fetch(url, { method: "GET", headers: authHeaders });
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

    // NEW: fetch comments in a second call -- the search endpoint above never returns them.
    // If this call fails for any reason, degrade to an empty comments list rather than
    // failing the whole lookup -- status/assignee already resolved above are still useful
    // on their own, and comments are additive, not required.
    let comments = [];
    try {
      const cRes = await fetch(
        `https://${site}.atlassian.net/rest/api/3/issue/${issue.key}/comment?orderBy=-created&maxResults=20`,
        { method: "GET", headers: authHeaders }
      );
      if (cRes.ok) {
        const cData = await cRes.json();
        comments = (cData.comments || []).map(c => ({
          id: c.id,
          author: c.author ? c.author.displayName : null,
          body: adfToText(c.body),
          created: c.created
        }));
      } else {
        context.log.warn("Jira comment fetch failed", cRes.status);
      }
    } catch (cErr) {
      context.log.warn("Jira comment fetch threw", cErr.message);
    }

    context.res = {
      status: 200,
      headers: { "Content-Type": "application/json" },
      body: {
        found: true,
        key: issue.key,
        summary: issue.fields.summary,
        status: issue.fields.status ? issue.fields.status.name : "Unknown",
        assignee: issue.fields.assignee ? issue.fields.assignee.displayName : null,
        url: `https://${site}.atlassian.net/browse/${issue.key}`,
        comments
      }
    };
  } catch (err) {
    context.res = { status: 500, body: { error: "Unhandled exception" } };
  }
};

// Jira Cloud REST v3 returns comment bodies as Atlassian Document Format (ADF) --
// a nested JSON tree, not plain text. This project already writes ADF on ticket
// creation (Step 6.2); this is the same format, read instead of written. Walks the
// tree and concatenates text nodes, joining separate paragraphs with newlines.
function adfToText(node) {
  if (!node) return "";
  if (typeof node === "string") return node;
  let out = [];
  function walk(n) {
    if (!n) return;
    if (n.type === "text" && typeof n.text === "string") { out.push(n.text); return; }
    if (Array.isArray(n.content)) n.content.forEach(walk);
    if (n.type === "paragraph" || n.type === "hardBreak") out.push("\n");
  }
  walk(node);
  return out.join("").replace(/\n{3,}/g, "\n\n").trim();
}
