module.exports = async function (context, req) {
  try {
    const { key, model, system, message } = req.body || {};

    if (!key) {
      context.res = { status: 400, body: { error: "key is required" } };
      return;
    }
    if (!message) {
      context.res = { status: 400, body: { error: "message is required" } };
      return;
    }

    const anthropicRes = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        model: model || "claude-sonnet-4-6",
        max_tokens: 1024,
        system: system || "",
        messages: [{ role: "user", content: message }],
        tools: [{ type: "web_search_20250305", name: "web_search" }]
      })
    });

    const data = await anthropicRes.json();

    if (!anthropicRes.ok) {
      context.res = { status: anthropicRes.status, body: { error: "Anthropic API error", details: data } };
      return;
    }

    const text = (data.content || [])
      .filter(function (block) { return block.type === "text"; })
      .map(function (block) { return block.text; })
      .join("\n");

    context.res = {
      status: 200,
      headers: { "Content-Type": "application/json" },
      body: { text: text || "" }
    };
  } catch (err) {
    context.res = { status: 500, body: { error: "Unhandled exception" } };
  }
};
