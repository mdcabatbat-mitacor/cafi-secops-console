module.exports = async function (context, req) {
  try {
    const { key, action } = req.body || {};

    if (!/^CAFI-\d+$/.test(key || "")) {
      context.res = { status: 400, body: { error: "key must match CAFI-<number>" } };
      return;
    }

    const site = process.env.JIRA_SITE;
    const email = process.env.JIRA_EMAIL;
    const token = process.env.JIRA_API_TOKEN;
    const auth = Buffer.from(`${email}:${token}`).toString("base64");
    const base = `https://${site}.atlassian.net/rest/api/3/issue/${key}`;
    const headers = { "Authorization": `Basic ${auth}`, "Content-Type": "application/json", "Accept": "application/json" };

    if (action === "comment") {
      const text = ((req.body.text || "") + "").slice(0, 2000);
      if (!text.trim()) {
        context.res = { status: 400, body: { error: "text is required" } };
        return;
      }
      const r = await fetch(`${base}/comment`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          body: {
            type: "doc",
            version: 1,
            content: [{ type: "paragraph", content: [{ type: "text", text }] }]
          }
        })
      });
      if (!r.ok) {
        const d = await r.json().catch(() => ({}));
        context.res = { status: r.status, body: { error: "Jira comment failed", details: d } };
        return;
      }
      context.res = { status: 200, body: { ok: true } };
      return;
    }

    if (action === "transition") {
      const target = ((req.body.targetStatus || "") + "");
      const norm = s => s.toLowerCase().replace(/[^a-z0-9]/g, "");
      if (!norm(target)) {
        context.res = { status: 400, body: { error: "targetStatus is required" } };
        return;
      }
      const tr = await fetch(`${base}/transitions`, { method: "GET", headers });
      const td = await tr.json();
      if (!tr.ok) {
        context.res = { status: tr.status, body: { error: "Jira transitions fetch failed", details: td } };
        return;
      }
      const match = (td.transitions || []).find(t => t.to && norm(t.to.name) === norm(target));
      if (!match) {
        context.res = { status: 404, body: { error: "no matching transition", available: (td.transitions || []).map(t => t.to && t.to.name) } };
        return;
      }
      const pr = await fetch(`${base}/transitions`, {
        method: "POST",
        headers,
        body: JSON.stringify({ transition: { id: match.id } })
      });
      if (!pr.ok) {
        const d = await pr.json().catch(() => ({}));
        context.res = { status: pr.status, body: { error: "Jira transition failed", details: d } };
        return;
      }
      context.res = { status: 200, body: { ok: true, status: match.to.name } };
      return;
    }

    context.res = { status: 400, body: { error: "action must be 'comment' or 'transition'" } };
  } catch (err) {
    context.res = { status: 500, body: { error: "Unhandled exception" } };
  }
};
