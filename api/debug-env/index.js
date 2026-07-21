module.exports = async function (context, req) {
  const t = process.env.JIRA_API_TOKEN || "";
  context.res = {
    status: 200,
    body: {
      jiraSiteSet: !!process.env.JIRA_SITE,
      jiraEmailSet: !!process.env.JIRA_EMAIL,
      tokenLength: t.length,
      tokenLooksLikeKvReference: t.startsWith("@Microsoft.KeyVault")
    }
  };
};
