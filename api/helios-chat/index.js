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
        model: model || "claude-3-5-sonnet-latest",
        max_tokens: 700,
        system: system || "",
        messages: [{ role: "user", content: message }]
      })
    });

    const data = await anthropicRes.json();

    if (!anthropicRes.ok) {
      context.res = { status: anthropicRes.status, body: { error: "Anthropic API error", details: data } };
      return;
    }

    const text = data.content && data.content[0] && data.content[0].text;

    context.res = {
      status: 200,
      headers: { "Content-Type": "application/json" },
      body: { text: text || "" }
    };
  } catch (err) {
    context.res = { status: 500, body: { error: "Unhandled exception" } };
  }
};
