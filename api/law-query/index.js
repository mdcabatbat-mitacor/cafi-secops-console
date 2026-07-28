module.exports = async function (context, req) {
  // CORS preflight (same-origin console still benefits)
  if (req.method === "OPTIONS") {
    context.res = {
      status: 204,
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type"
      }
    };
    return;
  }

  try {
    const body = req.body || {};
    const query = (body.query || body.kql || "").trim();
    const timespan = (body.timespan || "P7D").trim(); // ISO-8601 duration

    if (!query) {
      context.res = {
        status: 400,
        headers: { "Content-Type": "application/json" },
        body: { error: "query (KQL) is required" }
      };
      return;
    }

    const workspaceId = (process.env.LAW_WORKSPACE_ID || "").trim();
    const clientId = (process.env.AAD_CLIENT_ID || "").trim();
    const clientSecret = (process.env.AAD_CLIENT_SECRET || "").trim();
    const tenantId = (process.env.AAD_TENANT_ID || process.env.TENANT_ID || "6361ff58-88a7-404a-bf78-1767d3a843f1").trim();

    if (!workspaceId) {
      context.res = {
        status: 500,
        headers: { "Content-Type": "application/json" },
        body: {
          error: "LAW_WORKSPACE_ID is not set on the Static Web App",
          hint: "az monitor log-analytics workspace show -g rg-cafi-lab -n cafi-law --query customerId -o tsv"
        }
      };
      return;
    }
    if (!clientId || !clientSecret) {
      context.res = {
        status: 500,
        headers: { "Content-Type": "application/json" },
        body: { error: "AAD_CLIENT_ID / AAD_CLIENT_SECRET must be present (same settings used by Easy Auth)" }
      };
      return;
    }

    // Client-credentials token for Log Analytics API
    const tokenUrl = `https://login.microsoftonline.com/${tenantId}/oauth2/v2.0/token`;
    const tokenBody = new URLSearchParams({
      client_id: clientId,
      client_secret: clientSecret,
      scope: "https://api.loganalytics.io/.default",
      grant_type: "client_credentials"
    });

    const tokenRes = await fetch(tokenUrl, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: tokenBody.toString()
    });
    const tokenData = await tokenRes.json();
    if (!tokenRes.ok || !tokenData.access_token) {
      context.res = {
        status: 502,
        headers: { "Content-Type": "application/json" },
        body: {
          error: "Failed to obtain Log Analytics token",
          details: tokenData.error_description || tokenData.error || tokenData
        }
      };
      return;
    }

    // Query the workspace
    const queryUrl = `https://api.loganalytics.io/v1/workspaces/${workspaceId}/query`;
    const queryRes = await fetch(queryUrl, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${tokenData.access_token}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ query, timespan })
    });

    const queryData = await queryRes.json();
    if (!queryRes.ok) {
      context.res = {
        status: queryRes.status,
        headers: { "Content-Type": "application/json" },
        body: {
          error: "Log Analytics query failed",
          details: queryData.error || queryData
        }
      };
      return;
    }

    // Return native shape so console asArray() works unchanged
    context.res = {
      status: 200,
      headers: { "Content-Type": "application/json" },
      body: queryData
    };
  } catch (err) {
    context.res = {
      status: 500,
      headers: { "Content-Type": "application/json" },
      body: {
        error: err.message || "law-query failed",
        details: String(err)
      }
    };
  }
};
