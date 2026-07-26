module.exports = async function (context, req) {
  if (req.method === "OPTIONS") {
    context.res = { status: 204, headers: { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "POST, OPTIONS", "Access-Control-Allow-Headers": "Content-Type" } };
    return;
  }
  try {
    const body = req.body || {};
    const key = (process.env.ANTHROPIC_API_KEY || "").trim();
    const model = body.model || "claude-sonnet-4-6";
    const system = body.system || "";
    const message = body.message || body.prompt || "";

    if (!key) {
      context.res = { status: 500, headers: { "Content-Type": "application/json" }, body: { error: "ANTHROPIC_API_KEY is not set on the Static Web App (same place as JIRA_API_TOKEN)" } };
      return;
    }
    if (!message) {
      context.res = { status: 400, headers: { "Content-Type": "application/json" }, body: { error: "message is required" } };
      return;
    }

    async function callAnthropic(payload) {
      const anthropicRes = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: {
          "x-api-key": key,
          "anthropic-version": "2023-06-01",
          "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
      });
      const data = await anthropicRes.json();
      if (!anthropicRes.ok) {
        const err = new Error((data && data.error && (data.error.message || data.error.type)) || ("Anthropic HTTP " + anthropicRes.status));
        err.status = anthropicRes.status;
        err.details = data;
        throw err;
      }
      return data;
    }

    let data;
    try {
      data = await callAnthropic({
        model: model,
        max_tokens: 1024,
        system: system,
        messages: [{ role: "user", content: message }],
        tools: [{ type: "web_search_20250305", name: "web_search" }]
      });
    } catch (e) {
      data = await callAnthropic({
        model: model,
        max_tokens: 1024,
        system: system,
        messages: [{ role: "user", content: message }]
      });
    }

    const text = (data.content || [])
      .filter(function (block) { return block.type === "text"; })
      .map(function (block) { return block.text; })
      .join("\n");

    context.res = { status: 200, headers: { "Content-Type": "application/json" }, body: { ok: true, text: text } };
  } catch (err) {
    context.res = { status: err.status || 500, headers: { "Content-Type": "application/json" }, body: { error: err.message || "Helios proxy failed", details: err.details || undefined } };
  }
};
